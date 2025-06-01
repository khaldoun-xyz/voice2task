import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
import re

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    """Google Calendar integration service for automated task scheduling."""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    CREDENTIALS_FILE = os.path.join(settings.BASE_DIR, 'credentials.json')
    TOKEN_FILE = os.path.join(settings.BASE_DIR, 'token.json')
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.CREDENTIALS_FILE):
                    raise FileNotFoundError(f"Credentials file {self.CREDENTIALS_FILE} not found")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIALS_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        self.credentials = creds
        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("Google Calendar service authenticated successfully")
    
    def _parse_deadline_to_datetime(self, deadline_str: str, task_type: str) -> Optional[datetime]:
        """Parse deadline string to datetime object."""
        if not deadline_str:
            # Default scheduling based on task type
            now = datetime.now()
            if task_type == 'reminder':
                return now + timedelta(hours=1)  # 1 hour from now
            elif task_type in ['call', 'meeting']:
                return now + timedelta(days=1)  # Tomorrow
            elif task_type == 'followup':
                return now + timedelta(days=7)  # Next week
            else:
                return now + timedelta(days=1)  # Default to tomorrow
        
        deadline_lower = deadline_str.lower().strip()
        now = datetime.now()
        
        # Handle specific time patterns
        time_patterns = {
            'today': now.replace(hour=14, minute=0, second=0, microsecond=0),
            'tomorrow': (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0),
            'morgen': (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0),
            'next week': (now + timedelta(days=7)).replace(hour=14, minute=0, second=0, microsecond=0),
            'nächste woche': (now + timedelta(days=7)).replace(hour=14, minute=0, second=0, microsecond=0),
            'next friday': self._get_next_weekday(now, 4).replace(hour=14, minute=0, second=0, microsecond=0),
            'next monday': self._get_next_weekday(now, 0).replace(hour=14, minute=0, second=0, microsecond=0),
        }
        
        for pattern, dt in time_patterns.items():
            if pattern in deadline_lower:
                return dt
        
        # Try to extract time from string (e.g., "at 3pm", "um 15:00")
        time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm|uhr)?', deadline_lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3)
            
            if period == 'pm' and hour < 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            
            target_date = now + timedelta(days=1)  # Default to tomorrow
            return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Default fallback
        return now + timedelta(days=1)
    
    def _get_next_weekday(self, current_date: datetime, weekday: int) -> datetime:
        """Get the next occurrence of a specific weekday (0=Monday, 6=Sunday)."""
        days_ahead = weekday - current_date.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return current_date + timedelta(days=days_ahead)
    
    def _create_event_details(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create Google Calendar event details from task data."""
        action = task_data.get('action', '')
        person = task_data.get('person', '')
        topic = task_data.get('topic', '')
        task_type = task_data.get('task_type', 'general')
        deadline = task_data.get('deadline', '')
        
        # Parse the deadline to get event datetime
        event_datetime = self._parse_deadline_to_datetime(deadline, task_type)
        
        # Create event title based on task type
        title_templates = {
            'call': f"Call {person}" + (f" about {topic}" if topic else ""),
            'meeting': f"Meeting with {person}" + (f" - {topic}" if topic else ""),
            'reminder': f"Reminder: {action}",
            'followup': f"Follow-up with {person}" + (f" on {topic}" if topic else ""),
            'general': action
        }
        
        title = title_templates.get(task_type, action)
        
        # Create description
        description_parts = [f"Task Type: {task_type.title()}"]
        if person:
            description_parts.append(f"Person: {person}")
        if topic:
            description_parts.append(f"Topic: {topic}")
        if deadline:
            description_parts.append(f"Original Deadline: {deadline}")
        
        description = "\n".join(description_parts)
        description += f"\n\nCreated from voice input: {task_data.get('voice_input', '')}"
        
        # Set event duration based on task type
        duration_map = {
            'meeting': 60,  # 1 hour
            'call': 30,     # 30 minutes
            'reminder': 15, # 15 minutes
            'followup': 45, # 45 minutes
            'general': 30   # 30 minutes
        }
        
        duration_minutes = duration_map.get(task_type, 30)
        end_datetime = event_datetime + timedelta(minutes=duration_minutes)
        
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': event_datetime.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 15},       # 15 minutes before
                ],
            },
        }
        
        # Add attendees if person is provided and looks like an email
        if person and '@' in person:
            event['attendees'] = [{'email': person}]
        
        return event
    
    def create_calendar_event(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a calendar event for the given task."""
        try:
            if not self.service:
                raise Exception("Google Calendar service not authenticated")
            
            event_details = self._create_event_details(task_data)
            
            # Create the event
            event = self.service.events().insert(
                calendarId='primary',
                body=event_details
            ).execute()
            
            logger.info(f"Created calendar event: {event.get('id')} - {event_details['summary']}")
            
            return {
                'success': True,
                'event_id': event.get('id'),
                'event_link': event.get('htmlLink'),
                'event_title': event_details['summary'],
                'event_datetime': event_details['start']['dateTime'],
                'message': f"Successfully created calendar event: {event_details['summary']}"
            }
            
        except HttpError as error:
            logger.error(f"Google Calendar API error: {error}")
            return {
                'success': False,
                'error': f"Calendar API error: {error}",
                'message': f"Failed to create calendar event: {error}"
            }
        
        except Exception as error:
            logger.error(f"Error creating calendar event: {error}")
            return {
                'success': False,
                'error': str(error),
                'message': f"Failed to create calendar event: {error}"
            }
    
    def update_calendar_event(self, event_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing calendar event."""
        try:
            if not self.service:
                raise Exception("Google Calendar service not authenticated")
            
            event_details = self._create_event_details(task_data)
            
            # Update the event
            event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event_details
            ).execute()
            
            logger.info(f"Updated calendar event: {event_id}")
            
            return {
                'success': True,
                'event_id': event.get('id'),
                'event_link': event.get('htmlLink'),
                'message': f"Successfully updated calendar event: {event_details['summary']}"
            }
            
        except HttpError as error:
            logger.error(f"Error updating calendar event: {error}")
            return {
                'success': False,
                'error': str(error),
                'message': f"Failed to update calendar event: {error}"
            }
    
    def delete_calendar_event(self, event_id: str) -> Dict[str, Any]:
        """Delete a calendar event."""
        try:
            if not self.service:
                raise Exception("Google Calendar service not authenticated")
            
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            logger.info(f"Deleted calendar event: {event_id}")
            
            return {
                'success': True,
                'message': f"Successfully deleted calendar event: {event_id}"
            }
            
        except HttpError as error:
            logger.error(f"Error deleting calendar event: {error}")
            return {
                'success': False,
                'error': str(error),
                'message': f"Failed to delete calendar event: {error}"
            }
    
    def list_upcoming_events(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """List upcoming calendar events."""
        try:
            if not self.service:
                raise Exception("Google Calendar service not authenticated")
            
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return [{
                'id': event['id'],
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'link': event.get('htmlLink', ''),
                'description': event.get('description', '')
            } for event in events]
            
        except HttpError as error:
            logger.error(f"Error listing calendar events: {error}")
            return []


# Singleton instance
calendar_service = GoogleCalendarService()