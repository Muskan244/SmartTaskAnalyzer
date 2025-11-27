# Smart Task Analyzer

A Django + JavaScript application that intelligently scores and prioritizes tasks based on urgency, importance, effort, and dependencies.

## Algorithm Explanation

The Smart Task Analyzer uses a **weighted multi-factor scoring algorithm** to calculate priority scores for each task. The algorithm considers four key dimensions:

### Scoring Factors

1. **Urgency Score (0-10+)**: Calculated based on the due date proximity. Tasks due today receive a score of 10, with the score decreasing by 1 for each additional day until the deadline. Overdue tasks receive bonus points (10 + days overdue) to ensure they surface immediately. Tasks without due dates receive a minimal urgency score of 1.

2. **Importance Score (1-10)**: Directly mapped from user input. This subjective measure allows users to express how critical a task is to their goals, independent of deadlines.

3. **Effort Score (1-10)**: Inversely proportional to estimated hours. Quick tasks (under 1 hour) score 9-10, while large tasks (8+ hours) score lower. The formula `max(1, 10 - hours)` rewards smaller tasks that can be completed quickly, enabling momentum-building.

4. **Dependency Score (1-10)**: Analyzes task relationships in the dependency graph. Tasks that block many others receive bonus points (base 5 + 2 per dependent task). Blocked tasks receive penalties. The algorithm also detects circular dependencies using depth-first search, issuing warnings when cycles are found.

### Strategy Weights

The four strategies apply different weights to combine these scores:

| Strategy | Urgency | Importance | Effort | Dependency |
|----------|---------|------------|--------|------------|
| Smart Balance | 0.35 | 0.30 | 0.20 | 0.15 |
| Fastest Wins | 0.15 | 0.15 | 0.55 | 0.15 |
| High Impact | 0.20 | 0.50 | 0.15 | 0.15 |
| Deadline Driven | 0.55 | 0.20 | 0.10 | 0.15 |

The final priority score is computed as: `Σ(weight_i × score_i)` normalized to a 0-10 scale.

### Priority Levels

Tasks are categorized based on their final score:
- **Critical** (≥8): Requires immediate attention
- **High** (≥6): Important, schedule soon
- **Medium** (≥4): Normal priority
- **Low** (<4): Can be deferred

### Date Intelligence (Bonus Feature)

The algorithm includes **smart date handling** that considers weekends and holidays when calculating urgency:

- **Working Days Calculation**: Instead of counting calendar days, the algorithm counts only working days (Monday-Friday, excluding holidays)
- **Weekend Awareness**: A task due on Monday checked on Friday shows higher urgency because there's only 1 working day, not 3 calendar days
- **Holiday Support**: Common holidays (New Year's, Independence Day, Christmas, Boxing Day) are excluded from working day counts
- **Configurable**: Holidays can be customized per region/organization

**Example**: If today is Friday and a task is due Monday:
- Calendar days: 3 days → Medium urgency
- Working days: 1 day → High urgency (more accurate for work planning)

This feature helps users understand their *actual* available work time before deadlines.

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Open index.html in a browser, or use a simple HTTP server:
python -m http.server 3000
```

Access the frontend at `http://localhost:3000`

### Running Tests

```bash
cd backend
python manage.py test tasks
```

## API Endpoints

### POST /api/tasks/analyze/

Analyzes a list of tasks and returns prioritized results.

**Request Body:**
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Complete report",
      "due_date": "2025-12-01",
      "estimated_hours": 4,
      "importance": 8,
      "dependencies": []
    }
  ],
  "strategy": "smart_balance"
}
```

**Response:**
```json
{
  "success": true,
  "tasks": [
    {
      "id": 1,
      "title": "Complete report",
      "priority_score": 7.2,
      "priority_level": "high",
      "scores": {
        "urgency": 8,
        "importance": 8,
        "effort": 6,
        "dependency": 5
      },
      "explanation": "High importance task with approaching deadline"
    }
  ],
  "warnings": []
}
```

### GET /api/tasks/suggest/

Returns top 3 task suggestions from stored tasks.

### GET /api/tasks/

Lists all stored tasks.

### POST /api/tasks/

Creates a new task for persistence.

## Design Decisions

1. **Separation of Concerns**: Scoring logic is isolated in `scoring.py`, validation in `validators.py`, keeping views thin and testable.

2. **Flexible Input Handling**: The API accepts tasks via request body (for ad-hoc analysis) while also supporting database persistence for ongoing task management.

3. **Graceful Degradation**: Invalid inputs receive sensible defaults rather than errors. Missing titles become "Untitled Task", invalid dates are ignored, and importance values are clamped to 1-10.

4. **Circular Dependency Detection**: Using DFS with path tracking to detect cycles, the algorithm warns users but still processes tasks (excluding cyclic relationships from dependency scoring).

5. **Strategy Pattern**: Weights are stored in a dictionary, making it easy to add new strategies or allow custom weight configurations in the future.

## Project Structure

```
smartTaskAnalyzer/
├── backend/
│   ├── task_analyzer/        # Django project settings
│   │   ├── settings.py
│   │   └── urls.py
│   ├── tasks/                # Main application
│   │   ├── models.py         # Task, TaskDependency models
│   │   ├── scoring.py        # Priority calculation algorithm
│   │   ├── validators.py     # Input validation
│   │   ├── views.py          # API endpoints
│   │   ├── serializers.py    # DRF serializers
│   │   ├── urls.py           # URL routing
│   │   └── tests.py          # Unit tests
│   ├── requirements.txt
│   └── manage.py
└── frontend/
    ├── index.html            # Main HTML structure
    ├── styles.css            # Styling
    └── script.js             # Frontend logic
```

## Tech Stack

- **Backend**: Python, Django 4.2, Django REST Framework
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: SQLite (development)

## Bonus Challenges Implemented

1. **Unit Tests** (45 min) - 39 comprehensive tests covering:
   - Urgency, effort, importance, and dependency scoring
   - Circular dependency detection
   - Input validation and normalization
   - API endpoints
   - Date intelligence features

2. **Date Intelligence** (30 min) - Smart urgency calculation that:
   - Counts working days instead of calendar days
   - Excludes weekends (Saturday, Sunday)
   - Excludes common holidays
   - Shows working days context in task explanations
