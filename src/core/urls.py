"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from tasks.views import (
    home, 
    process_voice, 
    workflow_status, 
    complete_workflow_task_view,
    task_list,
    task_detail,
    update_task
)

urlpatterns = [
    path('', home, name='home'),
    path("admin/", admin.site.urls),
    path('api/process-voice/', process_voice, name='process_voice'),
    path('api/workflow/<str:workflow_id>/status/', workflow_status, name='workflow_status'),
    path('api/workflow/<str:workflow_id>/task/<str:task_name>/complete/', complete_workflow_task_view, name='complete_workflow_task'),
    path('tasks/', task_list, name='task_list'),
    path('task/<int:task_id>/', update_task, name='update_task'),
    path('task/<int:task_id>/detail/', task_detail, name='task_detail'),
]