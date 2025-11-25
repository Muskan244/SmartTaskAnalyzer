from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Task(models.Model):
    title = models.CharField(max_length=500)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.FloatField(
        default=2.0,
        validators=[MinValueValidator(0.1)]
    )
    importance = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_dependencies(self):
        return list(self.task_dependencies.values_list('depends_on_id', flat=True))

class TaskDependency(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='task_dependencies'
    )
    depends_on = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='dependent_tasks'
    )

    class Meta:
        unique_together = ('task', 'depends_on')

    def __str__(self):
        return f"{self.task.title} depends on {self.depends_on.title}"
