from django.core.management.base import BaseCommand
from tasks.google_calendar_service import GoogleCalendarService

class Command(BaseCommand):
    help = 'Authenticate with Google Calendar API'

    def handle(self, *args, **options):
        self.stdout.write("Starting Google Calendar authentication...")
        try:
            calendar_service = GoogleCalendarService()
            self.stdout.write(
                self.style.SUCCESS("Authentication successful! token.json created")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Authentication failed: {str(e)}")
            )