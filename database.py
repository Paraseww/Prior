"""
database.py
Local SQLite persistence layer for Prior desktop application.
Handles user profile settings and task CRUD operations with offline support.
"""

from datetime import datetime, timedelta
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

# Default database filename
DEFAULT_DB_FILE = "prior.db"


def get_default_db_path() -> str:
    """Returns the default absolute path for the SQLite database."""
    base_dir = Path(__file__).resolve().parent
    return str(base_dir / DEFAULT_DB_FILE)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Creates and returns a SQLite database connection with row factory enabled.
    """
    path = db_path if db_path is not None else get_default_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initializes database tables and default profile configuration.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Profile table for user preference and onboarding state
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL DEFAULT 'User',
            theme TEXT NOT NULL DEFAULT 'light',
            startup_enabled INTEGER NOT NULL DEFAULT 0,
            onboarding_completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    # Tasks table for Eisenhower matrix organization
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            quadrant TEXT NOT NULL DEFAULT 'Q1_DO',
            due_date TEXT,
            reminder_time TEXT,
            is_completed INTEGER NOT NULL DEFAULT 0,
            position INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        """
    )

    # Performance indices
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_quadrant ON tasks(quadrant)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(is_completed)"
    )

    # Pomodoro sessions table for focus tracking and analytics
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pomodoro_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            duration_minutes INTEGER NOT NULL,
            session_type TEXT NOT NULL DEFAULT 'work',
            completed_at TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pomodoro_completed_at ON pomodoro_sessions(completed_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pomodoro_task_id ON pomodoro_sessions(task_id)"
    )

    # Optional column migrations
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN reminder_time TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN estimated_duration INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE profile ADD COLUMN zoom_scale REAL NOT NULL DEFAULT 1.0")
    except sqlite3.OperationalError:
        pass

    # Ensure a single default profile record exists
    cursor.execute("SELECT COUNT(*) as count FROM profile WHERE id = 1")
    row = cursor.fetchone()
    if row and row["count"] == 0:
        cursor.execute(
            """
            INSERT INTO profile (id, name, theme, startup_enabled, onboarding_completed, created_at)
            VALUES (1, 'User', 'light', 0, 0, ?)
            """,
            (datetime.now().isoformat(),),
        )
    else:
        # If user is still in uncompleted onboarding, ensure the initial default theme is light
        cursor.execute("SELECT onboarding_completed, theme FROM profile WHERE id = 1")
        p_row = cursor.fetchone()
        if p_row and p_row["onboarding_completed"] == 0 and p_row["theme"] == "dark":
            cursor.execute("UPDATE profile SET theme = 'light' WHERE id = 1")

    conn.commit()
    conn.close()

    try:
        cleanup_orphaned_sessions(db_path)
    except Exception:
        pass


def get_profile(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves user profile settings."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profile WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    if row:
        d = dict(row)
        d.setdefault("zoom_scale", 1.0)
        return d
    return {
        "id": 1,
        "name": "User",
        "theme": "light",
        "startup_enabled": 0,
        "onboarding_completed": 0,
        "zoom_scale": 1.0,
        "created_at": datetime.now().isoformat(),
    }


def update_profile(
    name: Optional[str] = None,
    theme: Optional[str] = None,
    startup_enabled: Optional[int] = None,
    onboarding_completed: Optional[int] = None,
    zoom_scale: Optional[float] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Updates user profile settings."""
    fields = []
    values = []

    if name is not None:
        fields.append("name = ?")
        values.append(name.strip())
    if theme is not None:
        fields.append("theme = ?")
        values.append(theme.strip().lower())
    if startup_enabled is not None:
        fields.append("startup_enabled = ?")
        values.append(1 if startup_enabled else 0)
    if onboarding_completed is not None:
        fields.append("onboarding_completed = ?")
        values.append(1 if onboarding_completed else 0)
    if zoom_scale is not None:
        fields.append("zoom_scale = ?")
        values.append(float(zoom_scale))

    if not fields:
        return False

    query = f"UPDATE profile SET {', '.join(fields)} WHERE id = 1"
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(query, tuple(values))
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected


def add_task(
    title: str,
    description: str = "",
    quadrant: str = "Q1_DO",
    due_date: Optional[str] = None,
    reminder_time: Optional[str] = None,
    estimated_duration: int = 0,
    db_path: Optional[str] = None,
) -> int:
    """
    Inserts a new task and returns its generated integer ID.
    Valid quadrants: 'Q1_DO', 'Q2_SCHEDULE', 'Q3_DELEGATE', 'Q4_ELIMINATE'.
    """
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("Task title cannot be empty.")

    valid_quadrants = {"Q1_DO", "Q2_SCHEDULE", "Q3_DELEGATE", "Q4_ELIMINATE"}
    normalized_quadrant = quadrant.upper() if quadrant else "Q1_DO"
    if normalized_quadrant not in valid_quadrants:
        normalized_quadrant = "Q1_DO"

    created_at = datetime.now().isoformat()
    duration_val = int(estimated_duration or 0)

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tasks (title, description, quadrant, due_date, reminder_time, estimated_duration, is_completed, position, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, NULL)
        """,
        (clean_title, description.strip(), normalized_quadrant, due_date, reminder_time, duration_val, created_at),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return int(task_id)


def get_all_tasks(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all tasks sorted by position order and creation date (newest first)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY position ASC, id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_task_by_id(task_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single task by its ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


_UNSET: Any = object()


def update_task(
    task_id: int,
    title: Any = _UNSET,
    description: Any = _UNSET,
    quadrant: Any = _UNSET,
    due_date: Any = _UNSET,
    reminder_time: Any = _UNSET,
    estimated_duration: Any = _UNSET,
    is_completed: Any = _UNSET,
    position: Any = _UNSET,
    db_path: Optional[str] = None,
) -> bool:
    """Updates specific fields of an existing task."""
    fields = []
    values = []

    if title is not _UNSET:
        clean_title = title.strip() if title else ""
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
        fields.append("title = ?")
        values.append(clean_title)

    if description is not _UNSET:
        fields.append("description = ?")
        values.append(description.strip() if description else "")

    if quadrant is not _UNSET:
        valid_quadrants = {"Q1_DO", "Q2_SCHEDULE", "Q3_DELEGATE", "Q4_ELIMINATE"}
        norm_quadrant = quadrant.upper() if quadrant else "Q1_DO"
        if norm_quadrant in valid_quadrants:
            fields.append("quadrant = ?")
            values.append(norm_quadrant)

    if due_date is not _UNSET:
        fields.append("due_date = ?")
        values.append(due_date.strip() if due_date and str(due_date).strip() else None)

    if reminder_time is not _UNSET:
        fields.append("reminder_time = ?")
        values.append(reminder_time.strip() if reminder_time and str(reminder_time).strip() else None)

    if estimated_duration is not _UNSET:
        fields.append("estimated_duration = ?")
        values.append(int(estimated_duration) if estimated_duration is not None else 0)

    comp_time = None
    if is_completed is not _UNSET:
        val = 1 if is_completed else 0
        fields.append("is_completed = ?")
        values.append(val)
        if val == 1:
            fields.append("completed_at = ?")
            comp_time = datetime.now().isoformat()
            values.append(comp_time)
        else:
            fields.append("completed_at = ?")
            values.append(None)

    if position is not _UNSET:
        fields.append("position = ?")
        values.append(int(position) if position is not None else 0)

    if not fields:
        return False

    values.append(task_id)
    query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(query, tuple(values))
    affected = cursor.rowcount > 0
    if is_completed is not _UNSET:
        if is_completed:
            _ensure_completed_task_sessions(cursor, task_id, comp_time)
        else:
            cursor.execute("DELETE FROM pomodoro_sessions WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()
    return affected


def _ensure_completed_task_sessions(cursor: sqlite3.Cursor, task_id: int, completed_at: Optional[str] = None) -> None:
    """
    Ensures that when a task is marked as completed directly (e.g. via checkbox, Done,
    or Mark Task Completed without using the pomodoro timer panel), its focus sprint
    and duration data are logged into pomodoro_sessions for analytics tracking.
    Guarantees no duplicate sessions are recorded beyond the task's required sprint target.
    Prunes any excess sessions if the task was already completed or repeated.
    """
    cursor.execute("SELECT estimated_duration, quadrant FROM tasks WHERE id = ?", (task_id,))
    t_row = cursor.fetchone()
    if not t_row:
        return

    est_duration = max(0, int(t_row["estimated_duration"] or 0))
    if est_duration > 0:
        cycles = est_duration // 130
        rem = est_duration % 130
        extra_sprints = round(rem / 30)
        target_sprints = max(1, cycles * 4 + extra_sprints)
        total_mins = est_duration
    else:
        target_sprints = 1
        total_mins = 25

    cursor.execute(
        "SELECT id, duration_minutes FROM pomodoro_sessions WHERE task_id = ? AND session_type = 'work' ORDER BY id ASC",
        (task_id,),
    )
    existing_sessions = cursor.fetchall()
    current_count = len(existing_sessions)

    if est_duration > 0:
        # If duplicate / excess sessions exist beyond target_sprints, prune the extras
        if current_count > target_sprints:
            excess_ids = [row["id"] for row in existing_sessions[target_sprints:]]
            placeholders = ",".join("?" for _ in excess_ids)
            cursor.execute(f"DELETE FROM pomodoro_sessions WHERE id IN ({placeholders})", tuple(excess_ids))
            current_count = target_sprints

        # If sessions are missing, add only the remaining needed sprints
        if current_count < target_sprints:
            base_dur = total_mins // target_sprints
            rem_dur = total_mins % target_sprints
            session_time = completed_at or datetime.now().isoformat()
            for i in range(current_count, target_sprints):
                dur = base_dur + (1 if i < rem_dur else 0)
                cursor.execute(
                    """
                    INSERT INTO pomodoro_sessions (task_id, duration_minutes, session_type, completed_at)
                    VALUES (?, ?, 'work', ?)
                    """,
                    (task_id, dur, session_time),
                )
    else:
        # If no estimate was set and no sessions exist yet, record 1 default sprint
        if current_count == 0:
            session_time = completed_at or datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO pomodoro_sessions (task_id, duration_minutes, session_type, completed_at)
                VALUES (?, ?, 'work', ?)
                """,
                (task_id, total_mins, session_time),
            )


def reorder_tasks(ordered_task_ids: List[int], db_path: Optional[str] = None) -> bool:
    """
    Updates the position order for a list of task IDs.
    The first task in ordered_task_ids gets position 0, the next gets 1, etc.
    """
    if not ordered_task_ids:
        return False
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for index, task_id in enumerate(ordered_task_ids):
        cursor.execute("UPDATE tasks SET position = ? WHERE id = ?", (index, task_id))
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected


def toggle_task_completion(task_id: int, db_path: Optional[str] = None) -> bool:
    """Toggles task completion state between 0 (pending) and 1 (completed)."""
    task = get_task_by_id(task_id, db_path=db_path)
    if not task:
        return False

    new_state = 0 if task["is_completed"] == 1 else 1
    completed_at = datetime.now().isoformat() if new_state == 1 else None

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET is_completed = ?, completed_at = ? WHERE id = ?",
        (new_state, completed_at, task_id),
    )
    affected = cursor.rowcount > 0
    if new_state == 1:
        # Task marked as completed: ensure focus session data is logged for analytics
        _ensure_completed_task_sessions(cursor, task_id, completed_at)
    elif new_state == 0:
        # Task unmarked as incomplete: clear focus session data for this task
        cursor.execute("DELETE FROM pomodoro_sessions WHERE task_id = ?", (task_id,))

    conn.commit()
    conn.close()
    return affected


def delete_task(task_id: int, db_path: Optional[str] = None) -> bool:
    """Deletes a task by ID and removes its associated pomodoro focus sessions."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE id = ?", (task_id,))
    if cursor.fetchone()[0] == 0:
        conn.close()
        return False

    # Cascade delete pomodoro sessions linked to this task
    cursor.execute("DELETE FROM pomodoro_sessions WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return True


def clear_completed_tasks(db_path: Optional[str] = None) -> int:
    """Deletes all completed tasks and their pomodoro sessions, returning number of deleted tasks."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM pomodoro_sessions WHERE task_id IN (SELECT id FROM tasks WHERE is_completed = 1)"
    )
    cursor.execute("DELETE FROM tasks WHERE is_completed = 1")
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count


def cleanup_orphaned_sessions(db_path: Optional[str] = None) -> int:
    """Removes pomodoro sessions whose parent task no longer exists or is NULL."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM pomodoro_sessions WHERE task_id NOT IN (SELECT id FROM tasks) OR task_id IS NULL"
    )
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count


def clear_all_pomodoro_sessions(db_path: Optional[str] = None) -> int:
    """Deletes all pomodoro session records and returns the number of deleted rows."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pomodoro_sessions")
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count


# ============================================================================
# Pomodoro Focus Sessions Persistence & Queries
# ============================================================================

def log_pomodoro_session(
    task_id: Optional[int],
    duration_minutes: int,
    session_type: str = "work",
    completed_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """
    Logs a completed Pomodoro session (focus sprint or break) to SQLite.

    :param task_id: Optional ID of the task associated with the focus session.
    :param duration_minutes: Duration of the session in minutes (positive integer).
    :param session_type: Type of session ('work', 'short_break', or 'long_break').
    :param completed_at: ISO formatted completion timestamp (defaults to now).
    :param db_path: Optional custom database path.
    :return: The integer primary key ID of the inserted session row.
    :raises ValueError: If duration_minutes <= 0 or session_type is invalid.
    """
    if not isinstance(duration_minutes, int) or isinstance(duration_minutes, bool) or duration_minutes <= 0:
        raise ValueError("duration_minutes must be a positive integer.")
    if session_type not in ("work", "short_break", "long_break"):
        raise ValueError("session_type must be 'work', 'short_break', or 'long_break'.")

    timestamp = completed_at if completed_at is not None else datetime.now().isoformat()

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Prevent duplicating work sessions beyond task's target sprint count
    if task_id is not None and session_type == "work":
        cursor.execute("SELECT estimated_duration FROM tasks WHERE id = ?", (task_id,))
        t_row = cursor.fetchone()
        if t_row:
            est_dur = max(0, int(t_row["estimated_duration"] or 0))
            if est_dur > 0:
                cycles = est_dur // 130
                rem = est_dur % 130
                extra_sprints = round(rem / 30)
                target_sprints = max(1, cycles * 4 + extra_sprints)

                cursor.execute(
                    "SELECT COUNT(*) FROM pomodoro_sessions WHERE task_id = ? AND session_type = 'work'",
                    (task_id,),
                )
                count = cursor.fetchone()[0]
                if count >= target_sprints:
                    cursor.execute(
                        "SELECT id FROM pomodoro_sessions WHERE task_id = ? AND session_type = 'work' ORDER BY id DESC LIMIT 1",
                        (task_id,),
                    )
                    existing_row = cursor.fetchone()
                    conn.close()
                    return existing_row[0] if existing_row else 0

    cursor.execute(
        """
        INSERT INTO pomodoro_sessions (task_id, duration_minutes, session_type, completed_at)
        VALUES (?, ?, ?, ?)
        """,
        (task_id, duration_minutes, session_type, timestamp),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_pomodoro_sessions(
    task_id: Optional[int] = None,
    session_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves logged Pomodoro sessions with optional filtering.

    :param task_id: Optional task ID filter.
    :param session_type: Optional filter ('work', 'short_break', 'long_break').
    :param start_date: Optional start date 'YYYY-MM-DD' filter.
    :param end_date: Optional end date 'YYYY-MM-DD' filter.
    :param db_path: Optional database path.
    :return: List of session dictionaries.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM pomodoro_sessions WHERE 1=1"
    params: List[Any] = []

    if task_id is not None:
        query += " AND task_id = ?"
        params.append(task_id)

    if session_type is not None:
        query += " AND session_type = ?"
        params.append(session_type)

    if start_date is not None:
        query += " AND completed_at >= ?"
        params.append(f"{start_date}T00:00:00")

    if end_date is not None:
        query += " AND completed_at <= ?"
        params.append(f"{end_date}T23:59:59")

    query += " ORDER BY completed_at DESC"

    cursor.execute(query, tuple(params))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_daily_pomodoro_stats(
    target_date: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculates total sprints and focus minutes for a given date.

    :param target_date: Target date 'YYYY-MM-DD' (defaults to today).
    :param db_path: Optional database path.
    :return: Dictionary containing 'date', 'sprints_count', and 'total_focus_minutes'.
    """
    day_str = target_date if target_date is not None else datetime.now().strftime("%Y-%m-%d")

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) as sprints_count, COALESCE(SUM(duration_minutes), 0) as total_focus_minutes
        FROM pomodoro_sessions
        WHERE session_type = 'work' AND completed_at LIKE ?
        """,
        (f"{day_str}%",),
    )
    row = cursor.fetchone()
    stats = {
        "date": day_str,
        "sprints_count": row["sprints_count"] if row else 0,
        "total_focus_minutes": row["total_focus_minutes"] if row else 0,
        "total_minutes": row["total_focus_minutes"] if row else 0,
    }
    conn.close()
    return stats


def get_all_time_pomodoro_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculates all-time lifetime focus statistics.

    :param db_path: Optional database path.
    :return: Dictionary containing 'total_sprints', 'total_focus_minutes', and 'active_days_count'.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            COUNT(*) as total_sprints,
            COALESCE(SUM(duration_minutes), 0) as total_focus_minutes,
            COUNT(DISTINCT SUBSTR(completed_at, 1, 10)) as active_days_count
        FROM pomodoro_sessions
        WHERE session_type = 'work'
        """
    )
    row = cursor.fetchone()
    summary = {
        "total_sprints": row["total_sprints"] if row else 0,
        "total_focus_minutes": row["total_focus_minutes"] if row else 0,
        "active_days_count": row["active_days_count"] if row else 0,
    }
    conn.close()
    return summary


def get_weekly_pomodoro_breakdown(
    reference_date: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Computes daily focus minutes and sprint counts for the 7-day period ending on reference_date.

    :param reference_date: ISO date string 'YYYY-MM-DD' (defaults to today).
    :param db_path: Optional database path.
    :return: List of 7 dictionaries ordered oldest to newest, each with:
             'date', 'day_name' (e.g. 'Mon'), 'sprints_count', 'focus_minutes', 'is_today'
    """
    ref_dt = datetime.strptime(reference_date.strip(), "%Y-%m-%d").date() if reference_date else datetime.now().date()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Generate 7 days from (ref_dt - 6 days) up to ref_dt
    days_list = [ref_dt - timedelta(days=i) for i in range(6, -1, -1)]

    start_str = days_list[0].strftime("%Y-%m-%d")
    end_str = days_list[-1].strftime("%Y-%m-%d")

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            SUBSTR(completed_at, 1, 10) as day_date,
            COUNT(*) as sprints_count,
            COALESCE(SUM(duration_minutes), 0) as focus_minutes
        FROM pomodoro_sessions
        WHERE session_type = 'work'
          AND completed_at >= ?
          AND completed_at <= ?
        GROUP BY SUBSTR(completed_at, 1, 10)
        """,
        (f"{start_str}T00:00:00", f"{end_str}T23:59:59"),
    )
    data_by_date = {row["day_date"]: dict(row) for row in cursor.fetchall()}
    conn.close()

    result = []
    for d in days_list:
        d_str = d.strftime("%Y-%m-%d")
        row = data_by_date.get(d_str, {})
        result.append({
            "date": d_str,
            "day_name": d.strftime("%a"),
            "sprints_count": int(row.get("sprints_count", 0)),
            "focus_minutes": int(row.get("focus_minutes", 0)),
            "is_today": (d_str == today_str),
        })
    return result


def get_pomodoro_quadrant_distribution(
    db_path: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Calculates total focus sprints and minutes categorized by Eisenhower quadrant.

    :param db_path: Optional database path.
    :return: Dictionary keyed by quadrant code ('Q1_DO', 'Q2_SCHEDULE', etc.)
             mapping to {'sprints_count': int, 'focus_minutes': int}.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            t.quadrant,
            COUNT(p.id) as sprints_count,
            COALESCE(SUM(p.duration_minutes), 0) as focus_minutes
        FROM pomodoro_sessions p
        JOIN tasks t ON p.task_id = t.id
        WHERE p.session_type = 'work'
        GROUP BY t.quadrant
        """
    )
    rows = cursor.fetchall()
    conn.close()

    dist = {
        "Q1_DO": {"sprints_count": 0, "focus_minutes": 0},
        "Q2_SCHEDULE": {"sprints_count": 0, "focus_minutes": 0},
        "Q3_DELEGATE": {"sprints_count": 0, "focus_minutes": 0},
        "Q4_ELIMINATE": {"sprints_count": 0, "focus_minutes": 0},
    }
    for row in rows:
        q = row["quadrant"]
        if q in dist:
            dist[q] = {
                "sprints_count": int(row["sprints_count"]),
                "focus_minutes": int(row["focus_minutes"]),
            }
    return dist


def get_top_focused_tasks(
    limit: int = 5,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves the most focused tasks ranked by total pomodoro time and sprints.

    :param limit: Maximum number of tasks to return (default 5).
    :param db_path: Optional database path.
    :return: List of dictionaries with task details and focus statistics.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            t.id,
            t.title,
            t.quadrant,
            t.is_completed,
            COUNT(p.id) as sprints_count,
            COALESCE(SUM(p.duration_minutes), 0) as focus_minutes
        FROM pomodoro_sessions p
        JOIN tasks t ON p.task_id = t.id
        WHERE p.session_type = 'work'
        GROUP BY t.id
        ORDER BY focus_minutes DESC, sprints_count DESC
        LIMIT ?
        """,
        (max(1, limit),),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
