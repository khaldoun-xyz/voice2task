# google_calendar_service.py
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import dateparser
from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    CREDENTIALS_FILE = os.path.join(settings.BASE_DIR, "credentials.json")
    TOKEN_FILE = os.path.join(settings.BASE_DIR, "token.json")

    DEFAULT_DURATIONS = {
        "meeting": 60,
        "call": 30,
        "reminder": 15,
        "followup": 45,
        "general": 30,
    }

    DEFAULT_DEADLINES = {
        "reminder": timedelta(hours=1),
        "call": timedelta(days=1),
        "meeting": timedelta(days=1),
        "followup": timedelta(days=7),
        "general": timedelta(days=1),
    }

    TIME_PATTERNS = {
        "today": 0,
        "tomorrow": 1,
        "morgen": 1,
        "next week": 7,
        "nächste woche": 7,
    }

    EVENT_TEMPLATES = {
        "call": "Call {person}{topic_suffix}",
        "meeting": "Meeting with {person}{topic_suffix}",
        "reminder": "Reminder: {action}",
        "followup": "Follow-up with {person}{topic_suffix}",
        "general": "{action}",
    }

    WEEKDAY_MAPPING = {
        "mon": 0,
        "monday": 0,
        "tue": 1,
        "tuesday": 1,
        "wed": 2,
        "wednesday": 2,
        "thu": 3,
        "thursday": 3,
        "fri": 4,
        "friday": 4,
        "sat": 5,
        "saturday": 5,
        "sun": 6,
        "sunday": 6,
        "mo": 0,
        "montag": 0,
        "di": 1,
        "dienstag": 1,
        "mi": 2,
        "mittwoch": 2,
        "do": 3,
        "donnerstag": 3,
        "fr": 4,
        "freitag": 4,
        "sa": 5,
        "samstag": 5,
        "sonnabend": 5,
        "so": 6,
        "sonntag": 6,
    }

    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()

    def _authenticate(self):
        creds = self._load_existing_credentials()

        if not creds or not creds.valid:
            creds = self._refresh_or_create_credentials(creds)

        self.credentials = creds
        self.service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar service authenticated successfully")

    def _load_existing_credentials(self) -> Optional[Credentials]:
        if os.path.exists(self.TOKEN_FILE):
            return Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)
        return None

    def _refresh_or_create_credentials(
        self, creds: Optional[Credentials]
    ) -> Credentials:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds)
                return creds
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")

        if not os.path.exists(self.CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"Credentials file {self.CREDENTIALS_FILE} not found"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            self.CREDENTIALS_FILE, self.SCOPES
        )
        new_creds = flow.run_local_server(port=0)
        self._save_credentials(new_creds)
        return new_creds

    def _save_credentials(self, creds: Credentials):
        with open(self.TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    def _get_relative_date(
        self, days_offset: int, hour: int = None, minute: int = 0
    ) -> datetime:
        base_date = timezone.now() + timedelta(days=days_offset)
        if hour is not None:
            return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return base_date.replace(second=0, microsecond=0)

    def _get_next_weekday(
        self, current_date: datetime, weekday: int, hour: int = None, minute: int = 0
    ) -> datetime:
        days_ahead = (weekday - current_date.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        target_date = current_date + timedelta(days=days_ahead)

        if hour is not None:
            return target_date.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        return target_date.replace(second=0, microsecond=0)

    def _make_timezone_aware(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:

            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def _parse_deadline_to_datetime(
        self, deadline_str: str, task_type: str
    ) -> datetime:
        if not deadline_str:
            return timezone.now() + self.DEFAULT_DEADLINES.get(
                task_type, timedelta(days=1)
            )

        deadline_lower = deadline_str.lower().strip()
        logger.info(f"Parsing deadline: '{deadline_str}' -> '{deadline_lower}'")

        dateparser_settings = {
            "PREFER_DAY_OF_MONTH": "first",
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
            "DATE_ORDER": "DMY",
            "STRICT_PARSING": False,
        }

        parsed_date = dateparser.parse(deadline_str, settings=dateparser_settings)
        if parsed_date:

            parsed_date = self._make_timezone_aware(parsed_date)

            current_time = timezone.now()
            if parsed_date < current_time and not self._parse_time_expression(
                deadline_lower
            ):

                if parsed_date.time() == datetime.min.time() or parsed_date.hour == 0:
                    parsed_date = parsed_date.replace(year=current_time.year + 1)
                    parsed_date = self._make_timezone_aware(parsed_date)

            logger.info(
                f"Dateparser successfully parsed: '{deadline_str}' -> {parsed_date}"
            )
            return parsed_date

        logger.info(
            f"Dateparser failed, falling back to manual parsing for: '{deadline_str}'"
        )

        time_components = self._parse_time_expression(deadline_lower)
        logger.info(f"Time components extracted: {time_components}")

        date_patterns = [
            r"(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|jan(?:uar)?|feb(?:ruar)?|mär(?:z)?|apr(?:il)?|mai|jun(?:i)?|jul(?:i)?|aug(?:ust)?|sep(?:tember)?|okt(?:ober)?|nov(?:ember)?|dez(?:ember)?)",
            r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|jan(?:uar)?|feb(?:ruar)?|mär(?:z)?|apr(?:il)?|mai|jun(?:i)?|jul(?:i)?|aug(?:ust)?|sep(?:tember)?|okt(?:ober)?|nov(?:ember)?|dez(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, deadline_lower)
            if match:
                try:

                    matched_text = match.group(0)
                    parsed_date = dateparser.parse(
                        matched_text, settings=dateparser_settings
                    )
                    if parsed_date:
                        parsed_date = self._make_timezone_aware(parsed_date)

                        if time_components:
                            hour, minute = time_components
                            parsed_date = parsed_date.replace(hour=hour, minute=minute)

                        if parsed_date < timezone.now():
                            parsed_date = parsed_date.replace(
                                year=timezone.now().year + 1
                            )
                            parsed_date = self._make_timezone_aware(parsed_date)

                        logger.info(
                            f"Manual pattern match successful: '{matched_text}' -> {parsed_date}"
                        )
                        return parsed_date
                except Exception as e:
                    logger.warning(
                        f"Failed to parse matched pattern '{matched_text}': {e}"
                    )
                    continue

        weekday_match = self._parse_weekday(deadline_lower)
        if weekday_match:
            weekday_name, is_by_deadline = weekday_match
            target_day = self.WEEKDAY_MAPPING.get(weekday_name)

            if target_day is not None:
                if time_components:
                    hour, minute = time_components
                    target_date = self._get_next_weekday(
                        timezone.now(), target_day, hour, minute
                    )
                else:
                    if is_by_deadline:
                        target_date = self._get_next_weekday(
                            timezone.now(), target_day, 9, 0
                        )  # Default to 9 AM for deadlines
                    else:
                        current_time = timezone.now()
                        target_date = self._get_next_weekday(
                            current_time,
                            target_day,
                            current_time.hour,
                            current_time.minute,
                        )

                logger.info(
                    f"Weekday match: {weekday_name} -> day {target_day} -> {target_date}"
                )
                return target_date

        for pattern, days in self.TIME_PATTERNS.items():
            if pattern in deadline_lower:
                if time_components:
                    hour, minute = time_components
                    return self._get_relative_date(days, hour, minute)
                else:
                    current_time = timezone.now()
                    return self._get_relative_date(
                        days, current_time.hour, current_time.minute
                    )

        if time_components:
            hour, minute = time_components
            base_date = timezone.now()
            if base_date.hour > hour or (
                base_date.hour == hour and base_date.minute > minute
            ):
                return self._get_relative_date(1, hour, minute)
            return self._get_relative_date(0, hour, minute)

        default_deadline = timezone.now() + self.DEFAULT_DEADLINES.get(
            task_type, timedelta(days=1)
        )
        logger.info(f"Using default deadline: {default_deadline}")
        return default_deadline

    def _parse_weekday(self, text: str) -> Optional[Tuple[str, bool]]:
        weekday_match = re.search(
            r"(?:by\s+)?(?:on\s+)?(mon|tues?|wed|thur?s?|fri|sat|sun|mo|di|mi|do|fr|sa|so)(?:day|ntag|enstag|ttwoch|nnerstag|reitag|mstag|nntag)?",
            text,
            re.IGNORECASE,
        )
        if not weekday_match:
            return None

        weekday_abbrev = weekday_match.group(1).lower()
        is_by_deadline = "by " in text[: weekday_match.start()].lower()

        weekday_map = {
            "mon": "mon",
            "tue": "tue",
            "tues": "tue",
            "wed": "wed",
            "thu": "thu",
            "thur": "thu",
            "thurs": "thu",
            "fri": "fri",
            "sat": "sat",
            "sun": "sun",
            "mo": "mo",
            "di": "di",
            "mi": "mi",
            "do": "do",
            "fr": "fr",
            "sa": "sa",
            "so": "so",
        }

        normalized = weekday_map.get(weekday_abbrev)
        return (normalized, is_by_deadline) if normalized else None

    def _parse_time_expression(self, time_str: str) -> Optional[Tuple[int, int]]:
        time_match = re.search(
            r"(?:at|by|um)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|uhr)?\b", time_str.lower()
        ) or re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|uhr)\b", time_str.lower())

        if not time_match:
            return None

        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)

        if period:
            if period == "pm" and hour < 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0

        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))

        return hour, minute

    def _create_event_title(self, task_data: Dict[str, Any]) -> str:
        task_type = task_data.get("task_type", "general")
        template = self.EVENT_TEMPLATES.get(task_type, self.EVENT_TEMPLATES["general"])

        topic_suffix = (
            f" about {task_data.get('topic', '')}" if task_data.get("topic") else ""
        )

        return template.format(
            person=task_data.get("person", ""),
            topic_suffix=topic_suffix,
            action=task_data.get("action", "New Event"),
        ).strip()

    def _create_event_description(self, task_data: Dict[str, Any]) -> str:
        info_fields = ["person", "topic", "deadline"]
        info_lines = [
            f"{k.title()}: {task_data[k]}" for k in info_fields if task_data.get(k)
        ]

        description_parts = [
            f"Task Type: {task_data.get('task_type', 'general').title()}",
            *info_lines,
            f"\nCreated from voice input: {task_data.get('voice_input', '')}",
        ]

        return "\n".join(description_parts)

    def _create_event_details(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        deadline_str = task_data.get("deadline", "")

        if deadline_str and not self._parse_time_expression(deadline_str.lower()):
            voice_input = task_data.get("voice_input", "")
            if voice_input and self._parse_time_expression(voice_input.lower()):
                deadline_str = voice_input
                logger.info(f"Using voice input for time parsing: '{voice_input}'")

        event_datetime = self._parse_deadline_to_datetime(
            deadline_str, task_data.get("task_type", "general")
        )

        duration = self.DEFAULT_DURATIONS.get(task_data.get("task_type", "general"), 30)
        end_datetime = event_datetime + timedelta(minutes=duration)

        event = {
            "summary": self._create_event_title(task_data),
            "description": self._create_event_description(task_data),
            "start": {
                "dateTime": event_datetime.isoformat(),
                "timeZone": "Europe/Berlin",
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "Europe/Berlin",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }

        person = task_data.get("person", "")
        if person and "@" in person and person.count("@") == 1:
            event["attendees"] = [{"email": person}]

        return event

    def _execute_calendar_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        if not self.service:
            raise Exception("Google Calendar service not authenticated")

        try:
            method = getattr(self.service.events(), operation)
            return method(**kwargs).execute()
        except HttpError as error:
            logger.error(f"Google Calendar API error during {operation}: {error}")
            raise

    def _format_event_response(
        self, event: Dict[str, Any], success: bool = True, message: str = ""
    ) -> Dict[str, Any]:
        return {
            "success": success,
            "event_id": event.get("id"),
            "event_link": event.get("htmlLink"),
            "event_title": event.get("summary", ""),
            "event_datetime": event.get("start", {}).get("dateTime"),
            "message": message or "Calendar operation completed successfully",
        }

    def create_calendar_event(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            event_details = self._create_event_details(task_data)
            event = self._execute_calendar_operation(
                "insert", calendarId="primary", body=event_details
            )
            logger.info(f"Created event: {event.get('id')}")
            return self._format_event_response(
                event, message=f"Created: {event_details['summary']}"
            )
        except Exception as error:
            logger.error(f"Error creating event: {error}")
            return {
                "success": False,
                "error": str(error),
                "message": f"Failed to create event: {error}",
            }

    def update_calendar_event(
        self, event_id: str, task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            event_details = self._create_event_details(task_data)
            event = self._execute_calendar_operation(
                "update", calendarId="primary", eventId=event_id, body=event_details
            )
            logger.info(f"Updated event: {event_id}")
            return self._format_event_response(
                event, message=f"Updated: {event_details['summary']}"
            )
        except Exception as error:
            logger.error(f"Error updating event {event_id}: {error}")
            return {
                "success": False,
                "error": str(error),
                "message": f"Failed to update event: {error}",
            }

    def delete_calendar_event(self, event_id: str) -> Dict[str, Any]:
        try:
            self._execute_calendar_operation(
                "delete", calendarId="primary", eventId=event_id
            )
            logger.info(f"Deleted event: {event_id}")
            return {"success": True, "message": f"Deleted event: {event_id}"}
        except Exception as error:
            logger.error(f"Error deleting event {event_id}: {error}")
            return {
                "success": False,
                "error": str(error),
                "message": f"Failed to delete event: {error}",
            }

    def list_upcoming_events(self, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            events_result = self._execute_calendar_operation(
                "list",
                calendarId="primary",
                timeMin=timezone.now().isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )

            return [
                self._format_event_item(event)
                for event in events_result.get("items", [])
            ]

        except Exception as error:
            logger.error(f"Error listing events: {error}")
            return []

    def _format_event_item(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": event["id"],
            "summary": event.get("summary", "No title"),
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "end": event["end"].get("dateTime", event["end"].get("date")),
            "link": event.get("htmlLink", ""),
            "description": event.get("description", ""),
        }


calendar_service = GoogleCalendarService()
