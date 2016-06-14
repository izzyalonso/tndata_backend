from django.core.management.base import BaseCommand, CommandError
from goals.models import Action, Behavior, Category, Goal, Trigger


class Command(BaseCommand):
    """
    This command lets you reset some value in a group of Action's default trigger.

    Example usage:

        ./manage reset_triggers --category 42 --timeofday morning
        ./manage reset_triggers --behavior 123 --frequency daily
        ./manage reset_triggers --category 42 --timeofday allday --frequency daily

    """
    help = "Reset some value for all triggers in a given Category, Goal, or Behavior"

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            action='store',
            dest='category',
            default=None,
            help="Update triggers for all actions within a Category (pk or title). "
        )
        parser.add_argument(
            '--goal',
            action='store',
            dest='goal',
            default=None,
            help="Update triggers for all actions within a Goal (pk or title). "
        )
        parser.add_argument(
            '--behavior',
            action='store',
            dest='behavior',
            default=None,
            help="Update triggers for all actions within a Behavior (pk or title). "
        )
        parser.add_argument(
            '--timeofday',
            action='store',
            dest='timeofday',
            default=None,
            help="Specify a new time of day for the trigger."
        )
        parser.add_argument(
            '--frequency',
            action='store',
            dest='frequency',
            default=None,
            help="Specify a new frequency for the trigger."
        )

    def _get_parent(self, pk_or_title, model):
        try:
            if pk_or_title and pk_or_title.isnumeric():
                return model.objects.get(pk=pk_or_title)
            elif pk_or_title:
                return model.objects.get(title__iexact=pk_or_title)
        except model.DoesNotExist:
            raise CommandError("Could not find {}: {}".format(model, pk_or_title))

    def _get_actions(self, options):
        if options['category']:
            cat = self._get_parent(options['category'], Category)
            return Action.objects.filter(behavior__goals__categories=cat).distinct()
        elif options['goal']:
            goal = self._get_parent(options['goal'], Goal)
            return Action.objects.filter(behavior__goals=goal).distinct()
        elif options['behavior']:
            behavior = self._get_parent(options['behavior'], Behavior)
            return Action.objects.filter(behavior=behavior).distinct()
        else:
            raise CommandError("Specify a parent Category, Goal, or Behavior")

    def _verify_timeofday(self, value):
        opts = [t[0] for t in Trigger.TOD_CHOICES]
        if value is not None and value not in opts:
            raise CommandError("{} is not a valid Time of Day option.".format(value))

    def _verify_frequency(self, value):
        opts = [t[0] for t in Trigger.FREQUENCY_CHOICES]
        if value is not None and value not in opts:
            raise CommandError("{} is not a valid Frequency option.".format(value))

    def handle(self, *args, **options):

        total = 0
        updated = 0

        # Ensure we've got one of the new values to be set.
        if not any([options['timeofday'], options['frequency']]):
            raise CommandError(
                "You must specify at least one of --timeofday or --frequency"
            )

        # ensure the specified values are valid
        self._verify_frequency(options['frequency'])
        self._verify_timeofday(options['timeofday'])

        for action in self._get_actions(options):
            modified = False  # Was the trigger modified?

            if action.default_trigger and options['timeofday']:
                action.default_trigger.time_of_day = options['timeofday']
                modified = True

            if action.default_trigger and options['frequency']:
                action.default_trigger.frequency = options['frequency']
                modified = True

            if modified:
                action.default_trigger.save()
                action.save()
                updated += 1

            total += 1

        self.stdout.write("Updated {} (of {}) default triggers\n".format(updated, total))