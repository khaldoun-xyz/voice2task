import logging
import json
from typing import Dict, Any, Optional
from django.core.cache import cache
from .models import Task

logger = logging.getLogger(__name__)

class SimpleWorkflowEngine:
    
    CACHE_PREFIX = "workflow_"
    CACHE_TIMEOUT = 3600 * 24  
    
    def __init__(self):
        pass
    
    def create_task_workflow(self, task_data: Dict[str, Any]) -> Optional[str]:
        workflow_id = f"task_{task_data.get('id')}_{task_data.get('task_type')}"
        
        workflow = {
            'id': workflow_id,
            'task_data': task_data,
            'status': 'running',
            'current_step': 'validate',
            'steps': self._get_workflow_steps(task_data.get('task_type')),
            'completed_steps': [],
            'data': {},
            'created_at': task_data.get('created_at', ''),
        }

        self._save_workflow(workflow_id, workflow)
        self._process_automatic_steps(workflow_id)
        
        logger.info(f"Created workflow {workflow_id} for task {task_data.get('id')}")
        return workflow_id
    
    def _get_workflow_steps(self, task_type: str) -> list:
        base_steps = ['validate', 'set_priority', 'assign_user', 'notify']
        
        task_specific_steps = {
            'call': base_steps + ['schedule_call'],
            'email': base_steps + ['compose_email'],
            'meeting': base_steps + ['schedule_meeting'],
            'offer': base_steps + ['prepare_offer'],
            'document': base_steps + ['create_document'],
            'followup': base_steps + ['schedule_followup'],
            'reminder': base_steps + ['set_reminder'],
            'general': base_steps + ['complete_task']
        }
        
        return task_specific_steps.get(task_type, base_steps + ['complete_task'])
    
    def _process_automatic_steps(self, workflow_id: str):

        workflow = self._load_workflow(workflow_id)
        if not workflow:
            return

        automatic_steps = ['validate', 'set_priority', 'assign_user', 'notify']
        
        for step in automatic_steps:
            if step in workflow['steps'] and step not in workflow['completed_steps']:
                self._execute_step(workflow_id, step)
                workflow['completed_steps'].append(step)

        remaining_steps = [s for s in workflow['steps'] if s not in workflow['completed_steps']]
        if remaining_steps:
            workflow['current_step'] = remaining_steps[0]
            workflow['status'] = 'pending'
        else:
            workflow['status'] = 'completed'
            workflow['current_step'] = None
        
        self._save_workflow(workflow_id, workflow)
    
    def _execute_step(self, workflow_id: str, step: str):
        workflow = self._load_workflow(workflow_id)
        if not workflow:
            return
            
        task_data = workflow['task_data']
        
        if step == 'validate':
            validation_result = {'valid': True, 'errors': []}
            
            if not task_data.get('action'):
                validation_result['valid'] = False
                validation_result['errors'].append('Missing action')
                
            if task_data.get('task_type') == 'call' and not task_data.get('person'):
                validation_result['valid'] = False
                validation_result['errors'].append('Call task requires person')
            
            workflow['data']['validation'] = validation_result
            logger.info(f"Validated workflow {workflow_id}: {validation_result}")
            
        elif step == 'set_priority':
            priority = 'medium'
            
            if task_data.get('deadline'):
                deadline_lower = task_data['deadline'].lower()
                if any(urgent in deadline_lower for urgent in ['urgent', 'asap', 'today', 'heute', 'tomorrow', 'morgen']):
                    priority = 'high'
                elif any(low in deadline_lower for low in ['next month', 'nächsten monat']):
                    priority = 'low'
                    
            if task_data.get('task_type') in ['call', 'meeting']:
                if priority == 'medium':
                    priority = 'high'
                    
            workflow['data']['priority'] = priority
            logger.info(f"Set priority for workflow {workflow_id}: {priority}")
            
        elif step == 'assign_user':
            assignment_rules = {
                'call': 'sales_team',
                'email': 'admin_team',
                'meeting': 'sales_team',
                'offer': 'sales_team',
                'document': 'admin_team',
                'followup': 'sales_team',
                'reminder': 'current_user',
                'general': 'admin_team'
            }
            
            task_type = task_data.get('task_type', 'general')
            assigned_to = assignment_rules.get(task_type, 'admin_team')
            workflow['data']['assigned_to'] = assigned_to
            logger.info(f"Assigned workflow {workflow_id} to: {assigned_to}")
            
        elif step == 'notify':
            notification = {
                'type': 'task_created',
                'recipient': workflow['data'].get('assigned_to', 'admin_team'),
                'message': f"New {task_data.get('task_type')} task: {task_data.get('action')}",
                'task_id': task_data.get('id'),
                'priority': workflow['data'].get('priority', 'medium')
            }
            
            workflow['data']['notification'] = notification
            workflow['data']['notification_sent'] = True
            logger.info(f"Notification prepared for workflow {workflow_id}")
        
        self._save_workflow(workflow_id, workflow)
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        workflow = self._load_workflow(workflow_id)
        if not workflow:
            return {'status': 'not_found', 'error': f'Workflow {workflow_id} not found'}
        
        ready_tasks = []
        if workflow['status'] == 'pending' and workflow.get('current_step'):
            ready_tasks = [workflow['current_step']]
        
        return {
            'status': workflow['status'],
            'current_step': workflow.get('current_step'),
            'data': workflow['data'],
            'ready_tasks': ready_tasks,
            'completed_steps': workflow['completed_steps'],
            'total_steps': len(workflow['steps']),
            'progress': len(workflow['completed_steps']) / len(workflow['steps']) * 100
        }
    
    def complete_user_task(self, workflow_id: str, task_name: str, task_data: Dict[str, Any]) -> bool:
        workflow = self._load_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False
        
        if workflow.get('current_step') != task_name:
            logger.error(f"Expected step {workflow.get('current_step')}, got {task_name}")
            return False

        workflow['data'].update(task_data)
        workflow['completed_steps'].append(task_name)
        
        remaining_steps = [s for s in workflow['steps'] if s not in workflow['completed_steps']]
        if remaining_steps:
            workflow['current_step'] = remaining_steps[0]
            workflow['status'] = 'pending'
        else:
            workflow['status'] = 'completed'
            workflow['current_step'] = None
        
        self._save_workflow(workflow_id, workflow)
        
        try:
            task_id = workflow['task_data'].get('id')
            if task_id:
                task = Task.objects.get(id=task_id)
                task.workflow_status = workflow['status']
                if 'assigned_to' in workflow['data']:
                    task.assigned_to = workflow['data']['assigned_to']
                if 'priority' in workflow['data']:
                    task.priority = workflow['data']['priority']
                task.save()
        except Task.DoesNotExist:
            logger.error(f"Task {task_id} not found")
        except Exception as e:
            logger.error(f"Error updating task: {str(e)}")
        
        logger.info(f"Completed user task {task_name} in workflow {workflow_id}")
        return True
    
    def list_active_workflows(self) -> list:
        # This would require iterating through cache keys
        # For now, return empty list - would need Redis for full implementation
        return []
    
    def _save_workflow(self, workflow_id: str, workflow: Dict[str, Any]):
        cache_key = f"{self.CACHE_PREFIX}{workflow_id}"
        cache.set(cache_key, json.dumps(workflow), self.CACHE_TIMEOUT)
    
    def _load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        cache_key = f"{self.CACHE_PREFIX}{workflow_id}"
        workflow_json = cache.get(cache_key)
        if workflow_json:
            try:
                return json.loads(workflow_json)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode workflow {workflow_id}")
                return None
        return None

def create_workflow(task_data: Dict[str, Any]) -> Optional[str]:
    engine = SimpleWorkflowEngine()
    return engine.create_task_workflow(task_data)

def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    engine = SimpleWorkflowEngine()
    return engine.get_workflow_status(workflow_id)

def complete_workflow_task(workflow_id: str, task_name: str, task_data: Dict[str, Any]) -> bool:
    engine = SimpleWorkflowEngine()
    return engine.complete_user_task(workflow_id, task_name, task_data)