from rest_framework import serializers
from .models import Task, TaskDependency


class TaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDependency
        fields = ['id', 'depends_on']


class TaskSerializer(serializers.ModelSerializer):
    dependencies = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'due_date', 'estimated_hours', 'importance',
                  'dependencies', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_dependencies(self, obj):
        return obj.get_dependencies()


class TaskCreateSerializer(serializers.ModelSerializer):
    dependencies = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

    class Meta:
        model = Task
        fields = ['id', 'title', 'due_date', 'estimated_hours', 'importance', 'dependencies']

    def create(self, validated_data):
        dependencies = validated_data.pop('dependencies', [])
        task = Task.objects.create(**validated_data)

        for dep_id in dependencies:
            try:
                depends_on_task = Task.objects.get(id=dep_id)
                TaskDependency.objects.create(task=task, depends_on=depends_on_task)
            except Task.DoesNotExist:
                pass

        return task

    def update(self, instance, validated_data):
        dependencies = validated_data.pop('dependencies', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if dependencies is not None:
            instance.task_dependencies.all().delete()
            for dep_id in dependencies:
                try:
                    depends_on_task = Task.objects.get(id=dep_id)
                    TaskDependency.objects.create(task=instance, depends_on=depends_on_task)
                except Task.DoesNotExist:
                    pass

        return instance


class AnalyzeRequestSerializer(serializers.Serializer):
    tasks = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    strategy = serializers.ChoiceField(
        choices=['smart_balance', 'fastest_wins', 'high_impact', 'deadline_driven'],
        required=False,
        default='smart_balance'
    )
    use_stored_tasks = serializers.BooleanField(required=False, default=False)


class SuggestRequestSerializer(serializers.Serializer):
    strategy = serializers.ChoiceField(
        choices=['smart_balance', 'fastest_wins', 'high_impact', 'deadline_driven'],
        required=False,
        default='smart_balance'
    )
