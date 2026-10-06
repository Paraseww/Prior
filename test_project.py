"""
test_project.py
Comprehensive pytest unit test suite for Prior (CS50P Final Project).
Tests all required custom functions defined in project.py.
"""

from datetime import date, datetime
import pytest

from project import (
    calculate_drop_dead_time,
    calculate_matrix_stats,
    determine_quadrant,
    filter_tasks,
    format_due_status,
    format_timer_display,
    calculate_pomodoro_stage,
    calculate_pomodoro_stats,
    get_task_notifications,
    validate_schedule_time,
)
import database


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
    assert res_overdue_3["label"] == "Overdue: Oct 12"
    assert res_overdue_3["color_tag"] == "red"

    # Overdue by 1 day
    res_overdue_1 = format_due_status("2026-10-14", current_date_str=ref_date)
    assert res_overdue_1["status"] == "OVERDUE"
    assert res_overdue_1["days_diff"] == -1
    assert res_overdue_1["label"] == "Overdue: Oct 14"

    # Due Today
    res_today = format_due_status("2026-10-15", current_date_str=ref_date)
    assert res_today["status"] == "DUE_TODAY"
    assert res_today["days_diff"] == 0
    assert res_today["label"] == "Due: Oct 15"
    assert res_today["color_tag"] == "amber"

    # Due Tomorrow
    res_tomorrow = format_due_status("2026-10-16", current_date_str=ref_date)
    assert res_tomorrow["status"] == "UPCOMING"
    assert res_tomorrow["days_diff"] == 1
    assert res_tomorrow["label"] == "Due: Oct 16"
    assert res_tomorrow["color_tag"] == "blue"

    # Future date (5 days ahead)
    res_future = format_due_status("2026-10-20", current_date_str=ref_date)
    assert res_future["status"] == "UPCOMING"
    assert res_future["days_diff"] == 5
    assert res_future["label"] == "Due: Oct 20"
    assert res_future["color_tag"] == "blue"

    # Future date in different year
    res_next_year = format_due_status("2027-01-10", current_date_str=ref_date)
    assert res_next_year["status"] == "UPCOMING"
    assert res_next_year["label"] == "Due: Jan 10, 2027"


# ============================================================================
# 5. Tests for format_timer_display()
# ============================================================================

def test_format_timer_display_valid():
    """Verify seconds to MM:SS formatting for Pomodoro intervals."""
    assert format_timer_display(1500) == "25:00"   # 25-minute work block
    assert format_timer_display(300) == "05:00"    # 5-minute short break
    assert format_timer_display(900) == "15:00"    # 15-minute long break
    assert format_timer_display(65) == "01:05"     # 1 minute 5 seconds
    assert format_timer_display(0) == "00:00"      # Complete / zero


def test_format_timer_display_invalid():
    """Verify TypeError and ValueError handling on invalid timer inputs."""
    with pytest.raises(TypeError):
        format_timer_display("1500")  # type: ignore

    with pytest.raises(TypeError):
        format_timer_display(True)  # type: ignore

    with pytest.raises(ValueError):
        format_timer_display(-10)


def test_calculate_pomodoro_stage_progression():
    """Verify 4-sprint cycle transitions, short breaks, and long breaks."""
    # 1. First sprint finished -> goes to Short Break (stage 2 prep)
    s1 = calculate_pomodoro_stage(completed_sprints=0, current_mode="work", set_size=4)
    assert s1["next_mode"] == "short_break"
    assert s1["next_sprint"] == 2
    assert s1["is_set_completed"] is False
    assert s1["stage_title"] == "Short Break"

    # 2. Short break finished -> moves to Sprint 2
    b1 = calculate_pomodoro_stage(completed_sprints=1, current_mode="short_break", set_size=4)
    assert b1["next_mode"] == "work"
    assert b1["next_sprint"] == 2
    assert b1["is_set_completed"] is False
    assert b1["stage_title"] == "Sprint 2"

    # 3. Third sprint finished -> goes to Short Break (stage 4 prep)
    s3 = calculate_pomodoro_stage(completed_sprints=2, current_mode="work", set_size=4)
    assert s3["next_mode"] == "short_break"
    assert s3["next_sprint"] == 4
    assert s3["is_set_completed"] is False

    # 4. Fourth sprint finished -> completes set, triggers Long Break
    s4 = calculate_pomodoro_stage(completed_sprints=3, current_mode="work", set_size=4)
    assert s4["next_mode"] == "long_break"
    assert s4["next_sprint"] == 1
    assert s4["is_set_completed"] is True
    assert s4["stage_title"] == "Long Break"

    # 5. Long break finished -> resets set and returns to Sprint 1
    lb = calculate_pomodoro_stage(completed_sprints=4, current_mode="long_break", set_size=4)
    assert lb["next_mode"] == "work"
    assert lb["next_sprint"] == 1
    assert lb["is_set_completed"] is False
    assert lb["stage_title"] == "Sprint 1"


def test_calculate_pomodoro_stage_invalid():
    """Verify error handling on invalid types and negative arguments."""
    with pytest.raises(TypeError):
        calculate_pomodoro_stage("0", "work")  # type: ignore

    with pytest.raises(TypeError):
        calculate_pomodoro_stage(True, "work")  # type: ignore

    with pytest.raises(TypeError):
        calculate_pomodoro_stage(1, "work", set_size="4")  # type: ignore

    with pytest.raises(ValueError):
        calculate_pomodoro_stage(-1, "work")

    with pytest.raises(ValueError):
        calculate_pomodoro_stage(1, "work", set_size=0)

    with pytest.raises(ValueError):
        calculate_pomodoro_stage(1, "invalid_mode")


def test_calculate_pomodoro_stats_valid():
    """Verify aggregation of sprints, focus minutes, and break minutes."""
    sample_sessions = [
        {"duration_minutes": 25, "session_type": "work"},
        {"duration_minutes": 5, "session_type": "short_break"},
        {"duration_minutes": 25, "session_type": "work"},
        {"duration_minutes": 15, "session_type": "long_break"},
        {"duration_minutes": 50, "session_type": "work"},
    ]
    stats = calculate_pomodoro_stats(sample_sessions)
    assert stats["total_sprints"] == 3
    assert stats["total_focus_minutes"] == 100
    assert stats["total_break_minutes"] == 20
    assert stats["average_sprint_minutes"] == round(100 / 3, 1)


def test_calculate_pomodoro_stats_empty_and_none():
    """Verify safe fallback on empty or None session lists."""
    assert calculate_pomodoro_stats([]) == {
        "total_sprints": 0,
        "total_focus_minutes": 0,
        "total_break_minutes": 0,
        "average_sprint_minutes": 0.0,
    }
    assert calculate_pomodoro_stats(None) == {
        "total_sprints": 0,
        "total_focus_minutes": 0,
        "total_break_minutes": 0,
        "average_sprint_minutes": 0.0,
    }


def test_calculate_pomodoro_stats_invalid():
    """Verify TypeError raised when non-list argument is passed."""
    with pytest.raises(TypeError):
        calculate_pomodoro_stats("not a list")  # type: ignore
    with pytest.raises(TypeError):
        calculate_pomodoro_stats(123)  # type: ignore


def test_database_pomodoro_persistence(tmp_path):
    """Verify SQLite persistence of Pomodoro sessions and daily/all-time queries."""
    db_file = str(tmp_path / "test_pomodoro.db")
    database.init_db(db_file)

    # 1. Log sessions
    s1_id = database.log_pomodoro_session(
        task_id=None,
        duration_minutes=25,
        session_type="work",
        completed_at="2026-10-06T10:00:00",
        db_path=db_file,
    )
    assert s1_id > 0

    s2_id = database.log_pomodoro_session(
        task_id=42,
        duration_minutes=25,
        session_type="work",
        completed_at="2026-10-06T11:00:00",
        db_path=db_file,
    )
    assert s2_id > s1_id

    # Log a break
    b1_id = database.log_pomodoro_session(
        task_id=None,
        duration_minutes=5,
        session_type="short_break",
        completed_at="2026-10-06T10:25:00",
        db_path=db_file,
    )
    assert b1_id > 0

    # 2. Query sessions
    all_sessions = database.get_pomodoro_sessions(db_path=db_file)
    assert len(all_sessions) == 3

    task_sessions = database.get_pomodoro_sessions(task_id=42, db_path=db_file)
    assert len(task_sessions) == 1
    assert task_sessions[0]["task_id"] == 42

    # 3. Daily stats
    daily_stats = database.get_daily_pomodoro_stats("2026-10-06", db_path=db_file)
    assert daily_stats["sprints_count"] == 2
    assert daily_stats["total_focus_minutes"] == 50

    # 4. All-time summary
    summary = database.get_all_time_pomodoro_summary(db_path=db_file)
    assert summary["total_sprints"] == 2
    assert summary["total_focus_minutes"] == 50
    assert summary["active_days_count"] == 1

    # 5. Validation error tests
    with pytest.raises(ValueError):
        database.log_pomodoro_session(None, 0, "work", db_path=db_file)
    with pytest.raises(ValueError):
        database.log_pomodoro_session(None, 25, "invalid_type", db_path=db_file)


# ============================================================================
# 6. Tests for get_task_notifications()
# ============================================================================

def test_get_task_notifications_empty():
    """Verify notification categorization on empty/None task list."""
    res_empty = get_task_notifications([])
    assert res_empty["total_count"] == 0
    assert res_empty["overdue_count"] == 0
    assert res_empty["today_count"] == 0
    assert res_empty["tomorrow_count"] == 0
    assert res_empty["upcoming_count"] == 0
    assert res_empty["overdue"] == []
    assert res_empty["today"] == []
    assert res_empty["tomorrow"] == []
    assert res_empty["upcoming"] == []

    res_none = get_task_notifications(None)
    assert res_none["total_count"] == 0


def test_get_task_notifications_completed_and_invalid_ignored():
    """Verify completed tasks and tasks with missing/invalid due dates are excluded."""
    ref_date = "2026-10-15"
    sample_tasks = [
        {"id": 1, "title": "Completed overdue", "due_date": "2026-10-10", "is_completed": 1},
        {"id": 2, "title": "No date task", "due_date": None, "is_completed": 0},
        {"id": 3, "title": "Empty date task", "due_date": "", "is_completed": 0},
        {"id": 4, "title": "Invalid date task", "due_date": "not-a-date", "is_completed": 0},
    ]

    res = get_task_notifications(sample_tasks, current_date_str=ref_date)
    assert res["total_count"] == 0
    assert res["overdue"] == []
    assert res["today"] == []
    assert res["tomorrow"] == []
    assert res["upcoming"] == []


def test_get_task_notifications_categorization_and_sorting():
    """Verify correct classification into overdue, today, tomorrow, and upcoming buckets with sorting."""
    ref_date = "2026-10-15"
    sample_tasks = [
        {"id": 1, "title": "Severely Overdue", "due_date": "2026-10-10", "is_completed": 0},  # -5 days
        {"id": 2, "title": "Yesterday Overdue", "due_date": "2026-10-14", "is_completed": 0},  # -1 day
        {"id": 3, "title": "Due Today Task", "due_date": "2026-10-15", "is_completed": 0},    # 0 days
        {"id": 4, "title": "Due Tomorrow Task", "due_date": "2026-10-16", "is_completed": 0}, # 1 day
        {"id": 5, "title": "Due in 2 Days", "due_date": "2026-10-17", "is_completed": 0},     # 2 days
        {"id": 6, "title": "Due in 3 Days", "due_date": "2026-10-18", "is_completed": 0},     # 3 days
        {"id": 7, "title": "Far Future Task", "due_date": "2026-10-25", "is_completed": 0},   # 10 days (excluded from 3d window)
    ]

    res = get_task_notifications(sample_tasks, current_date_str=ref_date)

    assert res["total_count"] == 6  # 2 overdue + 1 today + 1 tomorrow + 2 upcoming
    assert res["overdue_count"] == 2
    assert res["today_count"] == 1
    assert res["tomorrow_count"] == 1
    assert res["upcoming_count"] == 2

    # Overdue should be sorted oldest first (id: 1 then id: 2)
    assert [t["id"] for t in res["overdue"]] == [1, 2]
    assert res["overdue"][0]["days_diff"] == -5
    assert res["overdue"][1]["days_diff"] == -1

    # Today
    assert res["today"][0]["id"] == 3
    assert res["today"][0]["days_diff"] == 0

    # Tomorrow
    assert res["tomorrow"][0]["id"] == 4
    assert res["tomorrow"][0]["days_diff"] == 1

    # Upcoming (2-3 days) should be sorted soonest first (id: 5 then id: 6)
    assert [t["id"] for t in res["upcoming"]] == [5, 6]
    assert res["upcoming"][0]["days_diff"] == 2
    assert res["upcoming"][1]["days_diff"] == 3


# ============================================================================
# 7. Tests for validate_schedule_time()
# ============================================================================

def test_validate_schedule_time_scenarios():
    """Verify schedule date and reminder time validation across past, present, and future scenarios."""
    ref_now = datetime(2026, 10, 3, 19, 22)  # 7:22 PM on Oct 03, 2026

    # 1. Setting a reminder for earlier today (e.g. 6:00 AM when current time is 7:22 PM) -> MUST FAIL
    is_valid, err = validate_schedule_time("2026-10-03", "6:00 AM", current_dt=ref_now)
    assert is_valid is False
    assert "has already passed today" in err

    # With leading zero "06:00 AM"
    is_valid, err = validate_schedule_time(date(2026, 10, 3), "06:00 AM", current_dt=ref_now)
    assert is_valid is False
    assert "has already passed today" in err

    # 2. Setting a reminder for future time today (e.g. 8:00 PM) -> MUST PASS
    is_valid, err = validate_schedule_time("2026-10-03", "8:00 PM", current_dt=ref_now)
    assert is_valid is True
    assert err is None

    # 3. Setting a reminder for tomorrow (e.g. 6:00 AM tomorrow) -> MUST PASS
    is_valid, err = validate_schedule_time("2026-10-04", "6:00 AM", current_dt=ref_now)
    assert is_valid is True
    assert err is None

    # 4. Setting a date in the past (yesterday) -> MUST FAIL
    is_valid, err = validate_schedule_time("2026-10-02", "6:00 AM", current_dt=ref_now)
    assert is_valid is False
    assert "in the past" in err

    # 5. Setting task for today without a reminder time -> MUST PASS
    is_valid, err = validate_schedule_time("2026-10-03", None, current_dt=ref_now)
    assert is_valid is True
    assert err is None

    # 6. Unscheduled task (no date, no reminder) -> MUST PASS
    is_valid, err = validate_schedule_time(None, None, current_dt=ref_now)
    assert is_valid is True
    assert err is None


# ============================================================================
# 8. Tests for calculate_drop_dead_time()
# ============================================================================

def test_calculate_drop_dead_time_basic():
    """Verify drop dead start time calculation for standard scenarios."""
    ref_now = datetime(2026, 10, 4, 20, 0)  # 8:00 PM

    # 2 hours runway for 11:00 PM deadline -> Drop-dead start must be 09:00 PM
    res = calculate_drop_dead_time("11:00 PM", 120, "2026-10-04", reference_dt=ref_now)
    assert res is not None
    assert res["drop_dead_time_str"] == "09:00 PM"
    assert res["duration_text"] == "2h"
    assert res["pomodoro_sprints"] == 5
    assert res["mins_to_start"] == 60.0
    assert res["mins_to_deadline"] == 180.0

    # 30 mins runway for 10:00 AM deadline
    res30 = calculate_drop_dead_time("10:00 AM", 30, "2026-10-04", reference_dt=ref_now)
    assert res30 is not None
    assert res30["drop_dead_time_str"] == "09:30 AM"
    assert res30["duration_text"] == "30m"
    assert res30["pomodoro_sprints"] == 1

    # Custom duration: 75 mins (1 hr 15 mins) for 11:00 PM deadline -> Drop dead 09:45 PM
    res75 = calculate_drop_dead_time("11:00 PM", 75, "2026-10-04", reference_dt=ref_now)
    assert res75 is not None
    assert res75["drop_dead_time_str"] == "09:45 PM"
    assert res75["duration_text"] == "1h 15m"
    assert res75["pomodoro_sprints"] == 3


def test_calculate_drop_dead_time_midnight_crossover():
    """Verify cross-midnight drop dead time calculation (e.g., deadline 1:00 AM)."""
    # Deadline at 1:00 AM on Oct 5th with 2 hours runway -> Drop dead is 11:00 PM on Oct 4th
    res = calculate_drop_dead_time("1:00 AM", 120, "2026-10-05")
    assert res is not None
    assert res["drop_dead_time_str"] == "11:00 PM"
    assert res["drop_dead_dt"] == datetime(2026, 10, 4, 23, 0)


def test_calculate_drop_dead_time_invalid_inputs():
    """Verify handling of invalid or non-positive durations and malformed inputs."""
    assert calculate_drop_dead_time("11:00 PM", 0) is None
    assert calculate_drop_dead_time("11:00 PM", -30) is None
    assert calculate_drop_dead_time("", 60) is None
    assert calculate_drop_dead_time("invalid_time", 60) is None
    assert calculate_drop_dead_time("11:00 PM", 60, deadline_date="invalid_date") is None

    with pytest.raises(TypeError):
        calculate_drop_dead_time("11:00 PM", "60")  # type: ignore

    with pytest.raises(TypeError):
        calculate_drop_dead_time("11:00 PM", True)  # type: ignore


def test_calculate_drop_dead_time_user_persona_milestones():
    """Verify precision milestones for user persona: Bio paper due 11:00 PM, 2 hours duration."""
    # At 8:45 PM (15 mins before drop-dead start)
    ref_845pm = datetime(2026, 10, 4, 20, 45)
    res_845 = calculate_drop_dead_time("11:00 PM", 120, "2026-10-04", reference_dt=ref_845pm)
    assert res_845 is not None
    assert res_845["drop_dead_time_str"] == "09:00 PM"
    assert res_845["mins_to_start"] == 15.0
    assert 0 < res_845["mins_to_start"] <= 15  # Triggers 15-min warning

    # At 9:00 PM (Drop-Dead Start Time / Point of No Return)
    ref_900pm = datetime(2026, 10, 4, 21, 0)
    res_900 = calculate_drop_dead_time("11:00 PM", 120, "2026-10-04", reference_dt=ref_900pm)
    assert res_900 is not None
    assert res_900["mins_to_start"] == 0.0
    assert res_900["mins_to_deadline"] == 120.0  # Triggers Point of No Return

    # At 11:00 PM (Critical Deadline)
    ref_1100pm = datetime(2026, 10, 4, 23, 0)
    res_1100 = calculate_drop_dead_time("11:00 PM", 120, "2026-10-04", reference_dt=ref_1100pm)
    assert res_1100 is not None
    assert res_1100["mins_to_deadline"] == 0.0  # Triggers Critical Deadline


