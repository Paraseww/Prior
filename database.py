"""
database.py
Local SQLite persistence layer for Prior desktop application.
Handles user profile settings and task CRUD operations with offline support.
"""

from datetime import datetime
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
            theme TEXT NOT NULL DEFAULT 'dark',
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

    # Optional column migrations
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN reminder_time TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Ensure a single default profile record exists
    cursor.execute("SELECT COUNT(*) as count FROM profile WHERE id = 1")
    row = cursor.fetchone()
    if row and row["count"] == 0:
        cursor.execute(
            """
            INSERT INTO profile (id, name, theme, startup_enabled, onboarding_completed, created_at)
            VALUES (1, 'User', 'dark', 0, 0, ?)
            """,
            (datetime.now().isoformat(),),
        )

    conn.commit()
    conn.close()


def get_profile(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves user profile settings."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profile WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return {
        "id": 1,
        "name": "User",
        "theme": "dark",
        "startup_enabled": 0,
        "onboarding_completed": 0,
        "created_at": datetime.now().isoformat(),
    }


def update_profile(
    name: Optional[str] = None,
    theme: Optional[str] = None,
    startup_enabled: Optional[int] = None,
    onboarding_completed: Optional[int] = None,
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

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tasks (title, description, quadrant, due_date, reminder_time, is_completed, position, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, 0, 0, ?, NULL)
        """,
        (clean_title, description.strip(), normalized_quadrant, due_date, reminder_time, created_at),
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

    if is_completed is not _UNSET:
        val = 1 if is_completed else 0
        fields.append("is_completed = ?")
        values.append(val)
        if val == 1:
            fields.append("completed_at = ?")
            values.append(datetime.now().isoformat())
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
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected


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
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected


def delete_task(task_id: int, db_path: Optional[str] = None) -> bool:
    """Deletes a task by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE id = ?", (task_id,))
    if cursor.fetchone()[0] == 0:
        conn.close()
        return False

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return True


def clear_completed_tasks(db_path: Optional[str] = None) -> int:
    """Deletes all completed tasks and returns the number of deleted rows."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE is_completed = 1")
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count
