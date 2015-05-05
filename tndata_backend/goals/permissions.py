"""
This module provides permissions and Group-based tools. This app defines
custom groups for people who create and review content:


1. Content Viewers: Have read-only permissions for content models: Category,
   Goals, Behaviors, Actions.
2. Content Authors: Have Read, create, update permissions for content models;
   (Goals, Behaviors, Actions) and read for Categories.
3. Content Editors: Have the above plus the ability to delete and publish or
   decline content created by authors.

"""
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group, Permission

# Group Names
CONTENT_AUTHORS = "Content Authors"
CONTENT_EDITORS = "Content Editors"
CONTENT_VIEWERS = "Content Viewers"


def get_or_create_content_authors():
    """Creates the 'Content Authors' Group if it doesn't exist, and assigns
    the appropriate permissions to that group.

    """
    group, created = Group.objects.get_or_create(name=CONTENT_AUTHORS)
    perms = [
        "view_category",
        "view_trigger",
    ]
    for obj in ['goal', 'behavior', 'action']:
        perms.append("add_{0}".format(obj))
        perms.append("change_{0}".format(obj))
        perms.append("view_{0}".format(obj))
    for p in Permission.objects.filter(codename__in=perms):
        group.permissions.add(p)
    group.save()
    return group


def get_or_create_content_editors():
    """Creates the 'Content Editors' Group if it doesn't exist, and assigns the
    appropriate permissions.

    """
    group, created = Group.objects.get_or_create(name=CONTENT_EDITORS)
    perms = []
    for obj in ['category', 'goal', 'behavior', 'action', 'trigger']:
        perms.append("add_{0}".format(obj))
        perms.append("change_{0}".format(obj))
        perms.append("decline_{0}".format(obj))
        perms.append("delete_{0}".format(obj))
        perms.append("publish_{0}".format(obj))
        perms.append("view_{0}".format(obj))
    for p in Permission.objects.filter(codename__in=perms):
        group.permissions.add(p)
    group.save()
    return group


def get_or_create_content_viewers(apps=None, schema_editor=None):
    """Creates the 'Content Viewers' Group if it doesn't exist, and assigns the
    appropriate permissions.

    """
    group, created = Group.objects.get_or_create(name=CONTENT_VIEWERS)
    perms = []
    for obj in ['category', 'goal', 'behavior', 'action', 'trigger']:
        perms.append("view_{0}".format(obj))
    for p in Permission.objects.filter(codename__in=perms):
        group.permissions.add(p)
    group.save()
    return group


# --------------------------
# Permission Check Functions
# --------------------------

def superuser_required(user):
    """Verifies that a user is authenticated and a super user."""
    return user.is_authenticated() and user.is_superuser


def _is_superuser_or_in_group(user, group_name):
    """Checks for the following conditions:

    1. User is authenticated.
    2. User is a superuser, OR
    3. User is in the specified group.

    """
    return user.is_authenticated() and (
        user.is_superuser or user.groups.filter(name=group_name).exists()
    )


def is_content_author(user):
    """Verifies that a user is authenticated and a content author (or an editor
    since editors get all author permissions as well)."""
    author = _is_superuser_or_in_group(user, CONTENT_AUTHORS)
    editor = _is_superuser_or_in_group(user, CONTENT_EDITORS)
    return (author or editor)


def is_content_editor(user):
    """Verifies that a user is authenticated and a content editor."""
    return _is_superuser_or_in_group(user, CONTENT_EDITORS)
