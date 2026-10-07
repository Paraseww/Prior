"""
project.py
Prior — Eisenhower Matrix Time Management Desktop Application.
CS50P Final Project implementation.
"""

import os
import sys
import tempfile

# Route all temporary files to local .tmp directory on Drive G: (which has 350+ GB free)
# Prevents OSError [Errno 28] 'No space left on device' when host C: drive is full
_temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tmp")
os.makedirs(_temp_dir, exist_ok=True)
os.environ["TEMP"] = _temp_dir
os.environ["TMP"] = _temp_dir
tempfile.tempdir = _temp_dir

from datetime import date, datetime, timedelta
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import database


def is_existing_instance_running(signal_notifications: bool = False) -> bool:
    """
    Checks if an existing instance of Prior is already running.
    If so, communicates with it via local IPC to bring it to foreground,
    optionally opens the notification modal, and returns True.
    """
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 49281), timeout=0.6) as s:
            msg = b"open_notifications\n" if signal_notifications else b"show\n"
            s.sendall(msg)

        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.FindWindowW(None, "Prior - Eisenhower Matrix Task Manager")
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        return True
    except Exception:
        return False


def main() -> None:
    """
    Main entrypoint for Prior desktop application.
    Initializes local SQLite database and launches the GUI.
    """
    is_notification_trigger = "--open-notifications" in sys.argv or any("prior://" in arg.lower() for arg in sys.argv)
    if is_existing_instance_running(signal_notifications=is_notification_trigger):
        sys.exit(0)

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


def calculate_matrix_stats(
    tasks: Optional[List[Dict[str, Any]]],
    current_date_str: Optional[str] = None,
    target_proactive_tasks: int = 4,
) -> Dict[str, Any]:
    """
    Calculates productivity statistics, completion rates, and quadrant distribution metrics.

    Evaluates the Proactive Pipeline Health (Focus Score) based on a weekly buffer target
    of scheduled, forward-looking Q2 tasks (default: 4 tasks). Overdue/delayed tasks are
    excluded from the proactive count.

    :param tasks: List of task dictionaries.
    :param current_date_str: Optional reference date in 'YYYY-MM-DD' format (defaults to today).
    :param target_proactive_tasks: Target count of active upcoming Q2 tasks for 100% health (default: 4).
    :return: Dictionary with metrics:
             - 'total_tasks': Total number of tasks
             - 'completed_tasks': Number of completed tasks
             - 'pending_tasks': Number of active/pending tasks
             - 'completion_rate': Float percentage (0.0 to 100.0) rounded to 1 decimal place
             - 'quadrant_counts': Dict of active task counts per quadrant
             - 'quadrant_completed': Dict of completed task counts per quadrant
             - 'proactive_q2_tasks': Count of active Q2 tasks scheduled for today, upcoming, or unscheduled (not overdue)
             - 'target_q2_tasks': Target number of proactive Q2 tasks (default: 4)
             - 'focus_score': Float percentage (0.0 to 100.0) representing proactive pipeline health against target
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
        "quadrant_completed": {
            "Q1_DO": 0,
            "Q2_SCHEDULE": 0,
            "Q3_DELEGATE": 0,
            "Q4_ELIMINATE": 0,
        },
        "proactive_q2_tasks": 0,
        "target_q2_tasks": target_proactive_tasks,
        "focus_score": 0.0,
    }

    if not tasks:
        return default_stats

    # Determine reference date for evaluating overdue status
    if current_date_str and isinstance(current_date_str, str):
        try:
            today = datetime.strptime(current_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            today = date.today()
    else:
        today = date.today()

    total = len(tasks)
    completed = 0
    proactive_q2 = 0
    quadrant_counts = {
        "Q1_DO": 0,
        "Q2_SCHEDULE": 0,
        "Q3_DELEGATE": 0,
        "Q4_ELIMINATE": 0,
    }
    quadrant_completed = {
        "Q1_DO": 0,
        "Q2_SCHEDULE": 0,
        "Q3_DELEGATE": 0,
        "Q4_ELIMINATE": 0,
    }

    for task in tasks:
        q = str(task.get("quadrant", "")).upper()
        if bool(task.get("is_completed", 0)):
            completed += 1
            if q in quadrant_completed:
                quadrant_completed[q] += 1
        else:
            if q in quadrant_counts:
                quadrant_counts[q] += 1

            if q == "Q2_SCHEDULE":
                # Check whether the task is overdue / delayed
                due_val = task.get("due_date")
                is_overdue = False
                if due_val:
                    if isinstance(due_val, date) and not isinstance(due_val, datetime):
                        if due_val < today:
                            is_overdue = True
                    elif isinstance(due_val, datetime):
                        if due_val.date() < today:
                            is_overdue = True
                    elif isinstance(due_val, str) and due_val.strip():
                        clean_due = due_val.strip()
                        if re.match(r"^\d{4}-\d{2}-\d{2}$", clean_due):
                            try:
                                due_date_obj = datetime.strptime(clean_due[:10], "%Y-%m-%d").date()
                                if due_date_obj < today:
                                    is_overdue = True
                            except ValueError:
                                pass
                if not is_overdue:
                    proactive_q2 += 1

    pending = total - completed
    completion_rate = round((completed / total) * 100.0, 1) if total > 0 else 0.0

    # Focus Score: Solution 2 — Proactive Pipeline Health Target
    # Measures how well-stocked your upcoming Q2 schedule is against a target buffer (default: 4 tasks)
    focus_score = (
        min(100.0, round((proactive_q2 / target_proactive_tasks) * 100.0, 1))
        if target_proactive_tasks > 0
        else 0.0
    )

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": pending,
        "completion_rate": completion_rate,
        "quadrant_counts": quadrant_counts,
        "quadrant_completed": quadrant_completed,
        "proactive_q2_tasks": proactive_q2,
        "target_q2_tasks": target_proactive_tasks,
        "focus_score": focus_score,
    }


def is_task_delayed(
    task: Optional[Dict[str, Any]],
    current_dt: Optional[datetime] = None,
    current_date_str: Optional[str] = None,
) -> bool:
    """
    Determines whether an active task is delayed / passed its scheduled deadline.
    A task is considered delayed if:
    - It is not completed, AND
    - Its due date is strictly in the past (< today), OR
    - Its due date is today AND its reminder_time has already passed current time.
    """
    if not task or not isinstance(task, dict):
        return False
    if bool(task.get("is_completed", 0)):
        return False

    due_date_str = task.get("due_date")
    if not due_date_str or not isinstance(due_date_str, str) or not due_date_str.strip():
        return False

    clean_due = due_date_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", clean_due):
        return False

    if current_dt is not None:
        now = current_dt
        today = now.date()
    elif current_date_str and isinstance(current_date_str, str):
        try:
            today = datetime.strptime(current_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            today = date.today()
        now = datetime.combine(today, datetime.now().time())
    else:
        now = datetime.now()
        today = now.date()

    try:
        due = datetime.strptime(clean_due, "%Y-%m-%d").date()
    except ValueError:
        return False

    if due < today:
        return True

    if due == today:
        rem_str = task.get("reminder_time")
        if rem_str and str(rem_str).strip():
            rem_time = None
            for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
                try:
                    rem_time = datetime.strptime(str(rem_str).strip(), fmt).time()
                    break
                except ValueError:
                    pass
            if rem_time is not None:
                if (rem_time.hour, rem_time.minute) <= (now.hour, now.minute):
                    return True

    return False


def format_due_status(
    due_date_str: Optional[str],
    current_date_str: Optional[str] = None,
    reminder_time_str: Optional[str] = None,
    current_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Evaluates a task's due date string (YYYY-MM-DD) and optional reminder time,
    generating urgency status, remaining days, and formatted badge metadata.

    :param due_date_str: Target due date in 'YYYY-MM-DD' format.
    :param current_date_str: Optional reference date in 'YYYY-MM-DD' format (defaults to today).
    :param reminder_time_str: Optional reminder time string (e.g. '06:00 AM', '14:30').
    :param current_dt: Optional reference datetime for exact timestamp evaluation.
    :return: Dictionary with:
             - 'status': 'OVERDUE', 'DUE_TODAY', 'UPCOMING', or 'NO_DUE_DATE'
             - 'days_diff': Integer difference in days (negative for overdue, 0 for today, positive for future)
             - 'label': Human-friendly badge string
             - 'color_tag': Badge color tag ('red', 'amber', 'blue', 'gray')
             - 'is_delayed': Boolean flag indicating if task is past its due time
    """
    if not due_date_str or not isinstance(due_date_str, str) or not due_date_str.strip():
        return {
            "status": "NO_DUE_DATE",
            "days_diff": None,
            "label": "No Due Date",
            "color_tag": "gray",
            "is_delayed": False,
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
            "is_delayed": False,
        }

    try:
        due = datetime.strptime(clean_due, "%Y-%m-%d").date()
    except ValueError:
        return {
            "status": "INVALID_DATE",
            "days_diff": None,
            "label": "Invalid Date",
            "color_tag": "gray",
            "is_delayed": False,
        }

    # Reference current datetime & date
    if current_dt is not None:
        now = current_dt
        today = now.date()
    elif current_date_str and isinstance(current_date_str, str):
        try:
            today = datetime.strptime(current_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            today = date.today()
        now = datetime.combine(today, datetime.now().time())
    else:
        now = datetime.now()
        today = now.date()

    diff_days = (due - today).days

    due_formatted = due.strftime("%b %d, %Y") if due.year != today.year else due.strftime("%b %d")

    if diff_days < 0:
        return {
            "status": "OVERDUE",
            "days_diff": diff_days,
            "label": f"Overdue: {due_formatted}",
            "color_tag": "red",
            "is_delayed": True,
        }
    elif diff_days == 0:
        # Check if reminder time has already passed today
        is_passed = False
        if reminder_time_str and str(reminder_time_str).strip():
            rem_str = str(reminder_time_str).strip()
            rem_time = None
            for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
                try:
                    rem_time = datetime.strptime(rem_str, fmt).time()
                    break
                except ValueError:
                    pass
            if rem_time is not None:
                if (rem_time.hour, rem_time.minute) <= (now.hour, now.minute):
                    is_passed = True

        if is_passed:
            return {
                "status": "OVERDUE",
                "days_diff": 0,
                "label": f"Delayed: {due_formatted}",
                "color_tag": "gray",
                "is_delayed": True,
            }
        else:
            return {
                "status": "DUE_TODAY",
                "days_diff": 0,
                "label": f"Due: {due_formatted}",
                "color_tag": "amber",
                "is_delayed": False,
            }
    else:
        return {
            "status": "UPCOMING",
            "days_diff": diff_days,
            "label": f"Due: {due_formatted}",
            "color_tag": "blue",
            "is_delayed": False,
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


def calculate_pomodoro_stage(
    completed_sprints: int,
    current_mode: str = "work",
    set_size: int = 4,
    total_target_sprints: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Computes the next stage, sprint number, and cycle state for the Pomodoro workflow.

    :param completed_sprints: Non-negative integer count of completed sprints.
    :param current_mode: Current stage ('work', 'short_break', or 'long_break').
    :param set_size: Positive integer representing sprints per full set (default 4).
    :param total_target_sprints: Optional total target sprints for multi-set tasks (e.g. 8 for 4 hours).
    :return: Dictionary containing:
             - 'next_mode': 'work', 'short_break', or 'long_break'
             - 'next_sprint': Target sprint index (1 to set_size or total_target_sprints)
             - 'is_set_completed': Boolean indicating if a full set was just concluded
             - 'stage_title': Human-readable stage name
    :raises TypeError: If inputs have invalid types.
    :raises ValueError: If numbers are negative, set_size <= 0, or current_mode is invalid.
    """
    if not isinstance(completed_sprints, int) or isinstance(completed_sprints, bool):
        raise TypeError("completed_sprints must be an integer.")
    if not isinstance(set_size, int) or isinstance(set_size, bool):
        raise TypeError("set_size must be an integer.")
    if total_target_sprints is not None:
        if not isinstance(total_target_sprints, int) or isinstance(total_target_sprints, bool):
            raise TypeError("total_target_sprints must be an integer.")
        if total_target_sprints <= 0:
            raise ValueError("total_target_sprints must be greater than zero.")
    if completed_sprints < 0:
        raise ValueError("completed_sprints cannot be negative.")
    if set_size <= 0:
        raise ValueError("set_size must be greater than zero.")
    if current_mode not in ("work", "short_break", "long_break"):
        raise ValueError("current_mode must be 'work', 'short_break', or 'long_break'.")

    if current_mode == "work":
        new_completed = completed_sprints + 1
        is_set_completed = (new_completed % set_size == 0)
        if is_set_completed:
            if total_target_sprints is not None and new_completed < total_target_sprints:
                next_sprint = new_completed + 1
            else:
                next_sprint = 1
            return {
                "next_mode": "long_break",
                "next_sprint": next_sprint,
                "is_set_completed": True,
                "stage_title": "Long Break",
            }
        else:
            if total_target_sprints is not None and new_completed < total_target_sprints:
                next_sprint = new_completed + 1
            else:
                next_sprint = ((new_completed % set_size) + 1)
            return {
                "next_mode": "short_break",
                "next_sprint": next_sprint,
                "is_set_completed": False,
                "stage_title": "Short Break",
            }
    elif current_mode == "short_break":
        if total_target_sprints is not None:
            next_sprint = min(completed_sprints + 1, total_target_sprints)
        else:
            next_sprint = (completed_sprints % set_size) + 1
        return {
            "next_mode": "work",
            "next_sprint": next_sprint,
            "is_set_completed": False,
            "stage_title": f"Sprint {next_sprint}",
        }
    else:  # long_break
        if total_target_sprints is not None and completed_sprints < total_target_sprints:
            next_sprint = completed_sprints + 1
        else:
            next_sprint = 1
        return {
            "next_mode": "work",
            "next_sprint": next_sprint,
            "is_set_completed": False,
            "stage_title": f"Sprint {next_sprint}",
        }



def calculate_pomodoro_stats(
    sessions: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Computes aggregate metrics from a collection of Pomodoro session records.

    :param sessions: List of session dictionaries, each containing 'duration_minutes' and 'session_type'.
    :return: Dictionary containing:
             - 'total_sprints': Total count of completed work sprint sessions
             - 'total_focus_minutes': Total minutes spent in focus work
             - 'total_break_minutes': Total minutes spent in short or long breaks
             - 'average_sprint_minutes': Average focus sprint duration in minutes (rounded to 1 decimal)
    :raises TypeError: If sessions is provided but is not a list.
    """
    if sessions is None:
        return {
            "total_sprints": 0,
            "total_focus_minutes": 0,
            "total_break_minutes": 0,
            "average_sprint_minutes": 0.0,
        }
    if not isinstance(sessions, list):
        raise TypeError("Sessions must be a list of dictionaries.")

    total_sprints = 0
    total_focus_minutes = 0
    total_break_minutes = 0

    for s in sessions:
        if not isinstance(s, dict):
            continue
        duration = int(s.get("duration_minutes") or 0)
        stype = s.get("session_type", "work")

        if stype == "work":
            total_sprints += 1
            total_focus_minutes += duration
        elif stype in ("short_break", "long_break"):
            total_break_minutes += duration

    avg_sprint = round(total_focus_minutes / total_sprints, 1) if total_sprints > 0 else 0.0

    return {
        "total_sprints": total_sprints,
        "total_focus_minutes": total_focus_minutes,
        "total_break_minutes": total_break_minutes,
        "average_sprint_minutes": avg_sprint,
    }


def calculate_focus_quadrant_distribution(
    sessions: Optional[List[Dict[str, Any]]],
    tasks: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Computes total focus sprints and focus minutes categorized across Eisenhower quadrants.
    Associates each work session to its task's quadrant.

    :param sessions: List of pomodoro session dictionaries containing 'task_id', 'duration_minutes', 'session_type'.
    :param tasks: List of task dictionaries containing 'id' and 'quadrant'.
    :return: Dictionary containing:
             - 'quadrants': Mapping of 'Q1_DO', 'Q2_SCHEDULE', etc. to {'sprints_count': int, 'focus_minutes': int, 'percentage': float}
             - 'total_focus_minutes': Total focus minutes across all quadrants
             - 'total_sprints': Total focus sprint count
             - 'proactive_ratio': Percentage of focus time spent in high-value quadrants (Q1 + Q2)
    :raises TypeError: If sessions or tasks are invalid types.
    """
    if sessions is None:
        sessions = []
    if tasks is None:
        tasks = []
    if not isinstance(sessions, list):
        raise TypeError("Sessions must be a list of dictionaries.")
    if not isinstance(tasks, list):
        raise TypeError("Tasks must be a list of dictionaries.")

    task_quad_map = {}
    for t in tasks:
        if isinstance(t, dict) and "id" in t and "quadrant" in t:
            task_quad_map[t["id"]] = t["quadrant"]

    dist = {
        "Q1_DO": {"sprints_count": 0, "focus_minutes": 0},
        "Q2_SCHEDULE": {"sprints_count": 0, "focus_minutes": 0},
        "Q3_DELEGATE": {"sprints_count": 0, "focus_minutes": 0},
        "Q4_ELIMINATE": {"sprints_count": 0, "focus_minutes": 0},
    }

    total_focus_minutes = 0
    total_sprints = 0

    for s in sessions:
        if not isinstance(s, dict):
            continue
        if s.get("session_type") != "work":
            continue
        task_id = s.get("task_id")
        duration = int(s.get("duration_minutes") or 0)
        quad = task_quad_map.get(task_id, "Q1_DO")
        if quad not in dist:
            quad = "Q1_DO"

        dist[quad]["sprints_count"] += 1
        dist[quad]["focus_minutes"] += duration
        total_focus_minutes += duration
        total_sprints += 1

    # Compute percentages
    result_quads = {}
    for q, data in dist.items():
        mins = data["focus_minutes"]
        pct = round((mins / total_focus_minutes) * 100.0, 1) if total_focus_minutes > 0 else 0.0
        result_quads[q] = {
            "sprints_count": data["sprints_count"],
            "focus_minutes": mins,
            "percentage": pct,
        }

    q1_q2_mins = dist["Q1_DO"]["focus_minutes"] + dist["Q2_SCHEDULE"]["focus_minutes"]
    proactive_ratio = round((q1_q2_mins / total_focus_minutes) * 100.0, 1) if total_focus_minutes > 0 else 0.0

    return {
        "quadrants": result_quads,
        "total_focus_minutes": total_focus_minutes,
        "total_sprints": total_sprints,
        "proactive_ratio": proactive_ratio,
    }


def format_focus_duration(minutes: int) -> str:
    """
    Formats an integer minute count into a concise human-readable duration string.
    Example: 0 -> '0m', 45 -> '45m', 60 -> '1h', 130 -> '2h 10m'.

    :param minutes: Non-negative integer minute count.
    :return: Formatted duration string.
    :raises TypeError: If minutes is not an integer or is a boolean.
    :raises ValueError: If minutes is negative.
    """
    if not isinstance(minutes, int) or isinstance(minutes, bool):
        raise TypeError("Minutes must be an integer.")
    if minutes < 0:
        raise ValueError("Minutes cannot be negative.")
    if minutes == 0:
        return "0m"
    hours = minutes // 60
    rem = minutes % 60
    if hours > 0 and rem > 0:
        return f"{hours}h {rem}m"
    elif hours > 0:
        return f"{hours}h"
    return f"{rem}m"


def calculate_recommended_sprints(duration_minutes: int) -> int:
    """
    Computes recommended Pomodoro sprints for a given task duration in minutes.
    Accounts for 25m work + 5m short break, and 15m long break every 4 sprints
    (1 full cycle = 4 sprints = 130 minutes).

    :param duration_minutes: Non-negative integer duration in minutes.
    :return: Integer count of recommended focus sprints.
    :raises TypeError: If duration_minutes is not an integer or is a boolean.
    :raises ValueError: If duration_minutes is negative.
    """
    if not isinstance(duration_minutes, int) or isinstance(duration_minutes, bool):
        raise TypeError("duration_minutes must be an integer.")
    if duration_minutes < 0:
        raise ValueError("duration_minutes cannot be negative.")
    if duration_minutes == 0:
        return 0

    # 1 full cycle of 4 sprints = 3x30m + 1x40m (with 15m long break) = 130 min
    cycles = duration_minutes // 130
    rem = duration_minutes % 130
    extra_sprints = round(rem / 30)
    return max(1, cycles * 4 + extra_sprints)


def get_task_notifications(
    tasks: Optional[List[Dict[str, Any]]],
    current_date_str: Optional[str] = None,
    current_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Categorizes tasks into notification buckets based on their due date:
    - overdue: due_date < current_date OR due today with passed reminder_time (sorted oldest first)
    - today: due_date == current_date (and not yet passed)
    - tomorrow: due_date == current_date + 1 day
    - upcoming: due_date is within 2 to 3 days (current_date + 2 <= due_date <= current_date + 3)

    Only active / pending (non-completed) tasks with valid due_dates are considered.

    :param tasks: List of task dictionaries.
    :param current_date_str: Optional reference date in 'YYYY-MM-DD' format (defaults to today).
    :param current_dt: Optional reference datetime for exact timestamp evaluation.
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

    # Determine reference date and datetime
    now = current_dt if current_dt is not None else datetime.now()
    if current_date_str and isinstance(current_date_str, str):
        try:
            today = datetime.strptime(current_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            today = now.date()
        if current_dt is None:
            now = datetime.combine(today, datetime.now().time())
    else:
        today = now.date()

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

        # Check if task is delayed (either past due date or due today with passed reminder_time)
        delayed = is_task_delayed(task, current_dt=now, current_date_str=current_date_str)
        task_item["is_delayed"] = delayed

        if delayed:
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


def validate_schedule_time(
    due_date: Union[date, str, None],
    reminder_time: Optional[str] = None,
    current_dt: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validates whether a scheduled due date and reminder time are valid and not in the past.
    Returns (is_valid, error_message).
    - If no due date is provided, returns (True, None) (unscheduled task is valid).
    - If due date is in the past (< today), returns (False, "Selected date is in the past. Please choose today or a future date.").
    - If due date is today and reminder_time is provided, checks if reminder time has already passed.
      If it has passed, returns (False, f"Reminder time ({reminder_time}) has already passed today! Please select a future time.").
    - Otherwise returns (True, None).
    """
    if not due_date:
        return True, None

    now = current_dt if current_dt is not None else datetime.now()
    today = now.date()

    if isinstance(due_date, str):
        try:
            d = datetime.strptime(due_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            return False, "Invalid date format. Expected YYYY-MM-DD."
    elif isinstance(due_date, date):
        d = due_date
    else:
        return False, "Invalid date type."

    if d < today:
        return False, "Selected date is in the past. Please choose today or a future date."

    if d == today and reminder_time and str(reminder_time).strip():
        rem_str = str(reminder_time).strip()
        rem_time = None
        for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
            try:
                rem_time = datetime.strptime(rem_str, fmt).time()
                break
            except ValueError:
                pass

        if rem_time is None:
            return False, "Invalid reminder time format."

        # Compare hours and minutes against current time
        if (rem_time.hour, rem_time.minute) <= (now.hour, now.minute):
            return False, f"Reminder time ({rem_str}) has already passed today! Please select a future time."

    return True, None


def calculate_drop_dead_time(
    deadline_time_str: str,
    duration_minutes: int,
    deadline_date: Union[date, str, None] = None,
    reference_dt: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Calculates the 'Point of No Return' (Drop-Dead Start Time) for a task given its deadline time
    and estimated duration needed to complete the work.

    :param deadline_time_str: Deadline time string (e.g. '11:00 PM', '23:00').
    :param duration_minutes: Non-negative integer duration in minutes (e.g. 120).
    :param deadline_date: Target deadline date as date or 'YYYY-MM-DD' string (defaults to reference date).
    :param reference_dt: Optional reference datetime (defaults to datetime.now()).
    :return: Dict containing drop dead details, or None if invalid inputs or duration <= 0.
    :raises TypeError: If duration_minutes is not an integer.
    """
    if not isinstance(duration_minutes, int) or isinstance(duration_minutes, bool):
        raise TypeError("duration_minutes must be an integer.")

    if duration_minutes <= 0 or not deadline_time_str or not str(deadline_time_str).strip():
        return None

    now = reference_dt if reference_dt is not None else datetime.now()

    # Determine deadline date
    if deadline_date is None:
        target_date = now.date()
    elif isinstance(deadline_date, str):
        try:
            target_date = datetime.strptime(deadline_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    elif isinstance(deadline_date, date):
        target_date = deadline_date
    else:
        return None

    # Parse deadline time
    rem_str = str(deadline_time_str).strip()
    rem_time = None
    for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
        try:
            rem_time = datetime.strptime(rem_str, fmt).time()
            break
        except ValueError:
            pass

    if rem_time is None:
        return None

    deadline_dt = datetime.combine(target_date, rem_time)
    drop_dead_dt = deadline_dt - timedelta(minutes=duration_minutes)
    drop_dead_time_str = drop_dead_dt.strftime("%I:%M %p")

    # Format human-friendly duration text (e.g. 30m, 1h, 1h 30m, 2h)
    if duration_minutes < 60:
        duration_text = f"{duration_minutes}m"
    elif duration_minutes % 60 == 0:
        duration_text = f"{duration_minutes // 60}h"
    else:
        duration_text = f"{duration_minutes // 60}h {duration_minutes % 60}m"

    sprints = calculate_recommended_sprints(duration_minutes)
    mins_to_start = (drop_dead_dt - now).total_seconds() / 60.0
    mins_to_deadline = (deadline_dt - now).total_seconds() / 60.0

    return {
        "drop_dead_time_str": drop_dead_time_str,
        "drop_dead_dt": drop_dead_dt,
        "deadline_dt": deadline_dt,
        "duration_text": duration_text,
        "pomodoro_sprints": sprints,
        "mins_to_start": mins_to_start,
        "mins_to_deadline": mins_to_deadline,
    }


if __name__ == "__main__":
    main()

