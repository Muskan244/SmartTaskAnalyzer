from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, analyze_tasks, suggest_tasks

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('tasks/analyze/', analyze_tasks, name='analyze-tasks'),
    path('tasks/suggest/', suggest_tasks, name='suggest-tasks'),
    path('', include(router.urls)),
]
