from django.db import models
from django.utils import timezone


class Task(models.Model):
    """Model to store extracted tasks from voice input."""

    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("de", "German"),
    ]

    TASK_TYPES = [
        ("call", "Call"),
        ("email", "Email"),
        ("meeting", "Meeting"),
        ("reminder", "Reminder"),
        ("document", "Documentation"),
        ("followup", "Follow-up"),
        ("offer", "Offer"),
        ("general", "General Task"),
    ]

    user = models.CharField(max_length=100)
    voice_input = models.TextField()
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, default="general")
    action = models.CharField(max_length=100)
    person = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    deadline = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="en")
    created_at = models.DateTimeField(default=timezone.now)
    workflow_id = models.CharField(max_length=100, blank=True, null=True)
    workflow_status = models.CharField(max_length=50, default="pending")
    assigned_to = models.CharField(max_length=100, blank=True)
    priority = models.CharField(max_length=20, default="medium")
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    calendar_event_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.action} - {self.person} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def has_calendar_event(self):
        return bool(self.calendar_event_id)

    def get_calendar_link(self):
        if self.calendar_event_link:
            return self.calendar_event_link
        if self.calendar_event_id:
            return f"https://calendar.google.com/calendar/event?eid={self.calendar_event_id}"
        return None

    def save(self, *args, **kwargs):
        if self.calendar_event_id and self.workflow_status != "completed":
            self.workflow_status = "completed"
        super().save(*args, **kwargs)
