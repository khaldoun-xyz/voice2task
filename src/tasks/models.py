from django.db import models

class Task(models.Model):
    user = models.CharField(max_length=100)  
    voice_input = models.TextField()
    action = models.CharField(max_length=50) 
    person = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=200, blank=True)  
    deadline = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} {self.person} about {self.topic} by {self.deadline}"