const API_BASE = 'http://localhost:8000/api';

const state = {
    tasks: [],
    strategy: 'smart_balance',
    results: null,
    isLoading: false,
    nextId: 1
};

const STRATEGY_DESCRIPTIONS = {
    smart_balance: 'Balances urgency, importance, effort, and dependencies for optimal prioritization.',
    fastest_wins: 'Prioritizes quick tasks to build momentum and clear your list faster.',
    high_impact: 'Focuses on high-importance tasks regardless of effort or deadline.',
    deadline_driven: 'Prioritizes tasks by due date - urgent tasks come first.'
};

document.addEventListener('DOMContentLoaded', initApp);

function initApp() {
    initStrategyButtons();
    initTabs();
    initTaskForm();
    initJsonInput();
    initActionButtons();
    initImportanceSlider();
    initErrorDismiss();
    updateTaskList();
}

function initStrategyButtons() {
    document.querySelectorAll('.strategy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.strategy-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.strategy = btn.dataset.strategy;
            document.getElementById('strategy-desc').textContent = STRATEGY_DESCRIPTIONS[state.strategy];
        });
    });
}

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`${btn.dataset.tab}-tab`).classList.add('active');
        });
    });
}

function initTaskForm() {
    const form = document.getElementById('task-form');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        addTaskFromForm();
    });
}

function initJsonInput() {
    document.getElementById('parse-json').addEventListener('click', parseJsonInput);
}

function initActionButtons() {
    document.getElementById('analyze-btn').addEventListener('click', analyzeTasks);
    document.getElementById('clear-btn').addEventListener('click', clearAllTasks);
}

function initImportanceSlider() {
    const slider = document.getElementById('importance');
    const display = document.getElementById('importance-value');
    slider.addEventListener('input', () => {
        display.textContent = slider.value;
    });
}

function initErrorDismiss() {
    document.getElementById('dismiss-error').addEventListener('click', () => {
        document.getElementById('error').hidden = true;
    });
}

function addTaskFromForm() {
    const title = document.getElementById('title').value.trim();
    const dueDate = document.getElementById('due_date').value;
    const estimatedHours = parseFloat(document.getElementById('estimated_hours').value) || 2;
    const importance = parseInt(document.getElementById('importance').value) || 5;
    const dependenciesStr = document.getElementById('dependencies').value.trim();

    if (!title) {
        showError('Task title is required');
        return;
    }

    const dependencies = dependenciesStr
        ? dependenciesStr.split(',').map(d => parseInt(d.trim())).filter(d => !isNaN(d))
        : [];

    const task = {
        id: state.nextId++,
        title,
        due_date: dueDate || null,
        estimated_hours: estimatedHours,
        importance,
        dependencies
    };

    state.tasks.push(task);
    updateTaskList();
    resetForm();
}

function resetForm() {
    document.getElementById('task-form').reset();
    document.getElementById('importance-value').textContent = '5';
}

function parseJsonInput() {
    const jsonText = document.getElementById('json-input').value.trim();

    if (!jsonText) {
        showError('Please enter JSON data');
        return;
    }

    try {
        const parsed = JSON.parse(jsonText);
        const tasks = Array.isArray(parsed) ? parsed : [parsed];

        tasks.forEach(task => {
            if (!task.id) {
                task.id = state.nextId++;
            } else {
                state.nextId = Math.max(state.nextId, task.id + 1);
            }
            state.tasks.push(task);
        });

        updateTaskList();
        document.getElementById('json-input').value = '';

        document.querySelector('[data-tab="form"]').click();
    } catch (e) {
        showError(`Invalid JSON: ${e.message}`);
    }
}

function removeTask(id) {
    state.tasks = state.tasks.filter(t => t.id !== id);
    updateTaskList();
}

function clearAllTasks() {
    state.tasks = [];
    state.nextId = 1;
    updateTaskList();
    document.getElementById('results').hidden = true;
}

function updateTaskList() {
    const list = document.getElementById('task-list');
    const count = document.getElementById('task-count');
    const analyzeBtn = document.getElementById('analyze-btn');

    count.textContent = state.tasks.length;
    analyzeBtn.disabled = state.tasks.length === 0;

    if (state.tasks.length === 0) {
        list.innerHTML = '<li class="empty-state">No tasks added yet</li>';
        return;
    }

    list.innerHTML = state.tasks.map(task => `
        <li>
            <div class="task-info">
                <div class="task-title">${escapeHtml(task.title)}</div>
                <div class="task-meta">
                    ID: ${task.id} |
                    Due: ${task.due_date || 'No date'} |
                    ${task.estimated_hours}h |
                    Importance: ${task.importance}/10
                </div>
            </div>
            <button class="remove-btn" onclick="removeTask(${task.id})">×</button>
        </li>
    `).join('');
}

async function analyzeTasks() {
    if (state.tasks.length === 0) {
        showError('Please add at least one task');
        return;
    }

    setLoading(true);

    try {
        const response = await fetch(`${API_BASE}/tasks/analyze/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tasks: state.tasks,
                strategy: state.strategy
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        state.results = data;
        renderResults(data);

    } catch (error) {
        showError(`Failed to analyze tasks: ${error.message}`);
    } finally {
        setLoading(false);
    }
}

function renderResults(data) {
    const resultsSection = document.getElementById('results');
    resultsSection.hidden = false;

    renderSuggestions(data.tasks.slice(0, 3));
    renderAllTasks(data.tasks);
    renderWarnings(data.warnings || []);

    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function renderSuggestions(topTasks) {
    const container = document.getElementById('suggestion-cards');

    if (topTasks.length === 0) {
        container.innerHTML = '<p>No suggestions available</p>';
        return;
    }

    container.innerHTML = topTasks.map((task, index) => `
        <div class="suggestion-card">
            <div class="task-title">
                <span class="rank">${index + 1}</span>
                ${escapeHtml(task.title)}
            </div>
            <div class="reason">${escapeHtml(task.explanation)}</div>
        </div>
    `).join('');
}

function renderAllTasks(tasks) {
    const container = document.getElementById('task-results');

    if (tasks.length === 0) {
        container.innerHTML = '<p>No tasks to display</p>';
        return;
    }

    container.innerHTML = tasks.map(task => `
        <div class="task-card priority-${task.priority_level}">
            <div class="task-header">
                <h4>${escapeHtml(task.title)}</h4>
                <span class="score-badge ${task.priority_level}">
                    ${task.priority_score.toFixed(1)}
                </span>
            </div>
            <div class="task-details">
                <span class="detail"><strong>Due:</strong> ${formatDate(task.due_date)}</span>
                <span class="detail"><strong>Effort:</strong> ${task.estimated_hours}h</span>
                <span class="detail"><strong>Importance:</strong> ${task.importance}/10</span>
            </div>
            <div class="task-explanation">${escapeHtml(task.explanation)}</div>
            <div class="score-breakdown">
                <div class="score-item">
                    <div class="label">Urgency</div>
                    <div class="bar-container">
                        <div class="bar" style="width: ${task.scores.urgency * 10}%"></div>
                    </div>
                    <div class="value">${task.scores.urgency}</div>
                </div>
                <div class="score-item">
                    <div class="label">Importance</div>
                    <div class="bar-container">
                        <div class="bar" style="width: ${task.scores.importance * 10}%"></div>
                    </div>
                    <div class="value">${task.scores.importance}</div>
                </div>
                <div class="score-item">
                    <div class="label">Effort</div>
                    <div class="bar-container">
                        <div class="bar" style="width: ${task.scores.effort * 10}%"></div>
                    </div>
                    <div class="value">${task.scores.effort}</div>
                </div>
                <div class="score-item">
                    <div class="label">Dependency</div>
                    <div class="bar-container">
                        <div class="bar" style="width: ${task.scores.dependency * 10}%"></div>
                    </div>
                    <div class="value">${task.scores.dependency}</div>
                </div>
            </div>
        </div>
    `).join('');
}

function renderWarnings(warnings) {
    const panel = document.getElementById('warnings-panel');
    const list = document.getElementById('warning-list');

    if (warnings.length === 0) {
        panel.hidden = true;
        return;
    }

    panel.hidden = false;
    list.innerHTML = warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('');
}

function setLoading(loading) {
    state.isLoading = loading;
    document.getElementById('loading').hidden = !loading;
    document.getElementById('analyze-btn').disabled = loading || state.tasks.length === 0;
}

function showError(message) {
    const errorPanel = document.getElementById('error');
    document.getElementById('error-message').textContent = message;
    errorPanel.hidden = false;

    setTimeout(() => {
        errorPanel.hidden = true;
    }, 5000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return 'No date';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
