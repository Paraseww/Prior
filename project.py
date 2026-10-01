"""
project.py
Prior — Eisenhower Matrix Time Management Desktop Application.
CS50P Final Project implementation.
"""

from datetime import date, datetime
import re
import sys
from typing import Any, Dict, List, Optional

import database


def main() -> None:
    """
    Main entrypoint for Prior desktop application.
    Initializes local SQLite database and launches the GUI.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("parami.prior.taskmanager.1.0")

            # Automatically hide the console window if one was allocated
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass

    database.init_db()
    
    # Import and launch GUI application (Phase 3 & 4)
    try:
        from ui.app import launch_app
        launch_app()
    except ImportError:
        print("Prior database initialized successfully. UI components will launch in Phase 3.")


def determine_quadrant(is_urgent: bool, is_important: bool) -> str:
    """
    Classifies a task into one of four Eisenhower Matrix quadrants based on urgency and importance.

    :param is_urgent: Whether the task has an immediate deadline or requires rapid attention.
    :param is_important: Whether the task contributes significantly to long-term goals and values.
    :return: Quadrant identifier ('Q1_DO', 'Q2_SCHEDULE', 'Q3_DELEGATE', 'Q4_ELIMINATE').
    :raises TypeError: If either parameter is not a boolean.
    """
    if not isinstance(is_urgent, bool) or not isinstance(is_important, bool):
        raise TypeError("Arguments is_urgent and is_important must be booleans.")

    if is_urgent and is_important:
        return "Q1_DO"
    elif not is_urgent and is_important:
        return "Q2_SCHEDULE"
    elif is_urgent and not is_important:
        return "Q3_DELEGATE"
    else:
        return "Q4_ELIMINATE"


def filter_tasks(
    tasks: Optional[List[Dict[str, Any]]],
    search_query: str = "",
    quadrant_filter: str = "ALL",
    show_completed: bool = True,
) -> List[Dict[str, Any]]:
    """
    Filters a collection of tasks based on a search term, quadrant category, and completion state.

    :param tasks: List of task dictionaries (each containing 'title', 'description', 'quadrant', 'is_completed').
    :param search_query: Search string to match against title or description (case-insensitive).
    :param quadrant_filter: 'ALL' or a specific quadrant ('Q1_DO', 'Q2_SCHEDULE', 'Q3_DELEGATE', 'Q4_ELIMINATE').
    :param show_completed: Whether to include completed tasks in the output.
    :return: Filtered list of task dictionaries.
    """
    if not tasks:
        return []

    clean_query = search_query.strip().lower() if search_query else ""
    target_quadrant = quadrant_filter.strip().upper() if quadrant_filter else "ALL"

    filtered: List[Dict[str, Any]] = []

    for task in tasks:
        # Check completion filter
        is_completed = bool(task.get("is_completed", 0))
        if not show_completed and is_completed:
            continue

        # Check quadrant filter
        task_quadrant = str(task.get("quadrant", "")).upper()
        if target_quadrant != "ALL" and task_quadrant != target_quadrant:
            continue

        # Check search query filter
        if clean_query:
            title = str(task.get("title", "")).lower()
            description = str(task.get("description", "")).lower()
            if clean_query not in title and clean_query not in description:
                continue

        filtered.append(task)

    return filtered


def calculate_matrix_stats(tasks: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Calculates productivity statistics, completion rates, and quadrant distribution metrics.

    :param tasks: List of task dictionaries.
    :return: Dictionary with metrics:
             - 'total_tasks': Total number of tasks
             - 'completed_tasks': Number of completed tasks
             - 'pending_tasks': Number of active/pending tasks
             - 'completion_rate': Float percentage (0.0 to 100.0) rounded to 1 decimal place
             - 'quadrant_counts': Dict of active task counts per quadrant
             - 'focus_score': Float percentage of pending tasks residing in Q2_SCHEDULE
    """
    default_stats: Dict[str, Any] = {
        "total_tasks": 0,
        "completed_tasks": 0,
        "pending_tasks": 0,
        "completion_rate": 0.0,
        "quadrant_counts": {
            "Q1_DO": 0,
            "Q2_SCHEDULE": 0,
            "Q3_DELEGATE": 0,
            "Q4_ELIMINATE": 0,
        },
        "focus_score": 0.0,
    }

    if not tasks:
        return default_stats

    total = len(tasks)
    completed = 0
    quadrant_counts = {
        "Q1_DO": 0,
        "Q2_SCHEDULE": 0,
        "Q3_DELEGATE": 0,
        "Q4_ELIMINATE": 0,
    }

    for task in tasks:
        if bool(task.get("is_completed", 0)):
            completed += 1
        else:
            q = str(task.get("quadrant", "")).upper()
            if q in quadrant_counts:
                quadrant_counts[q] += 1

    pending = total - completed
    completion_rate = round((completed / total) * 100.0, 1) if total > 0 else 0.0

    # Focus Score: Measures effectiveness in proactive planning (Q2 tasks out of all pending tasks)
    focus_score = (
        round((quadrant_counts["Q2_SCHEDULE"] / pending) * 100.0, 1)
        if pending > 0
        else 0.0
    )

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": pending,
        "completion_rate": completion_rate,
        "quadrant_counts": quadrant_counts,
        "focus_score": focus_score,
    }


def format_due_status(
    due_date_str: Optional[str],
    current_date_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates a task's due date string (YYYY-MM-DD) and generates urgency status, remaining days,
    and formatted badge metadata.

    :param due_date_str: Target due date in 'YYYY-MM-DD' format.
    :param current_date_str: Optional reference date in 'YYYY-MM-DD' format (defaults to today).
    :return: Dictionary with:
             - 'status': 'OVERDUE', 'DUE_TODAY', 'UPCOMING', or 'NO_DUE_DATE'
             - 'days_diff': Integer difference in days (negative for overdue, 0 for today, positive for future)
             - 'label': Human-friendly badge string
             - 'color_tag': Badge color tag ('red', 'amber', 'blue', 'gray')
    """
    if not due_date_str or not isinstance(due_date_str, str) or not due_date_str.strip():
        return {
            "status": "NO_DUE_DATE",
            "days_diff": None,
            "label": "No Due Date",
            "color_tag": "gray",
        }

    # Validate YYYY-MM-DD format with regex
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    clean_due = due_date_str.strip()
    if not re.match(date_pattern, clean_due):
        return {
            "status": "INVALID_DATE",
            "days_diff": None,
            "label": "Invalid Date",
            "color_tag": "gray",
        }

    try:
        due = datetime.strptime(clean_due, "%Y-%m-%d").date()
    except ValueError:
        return {
            "status": "INVALID_DATE",
            "days_diff": None,
            "label": "Invalid Date",
            "color_tag": "gray",
        }

    # Reference current date
    if current_date_str and isinstance(current_date_str, str):
        try:
            today = datetime.strptime(current_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            today = date.today()
    else:
        today = date.today()

    diff_days = (due - today).days

    due_formatted = due.strftime("%b %d, %Y") if due.year != today.year else due.strftime("%b %d")

    if diff_days < 0:
        return {
            "status": "OVERDUE",
            "days_diff": diff_days,
            "label": f"Overdue: {due_formatted}",
            "color_tag": "red",
        }
    elif diff_days == 0:
        return {
            "status": "DUE_TODAY",
            "days_diff": 0,
            "label": f"Due: {due_formatted}",
            "color_tag": "amber",
        }
    else:
        return {
            "status": "UPCOMING",
            "days_diff": diff_days,
            "label": f"Due: {due_formatted}",
            "color_tag": "blue",
        }


def format_timer_display(seconds: int) -> str:
    """
    Formats total seconds into MM:SS display format for Pomodoro focus sessions.

    :param seconds: Total integer seconds (non-negative).
    :return: Formatted string (e.g. 1500 -> '25:00', 65 -> '01:05').
    :raises TypeError: If seconds is not an integer.
    :raises ValueError: If seconds is negative.
    """
    if not isinstance(seconds, int) or isinstance(seconds, bool):
        raise TypeError("Seconds argument must be an integer.")
    if seconds < 0:
        raise ValueError("Seconds cannot be negative.")

    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"


def get_task_notifications(
    tasks: Optional[List[Dict[str, Any]]],
    current_date_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Categorizes tasks into notification buckets based on their due date:
    - overdue: due_date < current_date (sorted oldest first)
    - today: due_date == current_date
    - tomorrow: due_date == current_date + 1 day
    - upcoming: due_date is within 2 to 3 days (current_date + 2 <= due_date <= current_date + 3)

    Only active / pending (non-completed) tasks with valid due_dates are considered.

    :param tasks: List of task dictionaries.
    :param current_date_str: Optional reference date in 'YYYY-MM-DD' format (defaults to today).
    :return: Dictionary containing:
             - 'total_count': Total number of notifying tasks
             - 'overdue_count': Count of overdue tasks
             - 'today_count': Count of tasks due today
             - 'tomorrow_count': Count of tasks due tomorrow
             - 'upcoming_count': Count of tasks due in 2-3 days
             - 'overdue': List of overdue task dicts (with 'days_diff' added, sorted oldest first)
             - 'today': List of today's task dicts (with 'days_diff' added)
             - 'tomorrow': List of tomorrow's task dicts (with 'days_diff' added)
             - 'upcoming': List of upcoming task dicts (with 'days_diff' added, sorted soonest first)
    """
    empty_result: Dict[str, Any] = {
        "total_count": 0,
        "overdue_count": 0,
        "today_count": 0,
        "tomorrow_count": 0,
        "upcoming_count": 0,
        "overdue": [],
        "today": [],
        "tomorrow": [],
        "upcoming": [],
    }

    if not tasks:
        return empty_result

    # Determine reference date
    if current_date_str and isinstance(current_date_str, str):
        try:
            today = datetime.strptime(current_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            today = date.today()
    else:
        today = date.today()

    date_pattern = r"^\d{4}-\d{2}-\d{2}$"

    overdue_list: List[Dict[str, Any]] = []
    today_list: List[Dict[str, Any]] = []
    tomorrow_list: List[Dict[str, Any]] = []
    upcoming_list: List[Dict[str, Any]] = []

    for task in tasks:
        # Ignore completed tasks
        if bool(task.get("is_completed", 0)):
            continue

        due_date_str = task.get("due_date")
        if not due_date_str or not isinstance(due_date_str, str) or not due_date_str.strip():
            continue

        clean_due = due_date_str.strip()
        if not re.match(date_pattern, clean_due):
            continue

        try:
            due = datetime.strptime(clean_due, "%Y-%m-%d").date()
        except ValueError:
            continue

        diff_days = (due - today).days

        # Create a shallow copy with days_diff attached
        task_item = dict(task)
        task_item["days_diff"] = diff_days

        if diff_days < 0:
            overdue_list.append(task_item)
        elif diff_days == 0:
            today_list.append(task_item)
        elif diff_days == 1:
            tomorrow_list.append(task_item)
        elif 2 <= diff_days <= 3:
            upcoming_list.append(task_item)

    # Sort overdue list by diff_days ascending (most overdue / oldest first)
    overdue_list.sort(key=lambda x: x["days_diff"])

    # Sort upcoming list by diff_days ascending (2 days left before 3 days left)
    upcoming_list.sort(key=lambda x: x["days_diff"])

    total_count = (
        len(overdue_list)
        + len(today_list)
        + len(tomorrow_list)
        + len(upcoming_list)
    )

    return {
        "total_count": total_count,
        "overdue_count": len(overdue_list),
        "today_count": len(today_list),
        "tomorrow_count": len(tomorrow_list),
        "upcoming_count": len(upcoming_list),
        "overdue": overdue_list,
        "today": today_list,
        "tomorrow": tomorrow_list,
        "upcoming": upcoming_list,
    }


if __name__ == "__main__":
    main()

