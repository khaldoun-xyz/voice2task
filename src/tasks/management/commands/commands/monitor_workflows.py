# monitor_workflows.py
from django.core.management.base import BaseCommand

from tasks.models import Task
from tasks.simple_workflow import SimpleWorkflowEngine


class Command(BaseCommand):
    help = "Monitor workflow status and update tasks"

    def handle(self, *args, **options):
        engine = SimpleWorkflowEngine()

        active_tasks = Task.objects.filter(
            workflow_id__isnull=False, workflow_status__in=["running", "waiting_user"]
        )

        for task in active_tasks:
            status = engine.get_workflow_status(task.workflow_id)

            if status["status"] != "not_found":

                task.workflow_status = status["status"]
                if "assigned_to" in status.get("data", {}):
                    task.assigned_to = status["data"]["assigned_to"]
                if "priority" in status.get("data", {}):
                    task.priority = status["data"]["priority"]
                task.save()

                self.stdout.write(
                    f"Task {task.id}: {status['status']} - Progress: {status.get('progress', 0):.1f}%"
                )

                if status.get("ready_tasks"):
                    self.stdout.write(
                        f"  Waiting for: {', '.join(status['ready_tasks'])}"
                    )
