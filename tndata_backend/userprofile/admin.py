from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from . import models

from utils.admin import UserRelatedModelAdmin


def remove_app_data(modeladmin, request, queryset):
    """Remove a user's selected content from the mobile app. This essentialy
    deletes their: UserAction, UserBehavior, UserCategory, PackageEnrollment,
    Trigger, UserCompletedAction, DailyProgress instances as well as their
    GCMMessages (which should also clear their queue)

    See: userprofile.views.admin_remove_app_data

    """
    ids = "+".join(str(obj.id) for obj in queryset)
    url = "{}?ids={}".format(reverse("userprofile:remove-app-data"), ids)
    # Include the user's original query, too
    if request.GET.get('q'):
        url += "&q={}".format(request.GET['q'])
    return HttpResponseRedirect(url)
remove_app_data.short_description = "Remove App Data"


class PlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'updated_on', 'created_on')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name',)
admin.site.register(models.Place, PlaceAdmin)


class UserPlaceAdmin(UserRelatedModelAdmin):
    list_display = ('user', 'user_email', 'user_first', 'user_last', 'place')
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'place__name',
    )
admin.site.register(models.UserPlace, UserPlaceAdmin)


class UserProfileAdmin(UserRelatedModelAdmin):
    list_display = (
        'user_email', 'user_first', 'user_last', 'timezone',
        'needs_onboarding', 'zipcode', 'ip_address',
    )
    list_filter = (
        'zipcode', 'sex', 'employed', 'is_parent',
        'in_relationship', 'has_degree',
        'timezone',
    )
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
    )
    actions = [remove_app_data]
admin.site.register(models.UserProfile, UserProfileAdmin)


class UserProfileInline(admin.StackedInline):
    model = models.UserProfile
    fields = (
        'timezone', 'maximum_daily_notifications',
        'needs_onboarding', 'zipcode', 'birthday', 'sex', 'employed',
        'is_parent', 'in_relationship', 'has_degree', 'ip_address',
    )
    readonly_fields = (
        'ip_address', 'zipcode', 'birthday', 'sex', 'employed',
        'is_parent', 'in_relationship', 'has_degree',
    )


class CustomUserAdmin(UserAdmin):
    """Override the default UserAdmin class so we can attach a custom action."""
    actions = [remove_app_data]
    list_display = ('email', 'full_name', 'is_staff', 'date_joined', 'username')
    inlines = [UserProfileInline]

    def full_name(self, obj):
        return obj.get_full_name()
    full_name.admin_order_field = 'first_name'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
