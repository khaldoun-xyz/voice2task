# views.py 
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from .models import Task
from .task_extractor import extract_task_from_text, TaskComponents
logger = logging.getLogger(__name__)

def home(request):
    recent_tasks = Task.objects.all().order_by('-created_at')[:10]
    return render(request, 'home.html', {'recent_tasks': recent_tasks})

@csrf_exempt
def process_voice(request):
    """
    Process voice input and extract task components.
    Handles both form data and raw POST data.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST requests are allowed"}, status=405)
    
    try:

        voice_text = request.POST.get('voice_text', '')
        if not voice_text and request.body:
            try:
                body_data = json.loads(request.body)
                voice_text = body_data.get('voice_text', '')
            except json.JSONDecodeError:
                from urllib.parse import parse_qs
                body_data = parse_qs(request.body.decode('utf-8'))
                voice_text = body_data.get('voice_text', [''])[0]
        
        if not voice_text:
            return JsonResponse({"status": "error", "message": "No voice text provided"}, status=400)
        
        logger.info(f"Processing voice input: {voice_text}")
        task_data = extract_task_from_text(voice_text)
        
        if 'error' in task_data:
            logger.error(f"Error extracting task: {task_data['error']}")
            return JsonResponse({
                "status": "error", 
                "error": f"Failed to extract task: {task_data['error']}"
            }, status=500)
        
        task = Task(
            user='anonymous',  
            voice_input=voice_text,
            task_type=task_data['task_type'],
            action=task_data['action'],
            person=task_data['person'],
            topic=task_data['topic'],
            deadline=task_data['deadline'],
            language=task_data['language']
        )
        task.save()
        
        feedback_message = generate_feedback_message(task_data)
        
        return JsonResponse({
            "status": "success",
            "data": {
                "action": task_data['action'],
                "person": task_data['person'],
                "topic": task_data['topic'],
                "deadline": task_data['deadline'],
                "task_type": task_data['task_type'],
                "language": task_data['language'],
                "feedback": feedback_message
            }
        })
        
    except Exception as e:
        logger.exception("Unexpected error processing voice input")
        return JsonResponse({"status": "error", "error": f"Unexpected error: {str(e)}"}, status=500)

def generate_feedback_message(task_data):
    language = task_data['language']
    action = task_data['action']
    person = task_data['person']
    topic = task_data['topic']
    deadline = task_data['deadline']
    
    if language == "en":
        message = f"Task created: {action}"
        if person:
            message += f" with {person}"
        if topic:
            message += f" about {topic}"
        if deadline:
            message += f" - Due {deadline}"
    else: 
        message = f"Aufgabe erstellt: {action}"
        if person:
            message += f" mit {person}"
        if topic:
            message += f" über {topic}"
        if deadline:
            message += f" - Fällig {deadline}"
    
    return message



def task_list(request):
    tasks = Task.objects.all().order_by('-created_at')
    return render(request, 'task_list.html', {'tasks': tasks})

def task_detail(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
        return render(request, 'task_detail.html', {'task': task})
    except Task.DoesNotExist:
        return render(request, '404.html', status=404)