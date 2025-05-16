The purpose of Voice-to-Task is to <b><u>automate task creation through voice commands</u></b>

We believe voice input can save time and reduce errors for employees who need to log tasks quickly—especially in mobile, fast-paced, or hands-free environments.
By converting natural language into structured tasks, we eliminate manual data entry and streamline everyday workflows.
📌 Description

Voice-to-Task is a lightweight prototype that:
Listens to a user’s spoken command
(e.g., “Create a task: Call Mr. Schmidt about the damage report by Friday.”)
Extracts key task elements using NLP:
- Action
- Person
- Topic
- Deadline
Pushes the task to a connected system (e.g., Microsoft Planner, CRM, Outlook)
The product is in prototype phase, designed for simplicity and flexibility.

At this stage, it works best with clearly structured sentences to reduce ambiguity.

⚙️ 1. Core Components


Voice Input:	Speech-to-text (STT) via browser or mobile app
NLP Parsing:	Extracts action, person, topic, deadline using spaCy
Task Output:	Sends structured data to task management systems
Confirmation:	Displays task preview and success message to user

🚧 2. Limitations (Phase 1)

- Supports only 1–2 sentence structures:
e.g., "[Action] [Person] about [Topic] by [Date]"
- No complex sentence support
- Assumes English only
- No support for recurring tasks or priorities yet

🧰 3. Tools & Stack


NLP:	spaCy (rule-based)
STT:	Web Speech API (browser-native)
Backend:	Django (Python)
Task APIs:	To be integrated (e.g., Planner, Outlook)

🖥️ Voice Input (UI Flow)

Minimal interface on the homepage with a Record button
User clicks “Start Recording,” speaks a command, and stops
A spinner indicates processing
Transcription is shown automatically
Example Input:
“Call Mr. Schmidt about the damage report by Friday”
✅ Task Preview

Once transcribed and parsed, the user sees a structured task preview:
Task created successfully:
Action: Call
Person: Schmidt
Topic: the damage report
Deadline: Friday
"Task created: Call Schmidt about the damage report - Due Friday"
Original text: "Call Mr. Schmidt about the damage report by Friday"

📥 Task Confirmation

Final confirmation screen once the task is created
Shows where the task was sent (e.g., “Created in Planner → Sales Tasks”)
Optional: Display external task ID or link
🗃️ Database Design (Star Schema)

tasks
Field	Type
task_id (PK)	UUID
user_id	UUID/Text
created_at	Timestamp
voice_input_text	Text
parsed_action	Text
parsed_deadline	Date/Text
integrations
Field	Type
integration_id (PK)	UUID
task_id (FK)	UUID
system_name	Text
external_task_id	Text

❓ Edge Cases & Open Questions

Priority detection
What if the user says "urgent"? → Should we tag or flag?
System errors
What happens if CRM or Planner is offline? → Queue locally?
Incomplete input
How should we handle missing person/topic/deadline?