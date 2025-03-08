from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta
from chat.models import ChatMessage  # Import your Message model


class Command(BaseCommand):
    help = "Delete chat messages older than 6 months"

    def handle(self, *args, **kwargs):
        threshold_date = now() - timedelta(days=180)  # 6 months
        old_messages = ChatMessage.objects.filter(timestamp__lt=threshold_date)
        count = old_messages.count()
        old_messages.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {count} old messages"))
