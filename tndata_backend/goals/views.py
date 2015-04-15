from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import redirect, render
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from . forms import (
    ActionForm,
    BehaviorForm,
    CSVUploadForm,
    GoalForm,
    TriggerForm,
)
from . mixins import ContentAuthorMixin, ContentEditorMixin
from . models import (
    Action, Behavior, Category, Goal, Trigger
)
from . permissions import superuser_required
from utils.db import get_max_order


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


class IndexView(ContentAuthorMixin, TemplateView):
    template_name = "goals/index.html"

    def get(self, request, *args, **kwargs):
        """Include info on pending and declined content items."""
        context = self.get_context_data(**kwargs)
        if request.user.is_staff:  # TODO: check for Editor group/permissions?
            context['categories'] = Category.objects.filter(state='pending-review')
            context['goals'] = Goal.objects.filter(state='pending-review')
            context['behaviors'] = Behavior.objects.filter(state='pending-review')
            context['actions'] = Action.objects.filter(state='pending-review')
        return self.render_to_response(context)


class CategoryListView(ContentAuthorMixin, ListView):
    model = Category
    context_object_name = 'categories'
    template_name = "goals/category_list.html"


class CategoryDetailView(ContentAuthorMixin, DetailView):
    queryset = Category.objects.all()
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"


class CategoryCreateView(ContentEditorMixin, CreateView):
    model = Category
    fields = ['order', 'title', 'description', 'icon', 'notes']

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


class CategoryUpdateView(ContentEditorMixin, UpdateView):
    model = Category
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    fields = ['order', 'title', 'description', 'icon', 'notes']

    def get_context_data(self, **kwargs):
        context = super(CategoryUpdateView, self).get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class CategoryDeleteView(ContentEditorMixin, DeleteView):
    model = Category
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    success_url = reverse_lazy('goals:index')


class GoalListView(ContentAuthorMixin, ListView):
    model = Goal
    context_object_name = 'goals'


class GoalDetailView(ContentAuthorMixin, DetailView):
    queryset = Goal.objects.all()
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"


class GoalCreateView(ContentAuthorMixin, CreateView):
    model = Goal
    form_class = GoalForm

    def get_context_data(self, **kwargs):
        context = super(GoalCreateView, self).get_context_data(**kwargs)
        context['goals'] = Goal.objects.all()
        return context


class GoalUpdateView(ContentAuthorMixin, UpdateView):
    model = Goal
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    form_class = GoalForm

    def get_context_data(self, **kwargs):
        context = super(GoalUpdateView, self).get_context_data(**kwargs)
        context['goals'] = Goal.objects.all()
        return context


class GoalDeleteView(ContentEditorMixin, DeleteView):
    model = Goal
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    success_url = reverse_lazy('goals:index')


class TriggerListView(ContentAuthorMixin, ListView):
    model = Trigger
    context_object_name = 'triggers'


class TriggerDetailView(ContentAuthorMixin, DetailView):
    queryset = Trigger.objects.all()
    slug_field = "name_slug"
    slug_url_kwarg = "name_slug"


class TriggerCreateView(ContentEditorMixin, CreateView):
    model = Trigger
    form_class = TriggerForm

    def get_context_data(self, **kwargs):
        context = super(TriggerCreateView, self).get_context_data(**kwargs)
        context['triggers'] = Trigger.objects.all()
        return context


class TriggerUpdateView(ContentEditorMixin, UpdateView):
    model = Trigger
    form_class = TriggerForm
    slug_field = "name_slug"
    slug_url_kwarg = "name_slug"

    def get_context_data(self, **kwargs):
        context = super(TriggerUpdateView, self).get_context_data(**kwargs)
        context['triggers'] = Trigger.objects.all()
        return context


class TriggerDeleteView(ContentEditorMixin, DeleteView):
    model = Trigger
    slug_field = "name_slug"
    slug_url_kwarg = "name_slug"
    success_url = reverse_lazy('goals:index')


class BehaviorListView(ContentAuthorMixin, ListView):
    model = Behavior
    context_object_name = 'behaviors'


class BehaviorDetailView(ContentAuthorMixin, DetailView):
    queryset = Behavior.objects.all()
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"


class BehaviorCreateView(ContentAuthorMixin, CreateView):
    model = Behavior
    form_class = BehaviorForm

    def get_context_data(self, **kwargs):
        context = super(BehaviorCreateView, self).get_context_data(**kwargs)
        context['behaviors'] = Behavior.objects.all()
        return context


class BehaviorUpdateView(ContentAuthorMixin, UpdateView):
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


class ActionListView(ContentAuthorMixin, ListView):
    model = Action
    context_object_name = 'actions'


class ActionDetailView(ContentAuthorMixin, DetailView):
    queryset = Action.objects.all()
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"


class ActionCreateView(ContentAuthorMixin, CreateView):
    model = Action
    form_class = ActionForm

    def get_context_data(self, **kwargs):
        context = super(ActionCreateView, self).get_context_data(**kwargs)
        context['actions'] = Action.objects.all()
        context['behaviors'] = Behavior.objects.all()
        return context


class ActionUpdateView(ContentAuthorMixin, UpdateView):
    model = Action
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    form_class = ActionForm

    def get_context_data(self, **kwargs):
        context = super(ActionUpdateView, self).get_context_data(**kwargs)
        context['actions'] = Action.objects.all()
        context['behaviors'] = Behavior.objects.all()
        return context


class ActionDeleteView(ContentEditorMixin, DeleteView):
    model = Action
    slug_field = "title_slug"
    slug_url_kwarg = "title_slug"
    success_url = reverse_lazy('goals:index')
