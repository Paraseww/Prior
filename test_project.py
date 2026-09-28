"""
test_project.py
Comprehensive pytest unit test suite for Prior (CS50P Final Project).
Tests all required custom functions defined in project.py.
"""

import pytest

from project import (
    calculate_matrix_stats,
    determine_quadrant,
    filter_tasks,
    format_due_status,
)


# ============================================================================
# 1. Tests for determine_quadrant()
# ============================================================================

def test_determine_quadrant_valid_cases():
    """Verify correct Eisenhower quadrant classification for all 4 boolean combinations."""
    # Urgent & Important -> Quadrant 1 (Do First)
    assert determine_quadrant(True, True) == "Q1_DO"

    # Not Urgent & Important -> Quadrant 2 (Schedule)
    assert determine_quadrant(False, True) == "Q2_SCHEDULE"

    # Urgent & Not Important -> Quadrant 3 (Delegate)
    assert determine_quadrant(True, False) == "Q3_DELEGATE"

    # Not Urgent & Not Important -> Quadrant 4 (Eliminate)
    assert determine_quadrant(False, False) == "Q4_ELIMINATE"


def test_determine_quadrant_type_errors():
    """Verify TypeError is raised when non-boolean arguments are passed."""
    with pytest.raises(TypeError):
        determine_quadrant("True", True)  # type: ignore

    with pytest.raises(TypeError):
        determine_quadrant(1, 0)  # type: ignore

    with pytest.raises(TypeError):
        determine_quadrant(None, False)  # type: ignore


# ============================================================================
# 2. Tests for filter_tasks()
# ============================================================================

def test_filter_tasks_empty():
    """Verify filtering empty task lists returns empty lists safely."""
    assert filter_tasks([]) == []
    assert filter_tasks(None) == []


def test_filter_tasks_by_quadrant():
    """Verify filtering tasks by specific quadrant and 'ALL'."""
    sample_tasks = [
        {"id": 1, "title": "Finish CS50P", "description": "Write final tests", "quadrant": "Q1_DO", "is_completed": 0},
        {"id": 2, "title": "Exercise", "description": "Gym workout", "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 3, "title": "Reply email", "description": "Client follow-up", "quadrant": "Q3_DELEGATE", "is_completed": 0},
        {"id": 4, "title": "Browse memes", "description": "Social media", "quadrant": "Q4_ELIMINATE", "is_completed": 1},
    ]

    # Filter by Q1_DO
    q1_results = filter_tasks(sample_tasks, quadrant_filter="Q1_DO")
    assert len(q1_results) == 1
    assert q1_results[0]["title"] == "Finish CS50P"

    # Filter by Q2_SCHEDULE
    q2_results = filter_tasks(sample_tasks, quadrant_filter="Q2_SCHEDULE")
    assert len(q2_results) == 1
    assert q2_results[0]["title"] == "Exercise"

    # Filter with ALL
    all_results = filter_tasks(sample_tasks, quadrant_filter="ALL")
    assert len(all_results) == 4


def test_filter_tasks_by_search_query():
    """Verify case-insensitive search across task title and description."""
    sample_tasks = [
        {"id": 1, "title": "Python project", "description": "CS50P assignment", "quadrant": "Q1_DO", "is_completed": 0},
        {"id": 2, "title": "Grocery shopping", "description": "Buy fresh fruits and milk", "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 3, "title": "Team sync", "description": "Discuss project deliverables", "quadrant": "Q3_DELEGATE", "is_completed": 0},
    ]

    # Search in title (case-insensitive)
    results = filter_tasks(sample_tasks, search_query="python")
    assert len(results) == 1
    assert results[0]["id"] == 1

    # Search in description (case-insensitive matching multiple)
    results = filter_tasks(sample_tasks, search_query="project")
    assert len(results) == 2
    assert {r["id"] for r in results} == {1, 3}

    # Search query with no match
    results = filter_tasks(sample_tasks, search_query="nonexistent query")
    assert len(results) == 0


def test_filter_tasks_completed_toggle():
    """Verify hiding completed tasks."""
    sample_tasks = [
        {"id": 1, "title": "Task 1", "description": "", "quadrant": "Q1_DO", "is_completed": 0},
        {"id": 2, "title": "Task 2", "description": "", "quadrant": "Q1_DO", "is_completed": 1},
    ]

    # Show completed = True
    assert len(filter_tasks(sample_tasks, show_completed=True)) == 2

    # Show completed = False
    active_tasks = filter_tasks(sample_tasks, show_completed=False)
    assert len(active_tasks) == 1
    assert active_tasks[0]["id"] == 1


# ============================================================================
# 3. Tests for calculate_matrix_stats()
# ============================================================================

def test_calculate_matrix_stats_empty():
    """Verify stats on empty task list return safe zeroed metrics."""
    stats = calculate_matrix_stats([])
    assert stats["total_tasks"] == 0
    assert stats["completed_tasks"] == 0
    assert stats["pending_tasks"] == 0
    assert stats["completion_rate"] == 0.0
    assert stats["focus_score"] == 0.0
    assert stats["quadrant_counts"] == {"Q1_DO": 0, "Q2_SCHEDULE": 0, "Q3_DELEGATE": 0, "Q4_ELIMINATE": 0}


def test_calculate_matrix_stats_normal_mix():
    """Verify metrics calculation for a mixed set of completed and pending tasks."""
    sample_tasks = [
        {"id": 1, "title": "T1", "quadrant": "Q1_DO", "is_completed": 0},
        {"id": 2, "title": "T2", "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 3, "title": "T3", "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 4, "title": "T4", "quadrant": "Q3_DELEGATE", "is_completed": 0},
        {"id": 5, "title": "T5", "quadrant": "Q1_DO", "is_completed": 1},
    ]

    stats = calculate_matrix_stats(sample_tasks)
    assert stats["total_tasks"] == 5
    assert stats["completed_tasks"] == 1
    assert stats["pending_tasks"] == 4
    assert stats["completion_rate"] == 20.0
    assert stats["quadrant_counts"]["Q1_DO"] == 1
    assert stats["quadrant_counts"]["Q2_SCHEDULE"] == 2
    assert stats["quadrant_counts"]["Q3_DELEGATE"] == 1
    assert stats["quadrant_counts"]["Q4_ELIMINATE"] == 0
    # Focus score = 2 (Q2) / 4 (pending) = 50.0%
    assert stats["focus_score"] == 50.0


def test_calculate_matrix_stats_all_completed():
    """Verify stats when all tasks are completed (no pending tasks)."""
    sample_tasks = [
        {"id": 1, "title": "T1", "quadrant": "Q1_DO", "is_completed": 1},
        {"id": 2, "title": "T2", "quadrant": "Q2_SCHEDULE", "is_completed": 1},
    ]

    stats = calculate_matrix_stats(sample_tasks)
    assert stats["total_tasks"] == 2
    assert stats["completed_tasks"] == 2
    assert stats["pending_tasks"] == 0
    assert stats["completion_rate"] == 100.0
    assert stats["focus_score"] == 0.0


# ============================================================================
# 4. Tests for format_due_status()
# ============================================================================

def test_format_due_status_no_date_or_invalid():
    """Verify handling of missing, empty, or invalid date strings."""
    assert format_due_status(None)["status"] == "NO_DUE_DATE"
    assert format_due_status("")["status"] == "NO_DUE_DATE"
    assert format_due_status("   ")["status"] == "NO_DUE_DATE"
    assert format_due_status("invalid-date")["status"] == "INVALID_DATE"
    assert format_due_status("2026-13-45")["status"] == "INVALID_DATE"


def test_format_due_status_comparisons():
    """Verify overdue, due today, tomorrow, and future date formatting against a fixed reference date."""
    ref_date = "2026-10-15"

    # Overdue by 3 days
    res_overdue_3 = format_due_status("2026-10-12", current_date_str=ref_date)
    assert res_overdue_3["status"] == "OVERDUE"
    assert res_overdue_3["days_diff"] == -3
    assert res_overdue_3["label"] == "Overdue by 3 days"
    assert res_overdue_3["color_tag"] == "red"

    # Overdue by 1 day (singular text)
    res_overdue_1 = format_due_status("2026-10-14", current_date_str=ref_date)
    assert res_overdue_1["status"] == "OVERDUE"
    assert res_overdue_1["days_diff"] == -1
    assert res_overdue_1["label"] == "Overdue by 1 day"

    # Due Today
    res_today = format_due_status("2026-10-15", current_date_str=ref_date)
    assert res_today["status"] == "DUE_TODAY"
    assert res_today["days_diff"] == 0
    assert res_today["label"] == "Due Today"
    assert res_today["color_tag"] == "amber"

    # Due Tomorrow
    res_tomorrow = format_due_status("2026-10-16", current_date_str=ref_date)
    assert res_tomorrow["status"] == "UPCOMING"
    assert res_tomorrow["days_diff"] == 1
    assert res_tomorrow["label"] == "Due Tomorrow"
    assert res_tomorrow["color_tag"] == "blue"

    # Future date (5 days ahead)
    res_future = format_due_status("2026-10-20", current_date_str=ref_date)
    assert res_future["status"] == "UPCOMING"
    assert res_future["days_diff"] == 5
    assert res_future["label"] == "In 5 days"
    assert res_future["color_tag"] == "blue"
