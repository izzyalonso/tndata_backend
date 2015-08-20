"""
This module contains Mixins.

"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import permission_required
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.utils.text import slugify

from rest_framework import status
from rest_framework.response import Response

from . permissions import ContentPermissions, superuser_required
from . utils import num_user_selections


# Mixins for Views
# ----------------
class DeleteMultipleMixin:
    """A Mixin that allows deleting multiple objects when a DELETE request is
    sent with a list of modelnames and object IDs.

    """
    def delete(self, request, *args, **kwargs):
        # XXX why is auth not handled by the authentication_classes, here?

        model = self.get_queryset().model
        model_name = model.__name__.lower()

        if isinstance(request.data, list) and request.user.is_authenticated():
            # We're deleting multiple items; just assume they exist?
            params = {
                "pk__in": filter(None, (d[model_name] for d in request.data)),
                "user": request.user.id,
            }
            model.objects.filter(**params).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class SuperuserRequiredMixin:
    """A Mixin that requires the user to be a superuser in order to access
    the view.
    """

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(SuperuserRequiredMixin, cls).as_view(**initkwargs)
        dec = user_passes_test(superuser_required, login_url=settings.LOGIN_URL)
        return dec(view)


class ContentViewerMixin:
    """A Mixin that requires the user have 'view_[object]' permissions for views
    with `model` or `queryset` attributes (e.g. ListView/DetailView) or that
    they be authenticated, otherwise.

    NOTE that the user must have ALL of the permissions specified.

    """

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(ContentViewerMixin, cls).as_view(**initkwargs)
        dec = permission_required(ContentPermissions.viewers, raise_exception=True)
        return dec(view)


class ContentAuthorMixin:
    """A Mixin that requires the user have the 'Authors' set of permissions.

    NOTE that the user must have ALL of the permissions specified.

    """

    _denied_message = None

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(ContentAuthorMixin, cls).as_view(**initkwargs)
        dec = permission_required(ContentPermissions.authors, raise_exception=True)
        return dec(view)

    def _object_permissions(self, request):
        """This method check's a user's permissions for the object on which
        the view is operating.

        If the user is an Author (doesn't have publish/decline permissions), they
        should have:

        * view permissions for ALL draft & published content
        * write permissions ONLY for their own draft/declined content
        * create permissions for all content

        Returns True if the user has permissions to view/update the object.

        """
        # This is a bit of a hack, but I need to differentiate if I'm updating
        # or creating an object (e.g. both also have GET requests for the form)
        # By convention, views are named [Model]UpdateView and [Model]CreateView
        updating = 'Update' in self.__class__.__name__
        creating = 'Create' in self.__class__.__name__

        if creating:  # Authors should be able to create content.
            return True

        obj = self.get_object()
        owner = request.user == obj.created_by

        # Content owners are updating their own draft/declined content.
        if owner and updating and obj.state in ['draft', 'declined']:
            return True  # OK
        elif owner:
            self._denied_message = (
                "Your content has either been Published already or is Pending "
                "Review. To continue editing this content, you will need to "
                "request that it be reset to a Draft state."
            )

        # Read-only for draft-to-published content
        if not updating and obj.state in ['draft', 'pending-review', 'published']:
            return True  # OK

        # HACK to test for Editor-like permissions.
        editor_perm = "goals.publish_{0}".format(obj.__class__.__name__.lower())
        if request.user.has_perm(editor_perm):
            return True

        return False

    def dispatch(self, request, *args, **kwargs):
        # NOTE: This mixin is only used in CreateView and UpdateView subclasses.
        if hasattr(self, 'get_object') and not self._object_permissions(request):
            ctx = {"message": self._denied_message}
            content = render_to_string("403.html", ctx)
            return HttpResponseForbidden(content=content)
        return super(ContentAuthorMixin, self).dispatch(request, *args, **kwargs)


class ContentEditorMixin:
    """A Mixin that requires the user to have the 'Editors' set of permissions.

    NOTE that the user must have ALL of the permissions specified.

    """

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(ContentEditorMixin, cls).as_view(**initkwargs)
        dec = permission_required(ContentPermissions.editors, raise_exception=True)
        return dec(view)


class ReviewableUpdateMixin:
    """This allows users to submit content for
    review. On POST, we simply check for a True `review` value once the object
    has been saved.

    """
    def get_context_data(self, **kwargs):
        """Include some information regarding the number of users that have
        selected the object, but only if it's published."""
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        if obj.is_published:
            context['num_user_selections'] = num_user_selections(obj)
        return context

    def _is_goal(self, obj):
        """Check if an object is a Goal. This method imports the goal model
        so we can still import from the models module from mixins."""
        from goals.models import Goal
        return isinstance(obj, Goal)

    def _goal_has_behaviors_in_review(self, obj):
        """Ensure this scenario is true:

        > No goal can be submitted for review until at least one child
        > behavior has been submitted for review.

        Returns True (the goes DOES have child behaviors in review) or False,
        (the goal DOES NOT have child behaviors in review).

        """
        if self._is_goal(obj):
            status = set(obj.behavior_set.values_list("state", flat=True))
            return ('pending-review' in status) or ('published' in status)
        raise TypeError("{0} is not a Goal".format(obj))

    def form_valid(self, form):
        result = super().form_valid(form)
        obj = self.object

        # If the POSTed data contains a True 'review' value, the user clicked
        # the "Submit for Review" button.
        if self.request.POST.get('review', False) and self._is_goal(obj):
            # Ensure goals have published or pending children.
            if self._goal_has_behaviors_in_review(obj):
                obj.review()  # Transition to the new state
                msg = "{0} has been submitted for review".format(obj)
                messages.success(self.request, msg)
            else:
                msg = ("This goal must have child behaviors that are either "
                       "published or in review before it can be reviewed.")
                messages.warning(self.request, msg)

        elif self.request.POST.get('review', False):
            obj.review()  # Transition to the new state
            msg = "{0} has been submitted for review".format(obj)
            messages.success(self.request, msg)

        # Record who saved the item.
        obj.save(updated_by=self.request.user)
        return result


# Mixins for Models
# -----------------
class StateMixin:
    """Convenience methods for models that use a `state` FSMField."""

    @property
    def is_draft(self):
        return self.state == "draft"

    @property
    def is_pending(self):
        return self.state == "pending-review"

    @property
    def is_declined(self):
        return self.state == "declined"

    @property
    def is_published(self):
        return self.state == "published"


class ModifiedMixin:
    def _check_updated_or_created_by(self, **kwargs):
        """Allows passing `updated_by` or `created_by` paramters in a model's
        save() method.

        USAGE: override `save` in a model and call:

            _check_updated_or_created_by(**kwargs)

        """
        updated_by = kwargs.pop("updated_by", None)
        if updated_by:
            self.updated_by = updated_by
        created_by = kwargs.pop("created_by", None)
        if created_by:
            self.created_by = created_by
        return kwargs


class UniqueTitleMixin:
    """Titles should be unique, and their slugs should also be unique. However,
    since slugs are not displayed in forms, it's possible to have a title that
    who's slug clashes with another, e.g.:

        "This title" and "this TITLE" would both have a slug of "this-title"

    This mixin overrides the model's `validate_unique` to check the slugified
    title and raise an exception if that's not unique.

    Requires that the class have both a `title` and a `title_slug` field.

    """
    def validate_unique(self, *args, **kwargs):
        super(UniqueTitleMixin, self.__class__).validate_unique(
            self, *args, **kwargs
        )
        if not self.id:
            slug = slugify(self.title)
            if self.__class__.objects.filter(title_slug=slug).exists():
                msg = '{0} with this Title already exists.'
                raise ValidationError(
                    {'title': [msg.format(self.__class__.__name__)]}
                )


class URLMixin:
    """Contains methods for reversing Model URLs. This Mixin DRYs up the various
    get_XXXX_url methods that I use on models, particularly for Read, Update,
    and Delete actions.

    Models using this mixin can customize its behavior by specifying the
    following:

    * (required) urls_app_namespace: The url namespace used for the app
    * (required) urls_model_name: The model name used for the url
    * urls_slug_field: The unique slug used for the model. Default is `title_slug`
    * urls_fields: A list of field names used to reverse the model's urls. This
      takes precendence over `urls_slug_field`, and is used when a Model requires
      more than one field for it's urls: e.g. [`pk`, `title_slug`]
    * urls_icon_field: An icon field for the model. Defaut is None.
    * urls_image_field: An image field for the model. Defaut is None.

    This mixin also supports a default icon or image as a static file. To use
    this, just set one of the following:

    * default_icon:  e.g. `default_icon = "img/compass-grey.png"`
    * default_image: e.g. `default_image = "img/compass-icon.png"`

    And we make the assumption that we have the following URLs defined, e.g.
    for the Category model:

    * Read: category-detail
    * Update: category-update
    * Delete: category-delete

    """
    urls_app_namespace = None  # e.g. 'goals'
    urls_model_name = None  # e.g. 'category'
    urls_slug_field = "title_slug"  # e.g. 'name_slug', if different.
    urls_fields = None  # Allow mutiple fields for urls e.g. [pk, title_slug]
    urls_icon_field = None
    urls_image_field = None

    # Support for default icons/images as a static file
    default_icon = None
    default_image = None

    def _url_args(self):
        if self.urls_fields:
            return [
                getattr(self, field, None) for field in self.urls_fields
            ]
        else:
            return [self._slug_field()]

    def _slug_field(self):
        return getattr(self, self.urls_slug_field, None)

    def _view(self, view_name):
        if self.urls_app_namespace is None or self.urls_model_name is None:
            raise ImproperlyConfigured(
                "Models using URLMixin must define both urls_app_namespace and "
                "urls_model_name."
            )
        return "{0}:{1}-{2}".format(
            self.urls_app_namespace, self.urls_model_name, view_name
        )

    def get_absolute_url(self):
        return reverse(self._view('detail'), args=self._url_args())

    def get_publish_url(self):
        return reverse(self._view('publish'), args=self._url_args())

    def get_update_url(self):
        return reverse(self._view('update'), args=self._url_args())

    def get_delete_url(self):
        return reverse(self._view('delete'), args=self._url_args())

    def get_duplicate_url(self):
        return reverse(self._view('duplicate'), args=self._url_args())

    def get_absolute_icon(self):
        icon_field = getattr(self, self.urls_icon_field, None)
        if self.urls_icon_field and icon_field:
            return icon_field.url
        elif self.default_icon:
            return static(self.default_icon)

    def get_absolute_image(self):
        image_field = getattr(self, self.urls_image_field, None)
        if self.urls_image_field and image_field:
            return image_field.url
        elif self.default_image:
            return static(self.default_image)
