from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import Task, TaskDependency
from .serializers import (
    TaskSerializer,
    TaskCreateSerializer,
    AnalyzeRequestSerializer,
    SuggestRequestSerializer
)
from .scoring import calculate_priority_scores, get_top_suggestions
from .validators import validate_task_list, validate_strategy


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCreateSerializer
        return TaskSerializer

    def list(self, request):
        tasks = self.get_queryset()
        serializer = TaskSerializer(tasks, many=True)
        return Response({
            'success': True,
            'count': tasks.count(),
            'tasks': serializer.data
        })

    def create(self, request):
        serializer = TaskCreateSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save()
            return Response({
                'success': True,
                'task': TaskSerializer(task).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        try:
            task = Task.objects.get(pk=pk)
            serializer = TaskSerializer(task)
            return Response({
                'success': True,
                'task': serializer.data
            })
        except Task.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        try:
            task = Task.objects.get(pk=pk)
            serializer = TaskCreateSerializer(task, data=request.data)
            if serializer.is_valid():
                task = serializer.save()
                return Response({
                    'success': True,
                    'task': TaskSerializer(task).data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Task.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        try:
            task = Task.objects.get(pk=pk)
            task.delete()
            return Response({
                'success': True,
                'message': 'Task deleted successfully'
            })
        except Task.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def analyze_tasks(request):
    serializer = AnalyzeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    strategy = data.get('strategy', 'smart_balance')
    use_stored_tasks = data.get('use_stored_tasks', False)

    if use_stored_tasks:
        stored_tasks = Task.objects.all()
        tasks_data = []
        for task in stored_tasks:
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'estimated_hours': task.estimated_hours,
                'importance': task.importance,
                'dependencies': task.get_dependencies()
            })
    else:
        tasks_data = data.get('tasks', [])

    validated_tasks, warnings = validate_task_list(tasks_data)

    result = calculate_priority_scores(validated_tasks, strategy)

    result['warnings'] = warnings + result.get('warnings', [])

    return Response(result)


@api_view(['GET'])
def suggest_tasks(request):
    strategy = request.query_params.get('strategy', 'smart_balance')
    strategy, strategy_warning = validate_strategy(strategy)

    stored_tasks = Task.objects.all()
    tasks_data = []
    for task in stored_tasks:
        tasks_data.append({
            'id': task.id,
            'title': task.title,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'estimated_hours': task.estimated_hours,
            'importance': task.importance,
            'dependencies': task.get_dependencies()
        })

    if not tasks_data:
        return Response({
            'success': True,
            'suggestions': [],
            'strategy_used': strategy,
            'warnings': ['No tasks in database. Add tasks first or use POST /api/tasks/analyze/ with task data.']
        })

    result = get_top_suggestions(tasks_data, strategy, count=3)

    if strategy_warning:
        result['warnings'] = result.get('warnings', []) + [strategy_warning]

    return Response(result)
