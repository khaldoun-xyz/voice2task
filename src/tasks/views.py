# views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from .models import Task
from .simple_workflow import SimpleWorkflowEngine
from .task_extractor import (
    extract_task_from_text,
    TaskExtractor,
    TaskComponents,
    LanguageDetector,
    NLPProcessor,
    InsuranceTaskHandler,
    generate_feedback_message
)

logger = logging.getLogger(__name__)

workflow_engine = SimpleWorkflowEngine()

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

    return voice_text.strip()

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
        'workflow_status': task.workflow_status,
        'assigned_to': task.assigned_to,
        'priority': task.priority,
        'created_at': task.created_at.isoformat(),
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
        workflow_id = workflow_engine.create_task_workflow(task_dict)

        task.workflow_id = workflow_id
        task.workflow_status = 'running' 
        task.save()

        workflow_engine._process_automatic_steps(workflow_id)

        task.refresh_from_db()

        task_components = TaskComponents(
            action=task_data['action'],
            person=task_data['person'],
            topic=task_data['topic'],
            deadline=task_data['deadline'],
            language=task_data['language'],
            task_type=task_data['task_type']
        )
        feedback_message = generate_feedback_message(task_components)

        return JsonResponse({
            "status": "success",
            "data": {
                "task_id": task.id,
                "action": task.action,
                "person": task.person,
                "topic": task.topic,
                "deadline": task.deadline,
                "task_type": task.task_type,
                "language": task.language,
                "feedback": feedback_message,
                "workflow_id": workflow_id,
                "workflow_status": task.workflow_status,
            }
        })

    except Exception as e:
        logger.exception("Unexpected error processing voice input")
        return JsonResponse({"status": "error", "error": f"Unexpected error: {str(e)}"}, status=500)

@csrf_exempt
def analyze_voice_text(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST requests are allowed"}, status=405)
    
    try:
        voice_text = _extract_voice_text(request)
        
        if not voice_text:
            return JsonResponse({"status": "error", "message": "No voice text provided"}, status=400)

        language = LanguageDetector.detect_language(voice_text)

        extractor = TaskExtractor(voice_text)
        task_components = extractor.extract_task()

        enhanced_task = InsuranceTaskHandler.enhance_task(task_components)

        feedback = generate_feedback_message(enhanced_task)
        
        return JsonResponse({
            "status": "success",
            "analysis": {
                "original_text": voice_text,
                "cleaned_text": extractor.cleaned_text,
                "detected_language": language,
                "extracted_components": enhanced_task.to_dict(),
                "feedback_message": feedback
            }
        })

    except Exception as e:
        logger.exception("Error analyzing voice text")
        return JsonResponse({"status": "error", "error": f"Analysis error: {str(e)}"}, status=500)

@csrf_exempt
def detect_language(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST requests are allowed"}, status=405)

    try:
        text = _extract_voice_text(request)

        if not text:
            return JsonResponse({"status": "error", "message": "No text provided"}, status=400)

        detected_language = LanguageDetector.detect_language(text)

        return JsonResponse({
            "status": "success",
            "data": {
                "text": text,
                "detected_language": detected_language,
                "language_name": "German" if detected_language == "de" else "English"
            }
        })

    except Exception as e:
        logger.exception("Error detecting language")
        return JsonResponse({"status": "error", "error": f"Language detection error: {str(e)}"}, status=500)

@csrf_exempt
def extract_task_components(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST requests are allowed"}, status=405)

    try:
        voice_text = _extract_voice_text(request)

        if not voice_text:
            return JsonResponse({"status": "error", "message": "No voice text provided"}, status=400)
        extractor = TaskExtractor(voice_text)

        components = {
            "original_text": voice_text,
            "cleaned_text": extractor.cleaned_text,
            "detected_language": extractor.language,
            "action": extractor._extract_action(),
            "person": extractor._extract_person(),
            "topic": extractor._extract_topic(),
            "deadline": extractor._extract_deadline(),
            "nlp_entities": [{"text": ent.text, "label": ent.label_} for ent in extractor.doc.ents]
        }

        task_type = extractor._determine_task_type(components["action"])
        components["task_type"] = task_type

        components["standardized_action"] = extractor._standardize_action(components["action"], task_type)

        return JsonResponse({
            "status": "success",
            "components": components
        })

    except Exception as e:
        logger.exception("Error extracting task components")
        return JsonResponse({"status": "error", "error": f"Component extraction error: {str(e)}"}, status=500)

def workflow_status(request, workflow_id):
    status = workflow_engine.get_workflow_status(workflow_id)
    return JsonResponse(status)

@csrf_exempt
def complete_workflow_task_view(request, workflow_id, task_name):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        task_data = json.loads(request.body) if request.body else {}
        success = workflow_engine.complete_user_task(workflow_id, task_name, task_data)

        return JsonResponse({"success": success})
    except Exception as e:
        logger.error(f"Error completing workflow task: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

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
        task.refresh_from_db()
        workflow_status_data = None
        if task.workflow_id:
            workflow_status_data = workflow_engine.get_workflow_status(task.workflow_id)
        try:
            extractor = TaskExtractor(task.voice_input)
            task_components = extractor.extract_task()
            enhanced_task = InsuranceTaskHandler.enhance_task(task_components)

            analysis = {
                "cleaned_text": extractor.cleaned_text,
                "nlp_entities": [{"text": ent.text, "label": ent.label_} for ent in extractor.doc.ents],
                "enhanced_components": enhanced_task.to_dict()
            }
        except Exception as e:
            logger.error(f"Error re-analyzing task {task_id}: {str(e)}")
            analysis = None

        return render(request, 'task_detail.html', {
            'task': task,
            'workflow_status': workflow_status_data,
            'analysis': analysis
        })
    except Task.DoesNotExist:
        return render(request, '404.html', status=404)

@csrf_exempt
def update_task(request, task_id):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

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
        updatable_fields = ['action', 'person', 'topic', 'deadline', 'assigned_to', 'priority']
        updated_fields = {}

        for field in updatable_fields:
            if field in data:
                setattr(task, field, data[field])
                updated_fields[field] = data[field]

        if updated_fields:
            task.save()
            return JsonResponse({
                "status": "success",
                "task_id": task.id,
                "updated_fields": updated_fields
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": "No valid fields provided for update"
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

@csrf_exempt
def bulk_process_tasks(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        voice_texts = data.get('voice_texts', [])

        if not voice_texts or not isinstance(voice_texts, list):
            return JsonResponse({
                "status": "error",
                "message": "voice_texts must be a non-empty array"
            }, status=400)

        results = []

        for i, voice_text in enumerate(voice_texts):
            try:
                task_data = extract_task_from_text(voice_text)

                if 'error' in task_data:
                    results.append({
                        "index": i,
                        "voice_text": voice_text,
                        "status": "error",
                        "error": task_data['error']
                    })
                    continue

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
                workflow_id = workflow_engine.create_task_workflow(task_dict)

                task.workflow_id = workflow_id
                task.workflow_status = 'running'
                task.save()

                task_components = TaskComponents(**task_data)
                feedback = generate_feedback_message(task_components)

                results.append({
                    "index": i,
                    "voice_text": voice_text,
                    "status": "success",
                    "task_id": task.id,
                    "task_data": task_data,
                    "feedback": feedback,
                    "workflow_id": workflow_id
                })

            except Exception as e:
                results.append({
                    "index": i,
                    "voice_text": voice_text,
                    "status": "error",
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r['status'] == 'success')

        return JsonResponse({
            "status": "completed",
            "total_processed": len(voice_texts),
            "successful": success_count,
            "failed": len(voice_texts) - success_count,
            "results": results
        })

    except Exception as e:
        logger.exception("Error in bulk processing")
        return JsonResponse({
            "status": "error",
            "error": f"Bulk processing error: {str(e)}"
         }, status=500)

def get_task_statistics(request):
    try:
        task_counts = _get_task_counts()

        language_stats = {}
        for lang_code, lang_name in Task.LANGUAGE_CHOICES:
            count = Task.objects.filter(language=lang_code).count()
            language_stats[lang_name] = count

        task_type_stats = {}
        for type_code, type_name in Task.TASK_TYPES:
            count = Task.objects.filter(task_type=type_code).count()
            task_type_stats[type_name] = count

        from datetime import datetime, timedelta
        from django.utils import timezone

        week_ago = timezone.now() - timedelta(days=7)
        recent_tasks = Task.objects.filter(created_at__gte=week_ago).count()

        return JsonResponse({
            "status": "success",
            "statistics": {
                "task_counts": task_counts,
                "language_distribution": language_stats,
                "task_type_distribution": task_type_stats,
                "recent_activity": {
                    "last_7_days": recent_tasks
                }
            }
        })

    except Exception as e:
        logger.exception("Error getting task statistics")
        return JsonResponse({
            "status": "error",
            "error": f"Statistics error: {str(e)}"
        }, status=500)