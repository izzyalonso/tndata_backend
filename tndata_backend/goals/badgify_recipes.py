"""
Badgify Recipes.

See: https://github.com/ulule/django-badgify

----

IMPLEMENTATION

1. _X_ Create recipes as part of the goals app.
2. _X_ Listen for signals (Award.post_save?) and send a push notification when
       a user is awarded a badge. (wrap this in a waffle.switch)
3. _X_ New app (badge_api?) that exposes a user's awarded badges
4. _X_ Cron jobs that will run the badgify_sync commands to do awards

----

WORKFLOW

Typical workflow for best performances:

    $ python manage.py badgify_sync badges  # Creates badges from recipes
    $ python manage.py badgify_sync counts  # Denorm. counts (for performance)

# This one awards the badges, we need to run it more frequently, but we may
# also need the signals (which will make it slower)

TODO: This is currently only scheduled in staging, we need to schedul these
      in production/worker.

    $ python manage.py badgify_sync awards --disable-signals


UPDATING BADGE IMAGES

If we need to update badge images, perform the following steps:

1. run collectstatic (part of deployment)
2. run badgify_sync badges --update


----

NOTE on Recipes; A recipe class must implement:

_ name class attribute
    The badge name (humanized).
- image property
    The badge image/logo as a file object.

Optionally, A recipe class may implement:

- slug class attribute
    The badge slug (used internally and in URLs). If not provided, it
    will be auto-generated based on the badge name.
- description class attribute
    The badge description (short). It not provided, value will be blank.
- user_ids property
    QuerySet returning User IDs likely to be awarded. You must return a
    QuerySet and not just a Python list or tuple. You can use
    values_list('id', flat=True).
- db_read class attribute
    The database alias on which to perform read queries. Defaults to
    django.db.DEFAULT_DB_ALIAS.
- batch_size class attribute
    How many Award objects to create at once. Defaults to
    BADGIFY_BATCH_SIZE (500).

"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import Case, Count, IntegerField, When
from django.utils import timezone

from badgify.recipe import BaseRecipe
import badgify

from .models import DailyProgress

from utils import dateutils


# ----------------
# Helper functions
# ----------------

def just_joined(minutes=None, days=None):
    """Return a QuerySet (a ValuesListQuerySet, actually) of users whose
    accounts were created either within the past `minutes` or on the day of
    `days` ago.

    """
    User = get_user_model()
    users = User.objects.none()
    if days:
        # Return all users who joined within the given day
        since = timezone.now() - timedelta(days=days)
        joined_on = dateutils.date_range(since)
        users = User.objects.filter(date_joined__range=joined_on)
    elif minutes:
        # Return all users who've joined in a 10-minute window at the given time
        since = timezone.now() - timedelta(minutes=minutes)
        users = User.objects.filter(date_joined__gte=since)
    return users.values_list("id", flat=True)


def just_logged_in(nth, minutes=10):
    """Return a QuerySet (a ValuesListQuerySet) of users who've logged in for
    the `nth` time (within the past few `minutes`)."""
    User = get_user_model()
    since = timezone.now() - timedelta(minutes=minutes)
    users = User.objects.filter(last_login__gte=since, userprofile__app_logins=nth)
    return users.values_list("id", flat=True)


def checkin_streak(streak_number, badge_slug):
    """Return a queryset of Users that have the a checkin-streak of
    `streak_number`, but have not received this specified badge, yet."""
    User = get_user_model()

    today = dateutils.date_range(timezone.now())
    user_ids = DailyProgress.objects.filter(
        created_on__range=today,
        checkin_streak=streak_number
    ).values_list("user", flat=True).distinct()

    users = User.objects.filter(pk__in=user_ids)
    users = users.exclude(badges__badge__slug=badge_slug).distinct()
    return users.values_list("id", flat=True)


# -------------------------
# General App-usage recipes
# -------------------------

class SignupMixin:
    minutes_since_signup = None
    days_since_signup = None
    badge_path = 'badges/placeholder.png'

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        """Returns a queryset of users who joined within the past 10 minutes"""
        return just_joined(
            minutes=self.minutes_since_signup,
            days=self.days_since_signup
        )


class StarterRecipe(SignupMixin, BaseRecipe):
    """Awarded when signing up (hopefully about the time they view the feed)."""
    name = 'Starter'
    slug = 'starter'
    description = "Congrats on signing up! You're on your way to success!"
    badge_path = 'badges/glob-01-starter.png'
    minutes_since_signup = 10
badgify.register(StarterRecipe)


class ExplorerRecipe(SignupMixin, BaseRecipe):
    """Awarded when the user has been signed up for a week."""
    name = 'Explorer'
    slug = 'explorer'
    description = "You've used Compass for a week! Woo-hoo!"
    badge_path = 'badges/glob-06-explorer.png'
    days_since_signup = 7
badgify.register(ExplorerRecipe)


class LighthouseRecipe(SignupMixin, BaseRecipe):
    """Awarded when the user has been signed up for a month."""
    name = 'Lighthouse'
    slug = 'lighthouse'
    description = "You've used Compass for a month! Woo-hoo!"
    badge_path = 'badges/placeholder.png'
    days_since_signup = 30
# badgify.register(LighthouseRecipe)


class LoginMixin:
    minutes_since_login = None
    login_number = None
    badge_path = 'badges/placeholder.png'

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        since = self.minutes_since_login or 10
        return just_logged_in(self.login_number, minutes=since)


class HomecomingRecipe(LoginMixin, BaseRecipe):
    """Awarded by coming back to the app a second time."""
    name = 'Homecoming'
    slug = 'homecoming'
    description = "Congrats for coming back."
    badge_path = 'badges/glob-02-homecoming.png'
    login_number = 2
badgify.register(HomecomingRecipe)


class SeekerRecipe(LoginMixin, BaseRecipe):
    """Awarded by coming back to the app (a third time)"""
    name = 'Seeker'
    slug = 'seeker'
    description = "Congrats for coming back the third time."
    badge_path = 'badges/glob-03-seeker.png'
    login_number = 3
badgify.register(SeekerRecipe)


class PathfinderRecipe(LoginMixin, BaseRecipe):
    """Awarded by coming back to the app (a seventh time)"""
    name = 'Pathfinder'
    slug = 'pathfinder'
    description = "Congrats for coming back the seventh time."
    login_number = 7
    badge_path = 'badges/glob-04-pathfinder.png'
badgify.register(PathfinderRecipe)


class NavigatorRecipe(LoginMixin, BaseRecipe):
    """Awarded by coming back to the app (a 14th time)"""
    name = 'Navigator'
    slug = 'navigator'
    description = "Congrats for coming back the fourteenth time."
    login_number = 14
    badge_path = 'badges/glob-05-navigator.png'
badgify.register(NavigatorRecipe)


# TODO: Scout -- After leaving the "total badges" activities
# ----------------------------------------------------------
# class ScoutRecipe(BaseRecipe):
#     """Awarded by coming back to the app (a 14th time)"""
#     name = 'Scout'
#     slug = 'scout'
#     description = "You're awesome for checking your stats!"
#
#     @property
#     def image(self):
#         return staticfiles_storage.open('badges/placeholder.png')
#
#     @property
#     def user_ids(self):
#         # TODO: How to do this?
#
# badgify.register(NavigatorRecipe)


# ------------------------------
# Self-report / Check-in recipes
# ------------------------------

class CheckinMixin:
    badge_path = 'badges/placeholder.png'  # Path to the badge.
    checkin_days = 1  # Number days in a row the user has checked in.

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        return checkin_streak(self.checkin_days, self.slug)


class ThoughtfulRecipe(CheckinMixin, BaseRecipe):
    name = 'Thoughtful'
    slug = 'thoughtful'
    description = "This was your first time checking in! You're awesome!"
    badge_path = 'badges/placeholder.png'
    checkin_days = 1
# badgify.register(ThoughtfulRecipe)


class ConscientiousRecipe(CheckinMixin, BaseRecipe):
    name = 'Conscientious'
    slug = 'conscientious'
    description = "This was your second time checking in! You're taking care of yourself!"
    badge_path = 'badges/placeholder.png'
    checkin_days = 2
# badgify.register(ConscientiousRecipe)


class StreakThreeDaysRecipe(CheckinMixin, BaseRecipe):
    name = 'Streak - three days!'
    slug = 'streak-three-days'
    description = "You've checked in three times in a row! Score!"
    badge_path = 'badges/placeholder.png'
    checkin_days = 3
# badgify.register(StreakThreeDaysRecipe)


class StreakFiveDaysRecipe(CheckinMixin, BaseRecipe):
    name = 'Streak - five days!'
    slug = 'streak-five-days'
    description = "You've checked in five times in a row! Way to go!"
    badge_path = 'badges/placeholder.png'
    checkin_days = 3
# badgify.register(StreakFiveDaysRecipe)


class StreakOneWeekRecipe(CheckinMixin, BaseRecipe):
    name = 'Streak - one week!'
    slug = 'streak-one-week'
    description = "You've checked in seven times in a row! Keep up the streak!"
    badge_path = 'badges/placeholder.png'
    checkin_days = 7
# badgify.register(StreakOneWeekRecipe)


class StreakTwoWeeksRecipe(CheckinMixin, BaseRecipe):
    name = 'Streak - two weeks!'
    slug = 'streak-two-weeks'
    description = "You've checked in every day for two weeks! Score!"
    badge_path = 'badges/placeholder.png'
    checkin_days = 14
# badgify.register(StreakTwoWeeksRecipe)


class StreakThreeWeeksRecipe(CheckinMixin, BaseRecipe):
    name = 'Streak - three weeks!'
    slug = 'streak-three-weeks'
    description = "You've checked in every day for three weeks! Score!"
    badge_path = 'badges/placeholder.png'
    checkin_days = 21
# badgify.register(StreakThreeWeeksRecipe)


class StreakFourWeeksRecipe(CheckinMixin, BaseRecipe):
    name = 'Streak - four weeks!'
    slug = 'streak-four-weeks'
    description = "You've checked in every day for four weeks! Score!"
    badge_path = 'badges/placeholder.png'
    checkin_days = 28
# badgify.register(StreakFourWeeksRecipe)


# -----------------------------------
# Package Enrollment & Goal Selection
# -----------------------------------


class ParticipantRecipe(BaseRecipe):
    """Awarded when a user accepts their pacakge enrollment (i.e. a
    PackageEnrollment object is `accepted` within the past 10 minutes.)"""
    name = 'Participant'
    slug = 'participant'
    # Wanted: 'Congrats on joining <package>!'
    description = "Congrats on joining your first package!"

    @property
    def image(self):
        return staticfiles_storage.open('badges/placeholder.png')

    @property
    def user_ids(self):
        User = get_user_model()
        since = timezone.now() - timedelta(minutes=10)

        users = User.objects.annotate(num_packages=Count('packageenrollment'))
        users = users.filter(
            num_packages=1,
            packageenrollment__accepted=True,
            packageenrollment__updated_on__gte=since
        )
        return users.values_list('id', flat=True)
# badgify.register(ParticipantRecipe)


class UserGoalCountMixin:
    """A mixin that counts a user's selected (non-package) goals.

    NOTE: The UserGoal.primary_category is used to exclude goals that are
    part of a packge. Unfortunately, if a user selects a goal that is public,
    but also part of a package, this won't count toward their receiving a badge.

    """
    badge_path = 'badges/placeholder.png'  # Path to the badge.
    num_usergoals = 1  # Number of goals the user has selected.

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        User = get_user_model()
        since = timezone.now() - timedelta(minutes=10)

        # Annote a queryset of users with the number of non-packaged UserGoals.
        users = User.objects.annotate(
            num_nonpackage_usergoals=Case(
                When(
                    usergoal__primary_category__packaged_content=False,
                    then=Count('usergoal')
                ),
                default=0,
                output_field=IntegerField()
            )
        ).distinct()

        # Now filter based on the specified number of selections.
        users = users.filter(
            num_nonpackage_usergoals=self.num_usergoals,
            usergoal__created_on__gte=since
        )
        return users.values_list("id", flat=True)


class GoalSetterRecipe(UserGoalCountMixin, BaseRecipe):
    # Goal-setter -- Enroll in first non-package goal
    name = 'Goal-setter'
    slug = 'goal-setter'
    description = "Congrats on setting your first goal!"
    badge_path = 'badges/goal-01-goalsetter.png'
    num_usergoals = 1
badgify.register(GoalSetterRecipe)


class StriverRecipe(UserGoalCountMixin, BaseRecipe):
    # Striver -- Enroll in second non-package goal
    name = 'Striver'
    slug = 'striver'
    description = "Congrats on setting your second goal!"
    badge_path = 'badges/goal-02-striver.png'
    num_usergoals = 2
badgify.register(StriverRecipe)


class AchieverRecipe(UserGoalCountMixin, BaseRecipe):
    # Achiever -- Enroll in fourth non-package goal
    name = 'Achiever'
    slug = 'achiever'
    description = "Congrats on setting your fourth goal!"
    badge_path = 'badges/goal-03-achiever.png'
    num_usergoals = 4
badgify.register(AchieverRecipe)


class HighFiveRecipe(UserGoalCountMixin, BaseRecipe):
    # High Five -- Enroll in fifth non-package goal
    name = 'High five'
    slug = 'high-five'
    description = "Congrats on setting your fifth goal!"
    badge_path = 'badges/goal-04-highfive.png'
    num_usergoals = 5
badgify.register(HighFiveRecipe)


class PerfectTenRecipe(UserGoalCountMixin, BaseRecipe):
    # Perfect ten -- Enroll in tenth non-package goal
    name = 'Perfect ten'
    slug = 'perfect-ten'
    description = "Congrats on setting your tenth goal!"
    badge_path = 'badges/goal-05-perfectten.png'
    num_usergoals = 10
badgify.register(PerfectTenRecipe)


class SuperstarRecipe(UserGoalCountMixin, BaseRecipe):
    # Superstar -- Enroll in twentieth non-package goal
    name = 'Superstar'
    slug = 'superstar'
    description = "Congrats on setting your twentieth goal!"
    badge_path = 'badges/goal-06-superstar.png'
    num_usergoals = 20
badgify.register(SuperstarRecipe)


# -----------------------------------------------------------------------------
# Goal/Behavior/Action *Custom* Completions...
# -----------------------------------------------------------------------------
#
# Additional ideas, here:
# -X- when users complete an Action (ie. create UserComplatedAction objects)
# -X- when users complete a Behavior (all actions within a behavior)
# -X- when users complete a Goal (all behaviors within a goal are completed)
# --- when users create a Custom Goal
# --- when users complete a Custom Action
# -----------------------------------------------------------------------------


class UserCompletedActionCountMixin:
    """A mixin that counts a user's completed Actions.

    """
    badge_path = 'badges/placeholder.png'  # Path to the badge.
    num_completed = 1  # Number of UserCompletedActions for the user

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        User = get_user_model()
        since = timezone.now() - timedelta(minutes=10)

        # Find users that have completed an Action within the past 10 minutes.
        # TODO: check that the state == "completed"
        users = User.objects.filter(usercompletedaction__created_on__gte=since)
        users = users.distinct()
        users = users.annotate(num_ucas=Count('usercompletedaction'))
        users = users.filter(num_ucas=self.num_completed)
        return users.values_list("id", flat=True)


class FirstTimerRecipe(UserCompletedActionCountMixin, BaseRecipe):
    """First 'got it' for *any* goal"""
    name = 'First Timer'
    slug = 'first-timer'
    description = "Congrats on your first activity! Keep up the good work!"
    badge_path = 'badges/action-01-firsttimer.png'
    num_completed = 1
badgify.register(FirstTimerRecipe)


class TwoFerRecipe(UserCompletedActionCountMixin, BaseRecipe):
    name = 'Two-fer'
    slug = 'two-fer'
    description = "Congrats on your second activity!"
    badge_path = 'badges/action-02-twofer.png'
    num_completed = 2
badgify.register(TwoFerRecipe)


class TrioRecipe(UserCompletedActionCountMixin, BaseRecipe):
    name = 'Trio'
    slug = 'trio'
    description = "Congrats on your third activity!"
    badge_path = 'badges/action-03-trio.png'
    num_completed = 3
badgify.register(TrioRecipe)


class ActionHighFiveRecipe(UserCompletedActionCountMixin, BaseRecipe):
    name = 'High Fives'
    slug = 'high-fives'
    description = "Congrats on your fifth activity!"
    badge_path = 'badges/action-04-highfive.png'
    num_completed = 5
badgify.register(ActionHighFiveRecipe)


class TenSpotRecipe(UserCompletedActionCountMixin, BaseRecipe):
    name = 'Ten Spot'
    slug = 'ten-spot'
    description = "Congrats on ten activities!"
    badge_path = 'badges/action-05-tenspot.png'
    num_completed = 10
badgify.register(TenSpotRecipe)


class UserCompletedBehaviorCountMixin:
    """A mixin that counts a user's completed Behaviors.

    """
    badge_path = 'badges/placeholder.png'  # Path to the badge.
    num_completed = 1  # Number of UserBehavior's marked complete

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        User = get_user_model()
        since = timezone.now() - timedelta(minutes=10)

        # Find users that have completed a Behavior within the past 10 minutes.
        users = User.objects.filter(
            userbehavior__completed=True,
            userbehavior__completed_on__gte=since
        ).distinct()
        users = users.annotate(num_completed=Count('userbehavior'))
        users = users.filter(num_completed=self.num_completed)
        return users.values_list("id", flat=True)


class BehaviorCompletedRecipe(UserCompletedBehaviorCountMixin, BaseRecipe):
    name = 'Wayfarer'
    slug = 'wayfarer'
    description = "Congrats on completing a set of actions!"
    badge_path = 'badges/placeholder.png'
    num_completed = 1
# badgify.register(BehaviorCompletedRecipe)
# TODO: more behavior completion badges.


class UserCompletedGoalCountMixin:
    """A mixin that counts a user's completed Goals.

    """
    badge_path = 'badges/placeholder.png'  # Path to the badge.
    num_completed = 1  # Number of UserGoals's marked complete

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        User = get_user_model()
        since = timezone.now() - timedelta(minutes=10)

        # Find users that have completed a Goal within the past 10 minutes.
        users = User.objects.filter(
            usergoal__completed=True,
            usergoal__completed_on__gte=since
        ).distinct()
        users = users.annotate(num_completed=Count('usergoal'))
        users = users.filter(num_completed=self.num_completed)
        return users.values_list("id", flat=True)


# TODO: What to name Goal Completion goals & more of these
class GoalCompletedRecipe(UserCompletedGoalCountMixin, BaseRecipe):
    name = 'Voyager'
    slug = 'voyager'
    description = "Congrats on completing every action in a Goal!"
    badge_path = 'badges/placeholder.png'
    num_completed = 1
# badgify.register(GoalCompletedRecipe)


class UserCreatedCustomGoalCountMixin:
    """A mixin that counts a user's CustomGoals when one is created.

    """
    badge_path = 'badges/placeholder.png'  # Path to the badge.
    num_custom_goals = 1

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        User = get_user_model()
        since = timezone.now() - timedelta(minutes=10)

        # Find users that have created a Custom Goal within the past 10 minutes.
        users = User.objects.filter(customgoal__created_on__gte=since)
        users = users.annotate(num_cgs=Count('customgoal'))
        # And then filter down to users that have the specified number
        users = users.filter(num_cgs=self.num_custom_goals).distinct()
        return users.values_list("id", flat=True)


# TODO: What to name Custom Goal Creation badges? More of these
class CustomGoalCreatedRecipe(UserCreatedCustomGoalCountMixin, BaseRecipe):
    name = 'Captain'
    slug = 'captain'
    description = "Congrats on creating your first Custom Goal!"
    badge_path = 'badges/placeholder.png'
    num_completed = 1
# badgify.register(CustomGoalCreatedRecipe)


class UserCompletedCustomActionCountMixin:
    """A mixin that counts a user's completed custom actions.

    """
    badge_path = 'badges/placeholder.png'  # Path to the badge.
    num_completed = 1

    @property
    def image(self):
        return staticfiles_storage.open(self.badge_path)

    @property
    def user_ids(self):
        User = get_user_model()
        since = timezone.now() - timedelta(minutes=10)

        # Find users that have completed a custom action
        users = User.objects.filter(
            usercompletedcustomaction__created_on__gte=since)

        # TODO: check that the state == completed.
        users = users.annotate(num_completed=Count('usercompletedcustomaction'))
        users = users.filter(num_completed=self.num_completed).distinct()
        return users.values_list("id", flat=True)


# TODO: What to name Custom Action Completion badges? More of these
class CustomActionCompletedRecipe(UserCompletedCustomActionCountMixin, BaseRecipe):
    name = 'Doer'
    slug = 'doer'
    description = "Congrats on creating your first Custom Action!"
    badge_path = 'badges/placeholder.png'
    num_completed = 1
# badgify.register(CustomActionCompletedRecipe)
