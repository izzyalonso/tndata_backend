from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from goals.models import GoalProgress


class Command(BaseCommand):
    help = 'Creates GoalProgress objects. Run Nightly'

    def handle(self, *args, **options):
        User = get_user_model()
        for user in User.objects.filter(usergoal__isnull=False).distinct():
            GoalProgress.objects.generate_scores(user)
