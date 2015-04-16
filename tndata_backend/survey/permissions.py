from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from rest_framework import permissions

SURVEY_ADMINS = "Survey Admins"  # Name of the group containing survey admins.


class IsOwner(permissions.BasePermission):
    """This permission checks that the authenticated user is the owner a given
    object. For this to work, the object MUST have a `user` attribute.

    """

    def has_object_permission(self, request, view, obj):
        try:
            return request.user.is_authenticated() and obj.user == request.user
        except AttributeError:
            return False


def is_survey_admin(user):
    """Verifies that a user is authenticated and a super user."""
    if not user.is_authenticated():
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name=SURVEY_ADMINS).exists()


class SurveyAdminsMixin(object):
    """A Mixin that requires the user to be in a "Survey Admins" Group."""
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(SurveyAdminsMixin, cls).as_view(**initkwargs)
        dec = user_passes_test(is_survey_admin, login_url=settings.LOGIN_URL)
        return dec(view)
