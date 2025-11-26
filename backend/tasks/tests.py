from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta
from .scoring import (
    calculate_urgency_score,
    calculate_importance_score,
    calculate_effort_score,
    calculate_dependency_score,
    detect_circular_dependencies,
    calculate_priority_scores,
    get_top_suggestions
)
from .validators import validate_and_normalize_task, validate_task_list, validate_strategy
from .models import Task

class UrgencyScoreTests(TestCase):
    def test_overdue_task_gets_high_urgency(self):
        yesterday = date.today() - timedelta(days=1)
        score = calculate_urgency_score(yesterday, date.today())
        self.assertGreaterEqual(score, 10)

    def test_overdue_task_increases_with_days(self):
        one_day_overdue = date.today() - timedelta(days=1)
        five_days_overdue = date.today() - timedelta(days=5)

        score_1 = calculate_urgency_score(one_day_overdue, date.today())
        score_5 = calculate_urgency_score(five_days_overdue, date.today())

        self.assertGreater(score_5, score_1)

    def test_task_due_today_gets_score_10(self):
        score = calculate_urgency_score(date.today(), date.today())
        self.assertEqual(score, 10.0)

    def test_task_due_tomorrow_gets_score_9(self):
        tomorrow = date.today() + timedelta(days=1)
        score = calculate_urgency_score(tomorrow, date.today())
        self.assertEqual(score, 9.0)

    def test_task_due_in_week_gets_medium_urgency(self):
        due_date = date.today() + timedelta(days=5)
        score = calculate_urgency_score(due_date, date.today())
        self.assertEqual(score, 6.0)

    def test_task_without_due_date_gets_low_urgency(self):
        score = calculate_urgency_score(None, date.today())
        self.assertEqual(score, 1.0)

class EffortScoreTests(TestCase):
    def test_quick_task_gets_high_score(self):
        score = calculate_effort_score(0.5)
        self.assertEqual(score, 10.0)

    def test_one_hour_task_gets_score_9(self):
        score = calculate_effort_score(1.0)
        self.assertEqual(score, 9.0)

    def test_full_day_task_gets_medium_score(self):
        score = calculate_effort_score(8)
        self.assertEqual(score, 4.0)

    def test_large_task_gets_low_score(self):
        score = calculate_effort_score(20)
        self.assertEqual(score, 1.0)

class DependencyScoreTests(TestCase):
    def test_blocking_task_gets_bonus(self):
        tasks = [
            {'id': 1, 'dependencies': []},
            {'id': 2, 'dependencies': [1]},
            {'id': 3, 'dependencies': [1]},
        ]
        score = calculate_dependency_score(1, tasks, set())
        self.assertGreater(score, 5)

    def test_blocked_task_gets_penalty(self):
        tasks = [
            {'id': 1, 'dependencies': []},
            {'id': 2, 'dependencies': [1]},
        ]
        blocked_ids = {2}
        score = calculate_dependency_score(2, tasks, blocked_ids)
        self.assertLess(score, 5)

    def test_independent_task_gets_base_score(self):
        tasks = [
            {'id': 1, 'dependencies': []},
            {'id': 2, 'dependencies': []},
        ]
        score = calculate_dependency_score(1, tasks, set())
        self.assertEqual(score, 5.0)

class CircularDependencyTests(TestCase):
    def test_detects_simple_cycle(self):
        tasks = [
            {'id': 1, 'dependencies': [2]},
            {'id': 2, 'dependencies': [1]},
        ]
        has_cycles, cycles = detect_circular_dependencies(tasks)
        self.assertTrue(has_cycles)

    def test_detects_complex_cycle(self):
        tasks = [
            {'id': 1, 'dependencies': [2]},
            {'id': 2, 'dependencies': [3]},
            {'id': 3, 'dependencies': [1]},
        ]
        has_cycles, cycles = detect_circular_dependencies(tasks)
        self.assertTrue(has_cycles)

    def test_no_false_positive_on_dag(self):
        tasks = [
            {'id': 1, 'dependencies': []},
            {'id': 2, 'dependencies': [1]},
            {'id': 3, 'dependencies': [1, 2]},
        ]
        has_cycles, cycles = detect_circular_dependencies(tasks)
        self.assertFalse(has_cycles)

class PriorityScoreIntegrationTests(TestCase):
    def test_overdue_important_task_ranks_highest(self):
        tasks = [
            {
                'id': 1,
                'title': 'Overdue important',
                'due_date': (date.today() - timedelta(days=2)).isoformat(),
                'estimated_hours': 4,
                'importance': 9,
                'dependencies': []
            },
            {
                'id': 2,
                'title': 'Future low importance',
                'due_date': (date.today() + timedelta(days=30)).isoformat(),
                'estimated_hours': 1,
                'importance': 3,
                'dependencies': []
            }
        ]

        result = calculate_priority_scores(tasks, 'smart_balance')
        self.assertEqual(result['tasks'][0]['id'], 1)

    def test_strategy_changes_ranking(self):
        tasks = [
            {
                'id': 1,
                'title': 'Quick low importance',
                'due_date': (date.today() + timedelta(days=10)).isoformat(),
                'estimated_hours': 0.5,
                'importance': 3,
                'dependencies': []
            },
            {
                'id': 2,
                'title': 'Slow high importance',
                'due_date': (date.today() + timedelta(days=10)).isoformat(),
                'estimated_hours': 8,
                'importance': 9,
                'dependencies': []
            }
        ]

        fastest = calculate_priority_scores(tasks, 'fastest_wins')
        high_impact = calculate_priority_scores(tasks, 'high_impact')

        self.assertEqual(fastest['tasks'][0]['id'], 1)
        self.assertEqual(high_impact['tasks'][0]['id'], 2)

    def test_empty_task_list_handled(self):
        result = calculate_priority_scores([], 'smart_balance')
        self.assertTrue(result['success'])
        self.assertEqual(len(result['tasks']), 0)
        self.assertIn('No tasks provided', result['warnings'][0])

class ValidationTests(TestCase):
    def test_valid_task_passes(self):
        task = {
            'id': 1,
            'title': 'Valid task',
            'due_date': '2025-12-01',
            'estimated_hours': 3,
            'importance': 7,
            'dependencies': []
        }
        normalized, warnings = validate_and_normalize_task(task)
        self.assertEqual(normalized['title'], 'Valid task')
        self.assertEqual(len(warnings), 0)

    def test_missing_title_gets_default(self):
        task = {'id': 1, 'title': ''}
        normalized, warnings = validate_and_normalize_task(task)
        self.assertEqual(normalized['title'], 'Untitled Task')
        self.assertTrue(any('Missing title' in w for w in warnings))

    def test_invalid_importance_gets_clamped(self):
        task = {'id': 1, 'title': 'Test', 'importance': 15}
        normalized, warnings = validate_and_normalize_task(task)
        self.assertEqual(normalized['importance'], 10)

    def test_invalid_date_handled(self):
        task = {'id': 1, 'title': 'Test', 'due_date': 'not-a-date'}
        normalized, warnings = validate_and_normalize_task(task)
        self.assertIsNone(normalized['due_date'])
        self.assertTrue(any('Invalid date' in w for w in warnings))

    def test_strategy_validation(self):
        strategy, warning = validate_strategy('unknown_strategy')
        self.assertEqual(strategy, 'smart_balance')
        self.assertIsNotNone(warning)

class SuggestionsTests(TestCase):
    def test_returns_top_3_suggestions(self):
        tasks = [
            {'id': i, 'title': f'Task {i}', 'due_date': (date.today() + timedelta(days=i)).isoformat(),
             'estimated_hours': 2, 'importance': 5, 'dependencies': []}
            for i in range(1, 6)
        ]

        result = get_top_suggestions(tasks, 'smart_balance', count=3)
        self.assertEqual(len(result['suggestions']), 3)

    def test_suggestions_have_reasons(self):
        tasks = [
            {'id': 1, 'title': 'Urgent', 'due_date': date.today().isoformat(),
             'estimated_hours': 1, 'importance': 9, 'dependencies': []}
        ]

        result = get_top_suggestions(tasks, 'smart_balance')
        self.assertTrue(len(result['suggestions']) > 0)
        self.assertIn('reason', result['suggestions'][0])

class APIEndpointTests(APITestCase):
    def test_analyze_endpoint(self):
        data = {
            'tasks': [
                {'id': 1, 'title': 'Test task', 'due_date': '2025-12-01',
                 'estimated_hours': 2, 'importance': 7, 'dependencies': []}
            ],
            'strategy': 'smart_balance'
        }

        response = self.client.post('/api/tasks/analyze/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['tasks']), 1)
        self.assertIn('priority_score', response.data['tasks'][0])

    def test_suggest_endpoint(self):
        Task.objects.create(
            title='Test task',
            due_date=date.today() + timedelta(days=5),
            estimated_hours=2,
            importance=7
        )

        response = self.client.get('/api/tasks/suggest/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_create_task_endpoint(self):
        data = {
            'title': 'New task',
            'due_date': '2025-12-01',
            'estimated_hours': 3,
            'importance': 8
        }

        response = self.client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(Task.objects.count(), 1)

    def test_list_tasks_endpoint(self):
        Task.objects.create(title='Task 1', importance=5)
        Task.objects.create(title='Task 2', importance=7)

        response = self.client.get('/api/tasks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
