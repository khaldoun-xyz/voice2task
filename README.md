# Voice-to-Task 🎙️➡️✅

A Django application that converts voice commands into structured tasks using natural language processing.

## Features ✨

- 🎤 Voice command input via browser
- 🔍 NLP processing to extract task details (action, person, deadline)
- 💾 Task storage in database
- 📱 Mobile-friendly interface

## Prerequisites 📋

- Python 3.8+
- pip package manager
- Modern web browser (Chrome/Edge recommended)


1. Create and activate virtual environment
     python -m venv venv
   - Activate the virtual environment:(On macOS/Linux):
       source venv/bin/activate
2. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
3. Set up database
python manage.py makemigrations
python manage.py migrate
4. Run development server
python manage.py runserver