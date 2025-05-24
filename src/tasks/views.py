# views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from .models import Task
from .simple_workflow import create_workflow, get_workflow_status, complete_workflow_task
from .task_extractor import extract_task_from_text

logger = logging.getLogger(__name__)

def _get_filtered_tasks(task_filter='all'):
    tasks = Task.objects.all().order_by('-created_at')
    
    filter_map = {
        'running': 'running',
        'waiting': 'pending', 
        'pending': 'pending',
        'completed': 'completed',
        'failed': 'failed'
    }
    
    if task_filter in filter_map:
        tasks = tasks.filter(workflow_status=filter_map[task_filter])
    
    return tasks

def _get_task_counts():
    return {
        'total_tasks': Task.objects.count(),
        'active_tasks': Task.objects.filter(workflow_status='running').count(),
        'pending_tasks': Task.objects.filter(workflow_status='pending').count(),
        'running_tasks': Task.objects.filter(workflow_status='running').count(),
        'completed_tasks': Task.objects.filter(workflow_status='completed').count(),
        'failed_tasks': Task.objects.filter(workflow_status='failed').count()
    }

def _extract_voice_text(request):
    voice_text = request.POST.get('voice_text', '')
    
    if not voice_text and request.body:
        try:
            body_data = json.loads(request.body)
            voice_text = body_data.get('voice_text', '')
        except json.JSONDecodeError:
            from urllib.parse import parse_qs
            body_data = parse_qs(request.body.decode('utf-8'))
            voice_text = body_data.get('voice_text', [''])[0]
    
    return voice_text

def _create_task_dict(task):
    return {
        'id': task.id,
        'task_type': task.task_type,
        'action': task.action,
        'person': task.person,
        'topic': task.topic,
        'deadline': task.deadline,
        'language': task.language,
        'voice_input': task.voice_input,
        'created_at': task.created_at.isoformat()
    }

def home(request):
    task_filter = request.GET.get('filter', 'all')
    recent_tasks = _get_filtered_tasks(task_filter)
    task_counts = _get_task_counts()
    
    return render(request, 'home.html', {
        'recent_tasks': recent_tasks,
        'current_filter': task_filter,
        **task_counts
    })

@csrf_exempt
def process_voice(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST requests are allowed"}, status=405)
    
    try:
        voice_text = _extract_voice_text(request)
        
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
        

        task_dict = _create_task_dict(task)
        workflow_id = create_workflow(task_dict)
        
        task.workflow_id = workflow_id
        task.workflow_status = 'running'
        task.save()
        
        feedback_message = generate_feedback_message(task_data)
        
        return JsonResponse({
            "status": "success",
            "data": {
                "task_id": task.id,
                "action": task_data['action'],
                "person": task_data['person'],
                "topic": task_data['topic'],
                "deadline": task_data['deadline'],
                "task_type": task_data['task_type'],
                "language": task_data['language'],
                "feedback": feedback_message,
                "workflow_id": workflow_id
            }
        })
        
    except Exception as e:
        logger.exception("Unexpected error processing voice input")
        return JsonResponse({"status": "error", "error": f"Unexpected error: {str(e)}"}, status=500)

def workflow_status(request, workflow_id):
    status = get_workflow_status(workflow_id)
    return JsonResponse(status)

@csrf_exempt
def complete_workflow_task_view(request, workflow_id, task_name):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    
    try:
        task_data = json.loads(request.body) if request.body else {}
        success = complete_workflow_task(workflow_id, task_name, task_data)
        
        return JsonResponse({"success": success})
    except Exception as e:
        logger.error(f"Error completing workflow task: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

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
    task_filter = request.GET.get('filter', 'all')
    tasks = _get_filtered_tasks(task_filter)
    task_counts = _get_task_counts()
    
    return render(request, 'task_list.html', {
        'tasks': tasks,
        'current_filter': task_filter,
        **task_counts
    })

def task_detail(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
        workflow_status = None
        if task.workflow_id:
            workflow_status = get_workflow_status(task.workflow_id)
        return render(request, 'task_detail.html', {
            'task': task,
            'workflow_status': workflow_status
        })
    except Task.DoesNotExist:
        return render(request, '404.html', status=404)

@csrf_exempt
def update_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
        data = json.loads(request.body)

        if 'status' in data:
            new_status = data['status']
            
            task.workflow_status = new_status
            task.save()

            return JsonResponse({
                "status": "success",
                "task_id": task.id,
                "new_status": new_status,
                "workflow_status": task.workflow_status
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": "No status provided"
            }, status=400)
    except Task.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Task not found"
        }, status=404)
    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)