from datetime import date, timedelta
from typing import Dict, List, Tuple, Any, Optional

STRATEGY_WEIGHTS = {
    'smart_balance': {'urgency': 0.30, 'importance': 0.30, 'effort': 0.20, 'dependency': 0.20},
    'fastest_wins': {'urgency': 0.15, 'importance': 0.15, 'effort': 0.60, 'dependency': 0.10},
    'high_impact': {'urgency': 0.15, 'importance': 0.60, 'effort': 0.10, 'dependency': 0.15},
    'deadline_driven': {'urgency': 0.60, 'importance': 0.15, 'effort': 0.10, 'dependency': 0.15},
}

def calculate_urgency_score(
    due_date: Optional[date], 
    today: Optional[date] = None
) -> float:
    if due_date is None:
        return 1.0
    if today is None:
        today = date.today()

    days_until_due = (due_date - today).days

    if days_until_due < 0:
        overdue_days = abs(days_until_due)
        return min(15, 10 + (overdue_days * 0.5))
    elif days_until_due == 0:
        return 10.0
    elif days_until_due <= 1:
        return 9.0
    elif days_until_due <= 3:
        return 8.0
    elif days_until_due <= 7:
        return 6.0
    elif days_until_due <= 14:
        return 4.0
    elif days_until_due <= 30:
        return 2.0
    else:
        return 1.0

def calculate_importance_score(importance: int) -> float:
    return float(max(1, min(10, importance)))

def calculate_effort_score(estimated_hours: float) -> float:
    if estimated_hours <= 0.5:
        return 10.0
    elif estimated_hours <= 1:
        return 9.0
    elif estimated_hours <= 2:
        return 8.0
    elif estimated_hours <= 4:
        return 6.0
    elif estimated_hours <= 8:
        return 4.0
    elif estimated_hours <= 16:
        return 2.0
    else:
        return 1.0

def calculate_dependency_score(
    task_id: int,
    all_tasks: List[Dict],
    blocked_task_ids: set
) -> float:
    blocked_count = 0
    for task in all_tasks:
        deps = task.get('dependencies', [])
        if task_id in deps:
            blocked_count += 1

    is_blocked = task_id in blocked_task_ids

    if is_blocked:
        base_score = 2.0
    else:
        base_score = 5.0

    blocker_bonus = min(5.0, blocked_count * 1.5)

    return min(10.0, base_score + blocker_bonus)


def detect_circular_dependencies(tasks: List[Dict]) -> Tuple[bool, List[List[int]]]:
    graph = {}
    task_ids = set()

    for task in tasks:
        task_id = task.get('id')
        if task_id is not None:
            task_ids.add(task_id)
            graph[task_id] = task.get('dependencies', [])

    state = {tid: 0 for tid in task_ids}
    cycles = []

    def dfs(node: int, path: List[int]) -> None:
        if node not in task_ids:
            return

        if state[node] == 1:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return

        if state[node] == 2:
            return

        state[node] = 1
        path.append(node)

        for dep in graph.get(node, []):
            dfs(dep, path)

        path.pop()
        state[node] = 2

    for task_id in task_ids:
        if state[task_id] == 0:
            dfs(task_id, [])

    return len(cycles) > 0, cycles


def get_blocked_task_ids(tasks: List[Dict]) -> set:
    task_ids = {task.get('id') for task in tasks if task.get('id') is not None}
    blocked = set()

    for task in tasks:
        task_id = task.get('id')
        deps = task.get('dependencies', [])
        for dep_id in deps:
            if dep_id in task_ids:
                blocked.add(task_id)
                break

    return blocked


def generate_explanation(
    task: Dict,
    scores: Dict[str, float],
    days_until_due: Optional[int]
) -> str:
    explanations = []

    if days_until_due is not None:
        if days_until_due < 0:
            explanations.append(f"OVERDUE by {abs(days_until_due)} day(s)")
        elif days_until_due == 0:
            explanations.append("Due TODAY")
        elif days_until_due == 1:
            explanations.append("Due tomorrow")
        elif days_until_due <= 3:
            explanations.append(f"Due in {days_until_due} days")
        elif days_until_due <= 7:
            explanations.append("Due this week")

    importance = task.get('importance', 5)
    if importance >= 8:
        explanations.append(f"High importance ({importance}/10)")
    elif importance >= 6:
        explanations.append(f"Medium-high importance ({importance}/10)")

    hours = task.get('estimated_hours', 2)
    if hours <= 1:
        explanations.append(f"Quick win ({hours}h)")
    elif hours >= 8:
        explanations.append(f"Large task ({hours}h)")

    if scores.get('dependency', 5) >= 7:
        explanations.append("Blocks other tasks")
    elif scores.get('dependency', 5) <= 3:
        explanations.append("Blocked by dependencies")

    return " | ".join(explanations) if explanations else "Standard priority task"


def get_priority_level(score: float) -> str:
    if score >= 7:
        return 'high'
    elif score >= 4:
        return 'medium'
    else:
        return 'low'


def calculate_priority_scores(
    tasks: List[Dict],
    strategy: str = 'smart_balance'
) -> Dict[str, Any]:
    if not tasks:
        return {
            'success': True,
            'strategy': strategy,
            'tasks': [],
            'metadata': {
                'total_tasks': 0,
                'has_circular_dependencies': False,
                'circular_dependency_cycles': []
            },
            'warnings': ['No tasks provided for analysis']
        }

    weights = STRATEGY_WEIGHTS.get(strategy, STRATEGY_WEIGHTS['smart_balance'])

    has_cycles, cycles = detect_circular_dependencies(tasks)

    blocked_task_ids = get_blocked_task_ids(tasks)

    today = date.today()
    scored_tasks = []
    warnings = []

    if has_cycles:
        warnings.append(f"Circular dependencies detected: {cycles}")

    for task in tasks:
        task_id = task.get('id')
        due_date = task.get('due_date')

        if isinstance(due_date, str):
            try:
                from datetime import datetime
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                due_date = None
                warnings.append(f"Invalid date format for task {task_id}")

        days_until_due = None
        if due_date:
            days_until_due = (due_date - today).days

        urgency = calculate_urgency_score(due_date, today)
        importance = calculate_importance_score(task.get('importance', 5))
        effort = calculate_effort_score(task.get('estimated_hours', 2))
        dependency = calculate_dependency_score(task_id, tasks, blocked_task_ids)

        priority_score = (
            weights['urgency'] * min(urgency, 10) +
            weights['importance'] * importance +
            weights['effort'] * effort +
            weights['dependency'] * dependency
        )

        scores = {
            'urgency': round(min(urgency, 10), 2),
            'importance': round(importance, 2),
            'effort': round(effort, 2),
            'dependency': round(dependency, 2)
        }

        explanation = generate_explanation(task, scores, days_until_due)

        priority_level = get_priority_level(priority_score)

        is_overdue = days_until_due is not None and days_until_due < 0
        if is_overdue:
            priority_level = 'overdue'

        scored_task = {
            'id': task_id,
            'title': task.get('title', 'Untitled'),
            'due_date': due_date.isoformat() if due_date else None,
            'estimated_hours': task.get('estimated_hours', 2),
            'importance': task.get('importance', 5),
            'dependencies': task.get('dependencies', []),
            'priority_score': round(priority_score, 2),
            'priority_level': priority_level,
            'scores': scores,
            'explanation': explanation,
            'is_overdue': is_overdue,
            '_raw_urgency': urgency
        }

        scored_tasks.append(scored_task)

    scored_tasks.sort(key=lambda x: (x['_raw_urgency'], x['priority_score']), reverse=True)

    for task in scored_tasks:
        del task['_raw_urgency']

    return {
        'success': True,
        'strategy': strategy,
        'tasks': scored_tasks,
        'metadata': {
            'total_tasks': len(scored_tasks),
            'has_circular_dependencies': has_cycles,
            'circular_dependency_cycles': cycles
        },
        'warnings': warnings
    }


def get_top_suggestions(
    tasks: List[Dict],
    strategy: str = 'smart_balance',
    count: int = 3
) -> Dict[str, Any]:
    result = calculate_priority_scores(tasks, strategy)

    if not result['success'] or not result['tasks']:
        return {
            'success': True,
            'suggestions': [],
            'strategy_used': strategy,
            'warnings': result.get('warnings', [])
        }

    suggestions = []
    for rank, task in enumerate(result['tasks'][:count], 1):
        reasons = []

        if task.get('is_overdue'):
            reasons.append(f"This task is overdue and needs immediate attention.")
        elif task['scores']['urgency'] >= 9:
            reasons.append(f"Due very soon - high urgency.")

        if task['scores']['importance'] >= 8:
            reasons.append(f"High importance rating ({task['importance']}/10).")

        if task['scores']['effort'] >= 8:
            reasons.append(f"Quick win - only {task['estimated_hours']}h estimated.")

        if task['scores']['dependency'] >= 7:
            reasons.append(f"Completing this will unblock other tasks.")

        if not reasons:
            reasons.append("Balanced priority based on all factors.")

        suggestions.append({
            'rank': rank,
            'task': task,
            'reason': ' '.join(reasons)
        })

    return {
        'success': True,
        'suggestions': suggestions,
        'strategy_used': strategy,
        'warnings': result.get('warnings', [])
    }
