from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, FormView, ListView, TemplateView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from django_fsm import TransitionNotAllowed
from userprofile.forms import UserForm
from utils.db import get_max_order
from utils.forms import SetNewPasswordForm

from . email import send_package_enrollment_batch
from . forms import (
    ActionForm,
    AcceptEnrollmentForm,
    ActionTriggerForm,
    BehaviorForm,
    CategoryForm,
    CSVUploadForm,
    GoalForm,
    PackageEnrollmentForm,
    TriggerForm,
)
from . mixins import ContentAuthorMixin, ContentEditorMixin, ContentViewerMixin
from . models import (
    Action, Behavior, Category, Goal, PackageEnrollment, Trigger
)
from . permissions import is_content_editor, superuser_required


class PublishView(View):
    """A Simple Base View for subclasses that need to publish content. This
    is overridden by views that specify the model and slug_field for different
    types of content.

    """
    http_method_names = ['post']
    model = None
    slug_field = None

    def get_object(self, kwargs):
        if self.model is None or self.slug_field is None:
            raise RuntimeError(
                "PublishView subclasses must define a model and slug_field "
                "attributes."
            )
        params = {self.slug_field: kwargs.get(self.slug_field, None)}
        return self.model.objects.get(**params)

    def post(self, request, *args, **kwargs):
        try:
            obj = self.get_object(kwargs)
            if request.POST.get('publish', False):
                obj.publish()
                obj.save(updated_by=request.user)
                messages.success(request, "{0} has been published".format(obj))
            elif request.POST.get('decline', False):
                obj.decline()
                obj.save(updated_by=request.user)
                messages.success(request, "{0} has been declined".format(obj))
            elif request.POST.get('draft', False):
                obj.draft()
                obj.save(updated_by=request.user)
                messages.success(request, "{0} is now in Draft".format(obj))
        except self.model.DoesNotExist:
            messages.error(
                request, "Could not find the specified {0}".format(self.model)
            )
        except TransitionNotAllowed:
            messages.error(request, "Unable to process transition.")
        return redirect("goals:index")


class ReviewableUpdateView(UpdateView):
    """A subclass of UpdateView; This allows users to submit content for
    review. On POST, we simply check for a True `review` value once the object
    has been saved.

    """
    def form_valid(self, form):
        result = super(ReviewableUpdateView, self).form_valid(form)

        # If the POSTed data contains a True 'review' value, the user clicked
        # the "Submit for Review" button.
        if self.request.POST.get('review', False):
            self.object.review()  # Transition to the new state
            msg = "{0} has been submitted for review".format(self.object)
            messages.success(self.request, msg)

        # Record who saved the item.
        self.object.save(updated_by=self.request.user)
        return result


class CreatedByView(CreateView):
    """A Subclass of CreateView that tracks who created the object."""

    def form_valid(self, form):
        result = super(CreatedByView, self).form_valid(form)
        self.object.save(created_by=self.request.user)
        return result


@user_passes_test(superuser_required, login_url='/')
def upload_csv(request):
    """Allow a user to upload a CSV file to populate our data backend."""
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'CSV File uploaded, successfully.')
                return redirect("goals:index")
            except CSVUploadForm.InvalidFormat as e:
                messages.error(
                    request, "The uploaded file could not be "
                    "processed. Please check the format and try again: "
                    " {0}".format(e)
                )
        else:
            messages.warning(
                request, "This form didn't validate. Please try again."
            )
    else:
        form = CSVUploadForm()

    context = {'form': form}
    return render(request, 'goals/upload_csv.html', context)


class IndexView(ContentViewerMixin, TemplateView):
    template_name = "goals/index.html"

    def get(self, request, *args, **kwargs):
        """Include info on pending and declined content items."""
        context = self.get_context_data(**kwargs)
        if is_content_editor(request.user):
            # Show content pending review.
            context['is_editor'] = True
            context['categories'] = Category.objects.filter(state='pending-review')
            context['goals'] = Goal.objects.filter(state='pending-review')
            context['behaviors'] = Behavior.objects.filter(state='pending-review')
            context['actions'] = Action.objects.filter(state='pending-review')
        # List content created/updated by the current user.
        conditions = Q(created_by=request.user) | Q(updated_by=request.user)
        context['my_categories'] = Category.objects.filter(conditions)
        context['my_goals'] = Goal.objects.filter(conditions)
        context['my_behaviors'] = Behavior.objects.filter(conditions)
        context['my_actions'] = Action.objects.filter(conditions)
        return self.render_to_response(context)


class CategoryListView(ContentViewerMixin, ListView):
    model = Category
    context_object_name = 'categories'
    template_name = "goals/category_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related("goal_set", "goal_set__behavior_set")


class CategoryDetailView(ContentViewerMixin, DetailView):
    queryset = Category.objects.all()
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"


class CategoryCreateView(ContentEditorMixin, CreatedByView):
    model = Category
    form_class = CategoryForm
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"

    def get_initial(self, *args, **kwargs):
        """Pre-populate the value for the initial order. This can't be done
        at the class level because we want to query the value each time."""
        initial = super(CategoryCreateView, self).get_initial(*args, **kwargs)
        if 'order' not in initial:
            initial['order'] = get_max_order(Category)
        return initial

    def get_context_data(self, **kwargs):
        context = super(CategoryCreateView, self).get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class CategoryDuplicateView(CategoryCreateView):
    """Initializes the Create form with a copy of data from another object."""
    def get_initial(self, *args, **kwargs):
        initial = super(CategoryDuplicateView, self).get_initial(*args, **kwargs)
        try:
            obj = self.get_object()
            initial.update({
                "title": "Copy of {0}".format(obj.title),
                "description": obj.description,
                "color": obj.color,
            })
        except self.model.DoesNotExist:
            pass
        initial['order'] = get_max_order(Category)
        return initial


class CategoryPublishView(ContentEditorMixin, PublishView):
    model = Category
    slug_field = 'title_slug'


class CategoryUpdateView(ContentEditorMixin, ReviewableUpdateView):
    model = Category
    form_class = CategoryForm
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"

    def get_context_data(self, **kwargs):
        context = super(CategoryUpdateView, self).get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class CategoryDeleteView(ContentEditorMixin, DeleteView):
    model = Category
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    success_url = reverse_lazy('goals:index')


class GoalListView(ContentViewerMixin, ListView):
    model = Goal
    context_object_name = 'goals'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related("behavior_set", "categories")


class GoalDetailView(ContentViewerMixin, DetailView):
    queryset = Goal.objects.all()
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"


class GoalCreateView(ContentAuthorMixin, CreatedByView):
    model = Goal
    form_class = GoalForm
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"

    def get_context_data(self, **kwargs):
        context = super(GoalCreateView, self).get_context_data(**kwargs)
        context['goals'] = Goal.objects.all().prefetch_related("categories")
        return context


class GoalDuplicateView(GoalCreateView):
    """Initializes the Create form with a copy of data from another object."""
    def get_initial(self, *args, **kwargs):
        initial = super(GoalDuplicateView, self).get_initial(*args, **kwargs)
        try:
            obj = self.get_object()
            initial.update({
                "title": "Copy of {0}".format(obj.title),
                "categories": obj.categories.values_list("id", flat=True),
                "description": obj.description,
            })
        except self.model.DoesNotExist:
            pass
        return initial


class GoalPublishView(ContentEditorMixin, PublishView):
    model = Goal
    slug_field = 'title_slug'


class GoalUpdateView(ContentAuthorMixin, ReviewableUpdateView):
    model = Goal
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    form_class = GoalForm

    def get_context_data(self, **kwargs):
        context = super(GoalUpdateView, self).get_context_data(**kwargs)
        context['goals'] = Goal.objects.all().prefetch_related(
            "categories",
            "behavior_set"
        )
        return context


class GoalDeleteView(ContentEditorMixin, DeleteView):
    model = Goal
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    success_url = reverse_lazy('goals:index')


class TriggerListView(ContentViewerMixin, ListView):
    model = Trigger
    queryset = Trigger.objects.default()
    context_object_name = 'triggers'


class TriggerDetailView(ContentViewerMixin, DetailView):
    queryset = Trigger.objects.default()
    slug_field = "name_slug"
    slug_url_kwarg = "name_slug"


class TriggerCreateView(ContentEditorMixin, CreateView):
    model = Trigger
    form_class = TriggerForm
    slug_field = "name_slug"
    slug_url_kwarg = "name_slug"

    def get_context_data(self, **kwargs):
        context = super(TriggerCreateView, self).get_context_data(**kwargs)
        context['triggers'] = Trigger.objects.default()
        return context


class TriggerDuplicateView(TriggerCreateView):
    """Initializes the Create form with a copy of data from another object."""
    def get_initial(self, *args, **kwargs):
        initial = super(TriggerDuplicateView, self).get_initial(*args, **kwargs)
        try:
            obj = self.get_object()
            initial.update({
                "name": "Copy of {0}".format(obj.name),
                "trigger_type": obj.trigger_type,
                "time": obj.time,
                "recurrences": obj.recurrences,
            })
        except self.model.DoesNotExist:
            pass
        return initial


class TriggerUpdateView(ContentEditorMixin, UpdateView):
    model = Trigger
    form_class = TriggerForm
    slug_field = "name_slug"
    slug_url_kwarg = "name_slug"

    def get_context_data(self, **kwargs):
        context = super(TriggerUpdateView, self).get_context_data(**kwargs)
        context['triggers'] = Trigger.objects.default()
        return context


class TriggerDeleteView(ContentEditorMixin, DeleteView):
    model = Trigger
    slug_field = "name_slug"
    slug_url_kwarg = "name_slug"
    success_url = reverse_lazy('goals:index')


class BehaviorListView(ContentViewerMixin, ListView):
    model = Behavior
    context_object_name = 'behaviors'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related(
            "goals", "goals__categories", "action_set"
        )


class BehaviorDetailView(ContentViewerMixin, DetailView):
    queryset = Behavior.objects.all()
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"


class BehaviorCreateView(ContentAuthorMixin, CreatedByView):
    model = Behavior
    form_class = BehaviorForm
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"

    def get_context_data(self, **kwargs):
        context = super(BehaviorCreateView, self).get_context_data(**kwargs)
        context['behaviors'] = Behavior.objects.all()
        return context


class BehaviorDuplicateView(BehaviorCreateView):
    """Initializes the Create form with a copy of data from another object."""
    def get_initial(self, *args, **kwargs):
        initial = super(BehaviorDuplicateView, self).get_initial(*args, **kwargs)
        try:
            obj = self.get_object()
            initial.update({
                "title": "Copy of {0}".format(obj.title),
                "description": obj.description,
                "more_info": obj.more_info,
                "informal_list": obj.informal_list,
                "external_resoruce": obj.external_resource,
                "goals": obj.goals.values_list("id", flat=True),
                "default_trigger": obj.default_trigger.id if obj.default_trigger else None,
                "source_link": obj.source_link,
                "source_notes": obj.source_notes,
            })
        except self.model.DoesNotExist:
            pass
        return initial


class BehaviorPublishView(ContentEditorMixin, PublishView):
    model = Behavior
    slug_field = 'title_slug'


class BehaviorUpdateView(ContentAuthorMixin, ReviewableUpdateView):
    model = Behavior
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    form_class = BehaviorForm

    def get_context_data(self, **kwargs):
        context = super(BehaviorUpdateView, self).get_context_data(**kwargs)
        context['behaviors'] = Behavior.objects.all()
        return context


class BehaviorDeleteView(ContentEditorMixin, DeleteView):
    model = Behavior
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    success_url = reverse_lazy('goals:index')


class ActionListView(ContentViewerMixin, ListView):
    model = Action
    context_object_name = 'actions'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related("behavior__title")


class ActionDetailView(ContentViewerMixin, DetailView):
    queryset = Action.objects.all()
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    pk_url_kwarg = 'pk'
    query_pk_and_slug = True  # Use pk and slug together to identify object.


class ActionCreateView(ContentAuthorMixin, CreatedByView):
    model = Action
    form_class = ActionForm
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    pk_url_kwarg = 'pk'
    query_pk_and_slug = True  # Use pk and slug together to identify object.
    action_type = Action.CUSTOM

    def _set_action_type(self, action_type):
        """Ensure the provided action type is valid."""
        if action_type in [at[0] for at in Action.ACTION_TYPE_CHOICES]:
            self.action_type = action_type

    def get_initial(self):
        data = self.initial.copy()
        data.update(self.form_class.INITIAL[self.action_type])
        return data

    def get(self, request, *args, **kwargs):
        # See if we're creating a specific Action type, and if so,
        # prepopulate the form with some initial data.
        self._set_action_type(request.GET.get("actiontype", self.action_type))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Handle dealing with 2 forms.
        self.object = None
        form = self.get_form()
        trigger_form = ActionTriggerForm(request.POST, prefix="trigger")
        if form.is_valid() and trigger_form.is_valid():
            return self.form_valid(form, trigger_form)
        else:
            return self.form_invalid(form, trigger_form)

    def form_valid(self, form, trigger_form):
        self.object = form.save()
        default_trigger = trigger_form.save(commit=False)
        default_trigger.name = "Default: {0}-{1}".format(self.object, self.object.id)
        default_trigger.save()
        self.object.default_trigger = default_trigger
        self.object.save()
        return redirect(self.get_success_url())

    def form_invalid(self, form, trigger_form):
        ctx = self.get_context_data(form=form, trigger_form=trigger_form)
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        context = super(ActionCreateView, self).get_context_data(**kwargs)
        context['action_type'] = self.action_type

        # We also list all existing actions & link to them.
        context['actions'] = Action.objects.all().select_related("behavior__title")

        # pre-populate some dynamic content displayed to the user regarding
        # an action's parent behavior.
        context['behaviors'] = Behavior.objects.values(
            "id", "description", "informal_list"
        )
        if 'trigger_form' not in context:
            context['trigger_form'] = ActionTriggerForm(prefix="trigger")
        return context


class ActionDuplicateView(ActionCreateView):
    """Initializes the Create form with a copy of data from another object."""
    def get_initial(self, *args, **kwargs):
        initial = super(ActionDuplicateView, self).get_initial(*args, **kwargs)
        try:
            obj = self.get_object()
            initial.update({
                "title": "Copy of {0}".format(obj.title),
                "sequence_order": obj.sequence_order,
                "behavior": obj.behavior.id,
                "description": obj.description,
                "more_info": obj.more_info,
                "external_resource": obj.external_resource,
            })
        except self.model.DoesNotExist:
            pass
        return initial


class ActionPublishView(ContentEditorMixin, PublishView):
    model = Action
    slug_field = 'title_slug'
    pk_url_kwarg = 'pk'
    query_pk_and_slug = True  # Use pk and slug together to identify object.

    def get_object(self, kwargs):
        """Actions may have have duplicates title_slug values, so we need to
        explicitly construct the lookup values."""
        params = {
            self.slug_field: kwargs.get(self.slug_field, None),
            self.pk_url_kwarg: kwargs.get(self.pk_url_kwarg, None),
        }
        return self.model.objects.get(**params)


class ActionUpdateView(ContentAuthorMixin, ReviewableUpdateView):
    model = Action
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    pk_url_kwarg = 'pk'
    query_pk_and_slug = True  # Use pk and slug together to identify object.
    form_class = ActionForm

    def post(self, request, *args, **kwargs):
        # Handle dealing with 2 forms.
        self.object = self.get_object()
        form = self.get_form()
        trigger_form = ActionTriggerForm(
            request.POST,
            instance=self.object.default_trigger,
            prefix="trigger"
        )
        if form.is_valid() and trigger_form.is_valid():
            return self.form_valid(form, trigger_form)
        else:
            return self.form_invalid(form, trigger_form)

    def form_valid(self, form, trigger_form):
        self.object = form.save()
        default_trigger = trigger_form.save(commit=False)
        default_trigger.name = "Default: {0}-{1}".format(self.object, self.object.id)
        default_trigger.save()
        self.object.default_trigger = default_trigger
        self.object.save()
        return redirect(self.get_success_url())

    def form_invalid(self, form, trigger_form):
        ctx = self.get_context_data(form=form, trigger_form=trigger_form)
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        context = super(ActionUpdateView, self).get_context_data(**kwargs)
        # We also list all existing actions & link to them.
        context['actions'] = Action.objects.all().select_related("behavior__title")

        # pre-populate some dynamic content displayed to the user regarding
        # an action's parent behavior.
        context['behaviors'] = Behavior.objects.values(
            "id", "description", "informal_list"
        )

        # Include a form for the default trigger
        if 'trigger_form' not in context:
            context['trigger_form'] = ActionTriggerForm(
                instance=self.object.default_trigger,
                prefix="trigger"
            )
        return context


class ActionDeleteView(ContentEditorMixin, DeleteView):
    model = Action
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    pk_url_kwarg = 'pk'
    query_pk_and_slug = True  # Use pk and slug together to identify object.
    success_url = reverse_lazy('goals:index')


class PackageListView(ContentViewerMixin, ListView):
    queryset = Category.objects.packages(published=False)
    context_object_name = 'categories'
    template_name = "goals/package_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class PackageDetailView(ContentViewerMixin, DetailView):
    queryset = Category.objects.packages(published=False)
    context_object_name = 'category'
    template_name = "goals/package_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        editor = any([
            self.request.user.is_staff,
            self.request.user.has_perm('goals.publish_category'),
            self.request.user in self.object.package_contributors.all()
        ])
        if editor:
            context['enrollments'] = self.object.packageenrollment_set.all()
        return context


# TODO: NEEDS TESTS.
class PackageEnrollmentView(ContentAuthorMixin, FormView):
    """Allow a user with *Author* permissions to automatically enroll users
    in a *package* of content. This will do the following:

    1. Create user accounts if they don't already exist.
    2. Assign users to all of the content in the package (i.e. create the
       intermediary UserAction, UserBehavior, UserGoal, and UserCategory objects)
       as if the user navigated through the app and selected them.
    3. Send the user an email letting them know they've been enrolled.

    TODO: ^^ Email needs to include link to the app in the play store; how to
    auto-enroll users in our alpha/beta test group?

    """
    template_name = "goals/package_enroll.html"
    form_class = PackageEnrollmentForm

    def get_success_url(self):
        return self.category.get_view_enrollment_url()

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.category, **self.get_form_kwargs())

    def get(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category, pk=kwargs.get('pk'))
        form = self.get_form()
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category, pk=kwargs.pop('pk', None))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # create user enrollment objects.
        goals = form.cleaned_data['packaged_goals']
        emails = form.cleaned_data['email_addresses']
        for email in emails:
            PackageEnrollment.objects.enroll_by_email(
                email,
                self.category,
                goals,
                by=self.request.user
            )
        send_package_enrollment_batch(emails, self.category, goals)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        editor = any([
            self.request.user.is_staff,
            self.request.user.has_perm('goals.publish_category'),
            self.request.user in self.category.package_contributors.all()
        ])
        if not editor:
           context['form'] = None
        return context


# TODO: NEEDS TESTS.
def accept_enrollment(request, username_hash):
    """This view lets app-users "claim" their account, set a password, & agree
    to some terms/conditions for testing. It should then enroll them in our
    Alphal/Beta-testing google group, and provide a link to the app in the app
    store, upon success.

    """
    User = get_user_model()
    try:
        user = User.objects.get(username=username_hash, is_active=False)
    except User.DoesNotExist:
        user = None

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=user, prefix="uf")
        password_form = SetNewPasswordForm(request.POST, prefix="pf")
        accept_form = AcceptEnrollmentForm(request.POST, prefix="aef")
        forms_valid = [
            user_form.is_valid(), password_form.is_valid(), accept_form.is_valid()
        ]
        if all(forms_valid):
            return redirect(reverse("goals:accept-enrollment-complete"))

    else:
        user_form = UserForm(instance=user, prefix="uf")
        password_form = SetNewPasswordForm(prefix="pf")
        accept_form = AcceptEnrollmentForm(prefix="aef")

    context = {
        'user': user,
        'user_form': user_form,
        'password_form': password_form,
        'accept_form': accept_form,
    }
    return render(request, 'goals/accept_enrollment.html', context)


class AcceptEnrollmentCompleteView(TemplateView):
    template_name = "goals/accept_enrollment_complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_url'] = settings.PLAY_APP_URL
        return context
