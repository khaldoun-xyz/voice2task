import logging

from django.core.management.base import BaseCommand

from core.workflows import TaskWorkflow
from tasks.models import Task
from tasks.simple_workflow import SimpleWorkflowEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Monitor workflow status and update tasks"

    def handle(self, *args, **options):
        engine = SimpleWorkflowEngine()
        workflow_engine = TaskWorkflow()

        active_tasks = Task.objects.filter(
            workflow_id__isnull=False,
            workflow_status__in=["running", "pending", "waiting_user"],
        )

        for task in active_tasks:
            try:
                status = engine.get_workflow_status(task.workflow_id)

                if status["status"] != "not_found":
                    task.workflow_status = status["status"]
                    update_fields = ["assigned_to", "priority"]
                    for field in update_fields:
                        if field in status.get("data", {}):
                            setattr(task, field, status["data"][field])

                    task.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Task {task.id} ({task.task_type}): {status['status']} "
                            f"- Progress: {status.get('progress', 0):.1f}%"
                        )
                    )

                    if status.get("ready_tasks"):
                        self.stdout.write(
                            self.style.NOTICE(
                                f"  Waiting for: {', '.join(status['ready_tasks'])}"
                            )
                        )

            except Exception as e:
                logger.error(f"Error processing task {task.id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Error processing task {task.id}: {str(e)}")
                )
                continue
