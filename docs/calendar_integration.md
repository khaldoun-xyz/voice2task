# 📅 Google Calendar Integration for SpiffWorkflow/SpiffArena

The purpose of this integration is to **connect SpiffWorkflow tasks with Google Calendar**, enabling seamless scheduling and automation of calendar events through workflow logic.

By bridging workflows with Google Calendar, we empower users to automate reminders, deadlines, and meeting scheduling directly from BPMN-based processes—eliminating manual syncing and ensuring time-sensitive actions are never missed.

---

## 📌 Description

This integration allows your SpiffWorkflow project to:

* Authenticate securely with a Google account using OAuth 2.0
* Access and manage calendar events via the Google Calendar API
* Add event creation logic directly into BPMN workflows
* Optionally display recent events or confirmations in logs/UI

The setup is built with flexibility and security in mind and is optimized for prototyping or internal apps.

---

## ⚙️ 1. Core Components

| Component           | Description                                                             |
| ------------------- | ----------------------------------------------------------------------- |
| **Google API Auth** | OAuth 2.0-based authentication using a client credentials file          |
| **Event Logic**     | Scripts that parse workflow data and push new events to Google Calendar |
| **Workflow Hook**   | BPMN tasks configured to trigger event creation or scheduling           |
| **Token Handling**  | Secure token storage via `token.json` to persist user sessions          |

---

## 🧭 2. Integration Setup Steps

### ✅ Step 1: Google Cloud Console Configuration

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable **Google Calendar API**:

   * Navigate to **APIs & Services > Library**
   * Search “Google Calendar API” and click **Enable**
   * Or use [this direct link](https://console.cloud.google.com/flows/enableapi?apiid=calendar-json.googleapis.com)

---

### ✅ Step 2: OAuth Consent Screen

1. Navigate to **OAuth consent screen**
2. Choose **External** (unless using Google Workspace)
3. Fill in:

   * App name
   * Support & developer emails
4. Add required scope:

   * `https://www.googleapis.com/auth/calendar`
5. Add test users (e.g., your own Google email)

---

### ✅ Step 3: Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Create **OAuth client ID**:

   * Choose **Desktop application**
   * Name it (e.g., “Spiff Calendar Integration”)
3. Click **Create**, then download the `credentials.json` file

---

### ✅ Step 4: Install Python Dependencies

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

---

### ✅ Step 5: Project Setup

* Place `credentials.json` in the root of your project (e.g., next to `manage.py` or in `src/`)
* Add these modules:

```
src/
  └─ core/
      └─ google_auth.py
  └─ tasks/
      └─ google_calendar_service.py
      └─ management/
           └─ commands/
               └─ auth_google.py
```

---

### ✅ Step 6: BPMN Workflow Integration

Create or modify your BPMN file:

```
src/tasks/workflows/calendar_workflow.bpmn
```

Add service task(s) that call your Python logic to create calendar events from workflow data.

---

## 🛠️ 3. Environment Configuration

Add the following to `.env` or your Django `settings.py`:

```python
GOOGLE_CALENDAR_CREDENTIALS_FILE = 'credentials.json'
GOOGLE_CALENDAR_TOKEN_FILE = 'token.json'
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
```

---

## 🔐 4. Authentication Flow

1. Run the authentication command:

   ```bash
   python manage.py auth_google
   ```
2. Follow the OAuth flow in your browser:

   * Sign in with your test Google account
   * Grant permission
   * You may need to click **Advanced → Go to App**
3. Upon success:

   * A `token.json` file is created
   * Terminal shows "Authentication successful!"
   * A list of recent events may be displayed

---

## 🖥️ 5. Frontend/Backend Integration

You may extend your frontend to:

* Show a calendar event preview
* Display confirmation of integration success
* Offer a manual “Sync to Calendar” trigger

---

## 🚧 6. Limitations

* Only works with authorized test users (until OAuth is verified)
* Requires clear workflow logic to extract event details (title, time, etc.)
* Only supports manual OAuth for now (no service account support)

---

## 🧪 7. Troubleshooting

### Common Issues:

* **OAuth not working?**
  → Ensure your Google account is added as a test user
* **Invalid credentials?**
  → Check file placement and that `credentials.json` matches your client ID
* **Token expired?**
  → Delete `token.json` and re-authenticate

---

## 🔗 Important Links

* [Google Calendar API Docs](https://developers.google.com/calendar/api)
* [Google Cloud Console](https://console.cloud.google.com/)
* [OAuth Quickstart (Python)](https://developers.google.com/calendar/api/quickstart/python)
* [SpiffWorkflow Docs](https://www.spiffworkflow.org/)

---

## 🔒 Security Notes

* **Do not commit** `credentials.json` or `token.json` to version control
* Add both to your `.gitignore`
* Consider using **service accounts** for production automation
* Always validate and sanitize event inputs from workflows
