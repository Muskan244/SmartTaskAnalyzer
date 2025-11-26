from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

TASK_DEFAULTS = {
    'title': 'Untitled Task',
    'due_date': None,
    'estimated_hours': 2.0,
    'importance': 5,
    'dependencies': []
}

def parse_date(date_value: Any) -> Optional[date]:
    if date_value is None:
        return None
    if isinstance(date_value, date):
        return date_value
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value, '%Y-%m-%d').date()
        except ValueError:
            return None
    return None

def validate_and_normalize_task(
    task: Dict, 
    task_index: int = 0
) -> Tuple[Dict, List[str]]:
    warnings = []
    normalized = {}
    if task.get('id') is not None:
        normalized['id'] = task['id']
    else:
        normalized['id'] = f"task-{task_index}"
        warnings.append(f"Task {task_index}: Missing ID, generated '{normalized['id']}'")

    title = task.get('title')
    if not title or not str(title).strip():
        normalized['title'] = TASK_DEFAULTS['title']
        warnings.append(f"Task {normalized['id']}: Missing title, using default")
    else:
        normalized['title'] = str(title).strip()[:500]

    due_date = task.get('due_date')
    parsed_date = parse_date(due_date)
    if due_date is not None and parsed_date is None:
        warnings.append(f"Task {normalized['id']}: Invalid date format '{due_date}', setting to None")
    normalized['due_date'] = parsed_date

    try:
        hours = float(task.get('estimated_hours', TASK_DEFAULTS['estimated_hours']))
        if hours < 0.1:
            hours = 0.1
            warnings.append(f"Task {normalized['id']}: estimated_hours too low, set to 0.1")
        elif hours > 1000:
            hours = 1000
            warnings.append(f"Task {normalized['id']}: estimated_hours too high, capped at 1000")
        normalized['estimated_hours'] = hours
    except (ValueError, TypeError):
        normalized['estimated_hours'] = TASK_DEFAULTS['estimated_hours']
        warnings.append(f"Task {normalized['id']}: Invalid estimated_hours, using default (2h)")

    try:
        importance = int(task.get('importance', TASK_DEFAULTS['importance']))
        if importance < 1:
            importance = 1
            warnings.append(f"Task {normalized['id']}: importance below 1, set to 1")
        elif importance > 10:
            importance = 10
            warnings.append(f"Task {normalized['id']}: importance above 10, capped at 10")
        normalized['importance'] = importance
    except (ValueError, TypeError):
        normalized['importance'] = TASK_DEFAULTS['importance']
        warnings.append(f"Task {normalized['id']}: Invalid importance, using default (5)")

    deps = task.get('dependencies', TASK_DEFAULTS['dependencies'])
    if isinstance(deps, list):
        normalized['dependencies'] = [d for d in deps if d is not None]
    else:
        normalized['dependencies'] = []
        warnings.append(f"Task {normalized['id']}: Invalid dependencies format, using empty list")

    return normalized, warnings

def validate_task_list(tasks: Any) -> Tuple[List[Dict], List[str]]:
    all_warnings = []

    if tasks is None:
        return [], ["No tasks provided"]

    if not isinstance(tasks, list):
        return [], ["Tasks must be a list"]

    if len(tasks) == 0:
        return [], ["Empty task list provided"]

    normalized_tasks = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            all_warnings.append(f"Task at index {index}: Not a valid object, skipped")
            continue

        normalized, warnings = validate_and_normalize_task(task, index)
        normalized_tasks.append(normalized)
        all_warnings.extend(warnings)

    return normalized_tasks, all_warnings

def validate_strategy(strategy: Any) -> Tuple[str, Optional[str]]:
    valid_strategies = ['smart_balance', 'fastest_wins', 'high_impact', 'deadline_driven']

    if strategy is None:
        return 'smart_balance', None

    if not isinstance(strategy, str):
        return 'smart_balance', f"Invalid strategy type, using default 'smart_balance'"

    strategy = strategy.lower().strip()

    if strategy not in valid_strategies:
        return 'smart_balance', f"Unknown strategy '{strategy}', using default 'smart_balance'"

    return strategy, None
