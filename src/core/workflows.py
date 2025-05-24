from SpiffWorkflow import Workflow
from SpiffWorkflow.bpmn import BpmnParser

class TaskWorkflow:
    def __init__(self):
        self.parser = BpmnParser()
        self.parser.add_bpmn_file("src/tasks/workflows/task_processing.bpmn")
    
    def run(self, task_data: dict):
        workflow = Workflow(self.parser.get_spec())
        workflow.run(task_data)
        return workflow.last_task.data