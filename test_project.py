"""
test_project.py
Comprehensive pytest unit test suite for Prior (CS50P Final Project).
Tests all required custom functions defined in project.py.
"""

from datetime import date, datetime
import pytest

from project import (
    calculate_drop_dead_time,
    calculate_focus_quadrant_distribution,
    calculate_matrix_stats,
    calculate_pomodoro_stage,
    calculate_pomodoro_stats,
    calculate_recommended_sprints,
    determine_quadrant,
    filter_tasks,
    format_due_status,
    format_focus_duration,
    format_timer_display,
    get_task_notifications,
    is_task_delayed,
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


def test_calculate_matrix_stats_overdue_q2_excluded_from_focus_score():
    """Verify that overdue tasks in Q2_SCHEDULE do not inflate the focus score."""
    ref_date = "2026-10-15"
    sample_tasks = [
        {"id": 1, "title": "T1 (Q1 pending)", "quadrant": "Q1_DO", "is_completed": 0},
        # Overdue Q2 task (scheduled for 2026-10-10, reference is 2026-10-15 -> delayed/overdue)
        {"id": 2, "title": "T2 (Q2 overdue)", "quadrant": "Q2_SCHEDULE", "due_date": "2026-10-10", "is_completed": 0},
        # Due today Q2 task (on schedule)
        {"id": 3, "title": "T3 (Q2 today)", "quadrant": "Q2_SCHEDULE", "due_date": "2026-10-15", "is_completed": 0},
        # Upcoming Q2 task (on schedule)
        {"id": 4, "title": "T4 (Q2 upcoming)", "quadrant": "Q2_SCHEDULE", "due_date": "2026-10-20", "is_completed": 0},
    ]

    stats = calculate_matrix_stats(sample_tasks, current_date_str=ref_date)
    assert stats["total_tasks"] == 4
    assert stats["completed_tasks"] == 0
    assert stats["pending_tasks"] == 4
    # All 3 pending Q2 tasks are reflected in quadrant_counts
    assert stats["quadrant_counts"]["Q2_SCHEDULE"] == 3
    # Only the 2 on-schedule tasks (today and future) count towards proactive planning
    assert stats["proactive_q2_tasks"] == 2
    # Focus score = (2 / 4) * 100.0 = 50.0% (instead of 3 / 4 = 75.0%)
    assert stats["focus_score"] == 50.0


def test_calculate_matrix_stats_all_q2_overdue():
    """Verify focus score drops to 0.0% if all pending Q2 tasks are overdue."""
    ref_date = "2026-10-15"
    sample_tasks = [
        {"id": 1, "title": "T1 (Q1)", "quadrant": "Q1_DO", "is_completed": 0},
        {"id": 2, "title": "T2 (Q2 overdue)", "quadrant": "Q2_SCHEDULE", "due_date": "2026-10-01", "is_completed": 0},
    ]

    stats = calculate_matrix_stats(sample_tasks, current_date_str=ref_date)
    assert stats["total_tasks"] == 2
    assert stats["pending_tasks"] == 2
    assert stats["quadrant_counts"]["Q2_SCHEDULE"] == 1
    assert stats["proactive_q2_tasks"] == 0
    assert stats["focus_score"] == 0.0


def test_calculate_matrix_stats_pipeline_target_progression():
    """Verify Solution 2 pipeline health scaling against target buffer (25% per task up to 100%)."""
    tasks_1 = [{"id": 1, "quadrant": "Q2_SCHEDULE", "is_completed": 0}]
    assert calculate_matrix_stats(tasks_1)["focus_score"] == 25.0

    tasks_2 = [
        {"id": 1, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 2, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
    ]
    assert calculate_matrix_stats(tasks_2)["focus_score"] == 50.0

    tasks_3 = [
        {"id": 1, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 2, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 3, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
    ]
    assert calculate_matrix_stats(tasks_3)["focus_score"] == 75.0

    tasks_4 = [
        {"id": 1, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 2, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 3, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
        {"id": 4, "quadrant": "Q2_SCHEDULE", "is_completed": 0},
    ]
    assert calculate_matrix_stats(tasks_4)["focus_score"] == 100.0

    # 5 tasks is capped at 100.0%
    tasks_5 = tasks_4 + [{"id": 5, "quadrant": "Q2_SCHEDULE", "is_completed": 0}]
    assert calculate_matrix_stats(tasks_5)["focus_score"] == 100.0

    # Custom target parameter
    assert calculate_matrix_stats(tasks_1, target_proactive_tasks=2)["focus_score"] == 50.0
    assert calculate_matrix_stats(tasks_2, target_proactive_tasks=2)["focus_score"] == 100.0


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


def test_format_due_status_passed_reminder_time():
    """Verify that a task due today whose reminder time has passed is marked OVERDUE / delayed."""
    ref_dt = datetime(2026, 10, 7, 15, 0)  # 3:00 PM on Oct 7, 2026
    # 6:00 AM passed today -> OVERDUE / delayed
    res_passed = format_due_status("2026-10-07", reminder_time_str="06:00 AM", current_dt=ref_dt)
    assert res_passed["status"] == "OVERDUE"
    assert res_passed["is_delayed"] is True
    assert res_passed["color_tag"] == "gray"

    # 6:00 PM is later today -> DUE_TODAY / not delayed
    res_future = format_due_status("2026-10-07", reminder_time_str="06:00 PM", current_dt=ref_dt)
    assert res_future["status"] == "DUE_TODAY"
    assert res_future["is_delayed"] is False
    assert res_future["color_tag"] == "amber"


def test_format_due_status_completed():
    """Verify that completed tasks are never marked as delayed or overdue."""
    ref_dt = datetime(2026, 10, 7, 15, 0)
    # Past date but completed -> COMPLETED, not delayed
    res_past = format_due_status("2026-10-06", current_dt=ref_dt, is_completed=True)
    assert res_past["status"] == "COMPLETED"
    assert res_past["is_delayed"] is False
    assert res_past["label"] == "Due: Oct 06"

    # Today with passed time but completed -> COMPLETED, not delayed
    res_today = format_due_status("2026-10-07", reminder_time_str="06:00 AM", current_dt=ref_dt, is_completed=True)
    assert res_today["status"] == "COMPLETED"
    assert res_today["is_delayed"] is False
    assert res_today["label"] == "Due: Oct 07"

    # Future date and completed -> COMPLETED, not delayed
    res_future = format_due_status("2026-10-09", reminder_time_str="06:00 PM", current_dt=ref_dt, is_completed=True)
    assert res_future["status"] == "COMPLETED"
    assert res_future["is_delayed"] is False
    assert res_future["label"] == "Due: Oct 09"


def test_is_task_delayed():
    """Verify is_task_delayed logic for various date/time combinations."""
    ref_dt = datetime(2026, 10, 7, 15, 0)  # 3:00 PM on Oct 7, 2026

    # Past date
    assert is_task_delayed({"due_date": "2026-10-06", "is_completed": 0}, current_dt=ref_dt) is True

    # Completed task is never considered delayed
    assert is_task_delayed({"due_date": "2026-10-06", "is_completed": 1}, current_dt=ref_dt) is False

    # Due today, 6:00 AM (passed)
    assert is_task_delayed({"due_date": "2026-10-07", "reminder_time": "06:00 AM", "is_completed": 0}, current_dt=ref_dt) is True

    # Due today, 6:00 PM (future)
    assert is_task_delayed({"due_date": "2026-10-07", "reminder_time": "06:00 PM", "is_completed": 0}, current_dt=ref_dt) is False

    # Due today, no reminder time
    assert is_task_delayed({"due_date": "2026-10-07", "is_completed": 0}, current_dt=ref_dt) is False

    # Future date
    assert is_task_delayed({"due_date": "2026-10-08", "reminder_time": "06:00 AM", "is_completed": 0}, current_dt=ref_dt) is False


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


def test_calculate_pomodoro_stage_multi_set_target():
    """Verify 8-sprint multi-set cycle transitions (e.g., 4-hour task runway)."""
    # 1. Fourth sprint finished in an 8-sprint session -> triggers Long Break, but next sprint is 5
    s4 = calculate_pomodoro_stage(completed_sprints=3, current_mode="work", set_size=4, total_target_sprints=8)
    assert s4["next_mode"] == "long_break"
    assert s4["next_sprint"] == 5
    assert s4["is_set_completed"] is True

    # 2. Long break finishes -> advances to Sprint 5
    lb4 = calculate_pomodoro_stage(completed_sprints=4, current_mode="long_break", set_size=4, total_target_sprints=8)
    assert lb4["next_mode"] == "work"
    assert lb4["next_sprint"] == 5
    assert lb4["stage_title"] == "Sprint 5"

    # 3. Sprint 5 finishes -> Short Break before Sprint 6
    s5 = calculate_pomodoro_stage(completed_sprints=4, current_mode="work", set_size=4, total_target_sprints=8)
    assert s5["next_mode"] == "short_break"
    assert s5["next_sprint"] == 6

    # 4. Short break finishes -> advances to Sprint 6
    b5 = calculate_pomodoro_stage(completed_sprints=5, current_mode="short_break", set_size=4, total_target_sprints=8)
    assert b5["next_mode"] == "work"
    assert b5["next_sprint"] == 6

    # 5. Sprint 8 finishes -> triggers final Long Break, cycles back to 1
    s8 = calculate_pomodoro_stage(completed_sprints=7, current_mode="work", set_size=4, total_target_sprints=8)
    assert s8["next_mode"] == "long_break"
    assert s8["next_sprint"] == 1
    assert s8["is_set_completed"] is True


def test_calculate_pomodoro_stage_invalid():
    """Verify error handling on invalid types and negative arguments."""
    with pytest.raises(TypeError):
        calculate_pomodoro_stage("0", "work")  # type: ignore

    with pytest.raises(TypeError):
        calculate_pomodoro_stage(True, "work")  # type: ignore

    with pytest.raises(TypeError):
        calculate_pomodoro_stage(1, "work", set_size="4")  # type: ignore

    with pytest.raises(TypeError):
        calculate_pomodoro_stage(1, "work", total_target_sprints="8")  # type: ignore

    with pytest.raises(ValueError):
        calculate_pomodoro_stage(1, "work", total_target_sprints=0)

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


def test_calculate_recommended_sprints_valid():
    """Verify cycle-aware Pomodoro sprint recommendations across standard durations."""
    # Under 2 hours (<= 120 mins)
    assert calculate_recommended_sprints(30) == 1
    assert calculate_recommended_sprints(60) == 2
    assert calculate_recommended_sprints(75) == 2
    assert calculate_recommended_sprints(90) == 3
    assert calculate_recommended_sprints(120) == 4   # 2 hours

    # Multi-cycle sessions (> 120 mins) taking 130m full cycles into account
    assert calculate_recommended_sprints(180) == 6   # 3 hours: 1 cycle (130m) + 2 sprints (50m)
    assert calculate_recommended_sprints(240) == 8   # 4 hours: 1 cycle (130m) + 4 sprints (110m)
    assert calculate_recommended_sprints(480) == 15  # 8 hours: 3 cycles (390m) + 3 sprints (90m) = 480m exactly

    # Zero duration
    assert calculate_recommended_sprints(0) == 0


def test_calculate_recommended_sprints_invalid():
    """Verify error handling on invalid types and negative durations."""
    with pytest.raises(TypeError):
        calculate_recommended_sprints("60")  # type: ignore
    with pytest.raises(TypeError):
        calculate_recommended_sprints(True)  # type: ignore
    with pytest.raises(ValueError):
        calculate_recommended_sprints(-30)


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
    assert res["pomodoro_sprints"] == 4
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
    assert res75["pomodoro_sprints"] == 2

    # 8 hours runway (480 mins) -> 15 sprints fills exactly 480m with 130m cycles and long breaks
    res480 = calculate_drop_dead_time("11:00 PM", 480, "2026-10-04", reference_dt=ref_now)
    assert res480 is not None
    assert res480["drop_dead_time_str"] == "03:00 PM"
    assert res480["duration_text"] == "8h"
    assert res480["pomodoro_sprints"] == 15


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


# ============================================================================
# 9. Tests for calculate_focus_quadrant_distribution() & Focus Analytics
# ============================================================================

def test_calculate_focus_quadrant_distribution_empty():
    """Verify focus quadrant distribution on empty inputs."""
    res = calculate_focus_quadrant_distribution([], [])
    assert res["total_focus_minutes"] == 0
    assert res["total_sprints"] == 0
    assert res["proactive_ratio"] == 0.0
    for q in ["Q1_DO", "Q2_SCHEDULE", "Q3_DELEGATE", "Q4_ELIMINATE"]:
        assert res["quadrants"][q]["sprints_count"] == 0
        assert res["quadrants"][q]["focus_minutes"] == 0
        assert res["quadrants"][q]["percentage"] == 0.0

    # None inputs
    res_none = calculate_focus_quadrant_distribution(None, None)
    assert res_none["total_sprints"] == 0


def test_calculate_focus_quadrant_distribution_aggregation():
    """Verify quadrant-level aggregation, focus time, and proactive ratio."""
    tasks = [
        {"id": 1, "title": "Math Assignment", "quadrant": "Q1_DO"},
        {"id": 2, "title": "Read Chapter 4", "quadrant": "Q2_SCHEDULE"},
        {"id": 3, "title": "Reply Email", "quadrant": "Q3_DELEGATE"},
    ]
    sessions = [
        {"task_id": 1, "duration_minutes": 25, "session_type": "work"},
        {"task_id": 1, "duration_minutes": 25, "session_type": "work"},
        {"task_id": 2, "duration_minutes": 25, "session_type": "work"},
        {"task_id": 2, "duration_minutes": 25, "session_type": "work"},
        {"task_id": 3, "duration_minutes": 25, "session_type": "work"},
        # Break sessions must be ignored
        {"task_id": 1, "duration_minutes": 5, "session_type": "short_break"},
        {"task_id": 2, "duration_minutes": 15, "session_type": "long_break"},
    ]

    res = calculate_focus_quadrant_distribution(sessions, tasks)
    assert res["total_sprints"] == 5
    assert res["total_focus_minutes"] == 125
    assert res["quadrants"]["Q1_DO"]["sprints_count"] == 2
    assert res["quadrants"]["Q1_DO"]["focus_minutes"] == 50
    assert res["quadrants"]["Q1_DO"]["percentage"] == 40.0

    assert res["quadrants"]["Q2_SCHEDULE"]["sprints_count"] == 2
    assert res["quadrants"]["Q2_SCHEDULE"]["focus_minutes"] == 50
    assert res["quadrants"]["Q2_SCHEDULE"]["percentage"] == 40.0

    assert res["quadrants"]["Q3_DELEGATE"]["sprints_count"] == 1
    assert res["quadrants"]["Q3_DELEGATE"]["focus_minutes"] == 25
    assert res["quadrants"]["Q3_DELEGATE"]["percentage"] == 20.0

    # High-value quadrants (Q1 + Q2) = 40% + 40% = 80.0%
    assert res["proactive_ratio"] == 80.0


def test_calculate_focus_quadrant_distribution_type_errors():
    """Verify TypeError on invalid inputs."""
    with pytest.raises(TypeError):
        calculate_focus_quadrant_distribution("invalid", [])  # type: ignore

    with pytest.raises(TypeError):
        calculate_focus_quadrant_distribution([], "invalid")  # type: ignore


def test_database_pomodoro_analytics_queries(tmp_path):
    """Verify weekly breakdown, quadrant distribution, and top tasks SQLite queries."""
    db_file = str(tmp_path / "test_analytics.db")
    database.init_db(db_file)

    # Create test tasks
    t1_id = database.add_task("Bio Research", "notes", "Q1_DO", db_path=db_file)
    t2_id = database.add_task("History Reading", "notes", "Q2_SCHEDULE", db_path=db_file)

    # Log pomodoro sessions
    database.log_pomodoro_session(t1_id, 25, "work", completed_at="2026-10-06T10:00:00", db_path=db_file)
    database.log_pomodoro_session(t1_id, 25, "work", completed_at="2026-10-06T11:00:00", db_path=db_file)
    database.log_pomodoro_session(t2_id, 25, "work", completed_at="2026-10-05T14:00:00", db_path=db_file)

    # 1. Weekly breakdown (ending on 2026-10-06)
    weekly = database.get_weekly_pomodoro_breakdown(reference_date="2026-10-06", db_path=db_file)
    assert len(weekly) == 7
    # Last item is 2026-10-06 with 2 sprints (50 mins)
    assert weekly[-1]["date"] == "2026-10-06"
    assert weekly[-1]["sprints_count"] == 2
    assert weekly[-1]["focus_minutes"] == 50
    # Second to last item is 2026-10-05 with 1 sprint (25 mins)
    assert weekly[-2]["date"] == "2026-10-05"
    assert weekly[-2]["sprints_count"] == 1
    assert weekly[-2]["focus_minutes"] == 25

    # 2. Quadrant distribution
    q_dist = database.get_pomodoro_quadrant_distribution(db_path=db_file)
    assert q_dist["Q1_DO"]["sprints_count"] == 2
    assert q_dist["Q1_DO"]["focus_minutes"] == 50
    assert q_dist["Q2_SCHEDULE"]["sprints_count"] == 1
    assert q_dist["Q2_SCHEDULE"]["focus_minutes"] == 25
    assert q_dist["Q3_DELEGATE"]["sprints_count"] == 0

    # 3. Top focused tasks leaderboard
    top_tasks = database.get_top_focused_tasks(limit=5, db_path=db_file)
    assert len(top_tasks) == 2
    assert top_tasks[0]["id"] == t1_id
    assert top_tasks[0]["sprints_count"] == 2
    assert top_tasks[0]["focus_minutes"] == 50
    assert top_tasks[1]["id"] == t2_id
    assert top_tasks[1]["sprints_count"] == 1
    assert top_tasks[1]["focus_minutes"] == 25


def test_format_focus_duration():
    """Verify conversion of minutes to readable focus duration string."""
    assert format_focus_duration(0) == "0m"
    assert format_focus_duration(25) == "25m"
    assert format_focus_duration(60) == "1h"
    assert format_focus_duration(75) == "1h 15m"
    assert format_focus_duration(130) == "2h 10m"
    assert format_focus_duration(180) == "3h"

    with pytest.raises(TypeError):
        format_focus_duration("30")  # type: ignore

    with pytest.raises(TypeError):
        format_focus_duration(True)  # type: ignore

    with pytest.raises(ValueError):
        format_focus_duration(-5)


def test_unmarking_task_clears_pomodoro_sessions(tmp_path):
    """Verify that unchecking/unmarking a task clears its pomodoro sessions and analytics data."""
    db_file = str(tmp_path / "test_unmark.db")
    database.init_db(db_file)

    t_id = database.add_task("Test Incomplete", "Desc", "Q1_DO", db_path=db_file)
    database.log_pomodoro_session(t_id, 25, "work", db_path=db_file)
    database.log_pomodoro_session(t_id, 25, "work", db_path=db_file)

    # Mark completed
    database.toggle_task_completion(t_id, db_path=db_file)
    task = database.get_task_by_id(t_id, db_path=db_file)
    assert task["is_completed"] == 1
    assert database.get_daily_pomodoro_stats(db_path=db_file)["sprints_count"] == 2

    # Uncheck / unmark task (new_state == 0)
    database.toggle_task_completion(t_id, db_path=db_file)
    task_after = database.get_task_by_id(t_id, db_path=db_file)
    assert task_after["is_completed"] == 0

    # Sessions must be cleared
    daily = database.get_daily_pomodoro_stats(db_path=db_file)
    assert daily["sprints_count"] == 0
    assert daily["total_focus_minutes"] == 0
    summary = database.get_all_time_pomodoro_summary(db_path=db_file)
    assert summary["total_sprints"] == 0
    assert summary["total_focus_minutes"] == 0

    # Also test update_task with is_completed=0
    database.log_pomodoro_session(t_id, 25, "work", db_path=db_file)
    database.update_task(t_id, is_completed=1, db_path=db_file)
    assert database.get_daily_pomodoro_stats(db_path=db_file)["sprints_count"] == 1

    database.update_task(t_id, is_completed=0, db_path=db_file)
    assert database.get_daily_pomodoro_stats(db_path=db_file)["sprints_count"] == 0


def test_marking_task_completed_directly_populates_analytics_sessions(tmp_path):
    """
    Verify that completing a task directly (via checkbox / Mark Completed without pomodoro timer)
    automatically logs focus sprint and duration data to pomodoro_sessions.
    """
    db_file = str(tmp_path / "test_direct_complete.db")
    database.init_db(db_file)

    # 1. Task in Q1_DO with estimated duration 60 mins (2 sprints)
    t1_id = database.add_task("Bio Study", "Notes", "Q1_DO", estimated_duration=60, db_path=db_file)
    # Complete directly via toggle_task_completion
    database.toggle_task_completion(t1_id, db_path=db_file)

    task1 = database.get_task_by_id(t1_id, db_path=db_file)
    assert task1["is_completed"] == 1

    stats1 = database.get_daily_pomodoro_stats(db_path=db_file)
    assert stats1["sprints_count"] == 2
    assert stats1["total_focus_minutes"] == 50  # 2 sprints * 25m = 50m

    q_dist = database.get_pomodoro_quadrant_distribution(db_path=db_file)
    assert q_dist["Q1_DO"]["sprints_count"] == 2
    assert q_dist["Q1_DO"]["focus_minutes"] == 50

    # 2. Uncheck task -> clears data
    database.toggle_task_completion(t1_id, db_path=db_file)
    stats_cleared = database.get_daily_pomodoro_stats(db_path=db_file)
    assert stats_cleared["sprints_count"] == 0
    assert stats_cleared["total_focus_minutes"] == 0

    # 3. 2-hour task (120m) yields 4 sprints * 25m = 100m (1h 40m)
    t_2h = database.add_task("Chem Lab", "", "Q1_DO", estimated_duration=120, db_path=db_file)
    database.toggle_task_completion(t_2h, db_path=db_file)
    stats_2h = database.get_daily_pomodoro_stats(db_path=db_file)
    assert stats_2h["sprints_count"] == 4
    assert stats_2h["total_focus_minutes"] == 100  # 4 * 25m = 100m (1h 40m)

    # 4. Task with 0 duration defaults to 1 sprint (25m)
    t2_id = database.add_task("Quick Chore", "", "Q1_DO", estimated_duration=0, db_path=db_file)
    database.toggle_task_completion(t2_id, db_path=db_file)
    stats2 = database.get_daily_pomodoro_stats(db_path=db_file)
    assert stats2["sprints_count"] == 5  # 4 from t_2h + 1 from t2_id
    assert stats2["total_focus_minutes"] == 125  # 100 + 25


def test_no_duplicate_sessions_on_repeated_timer_or_mark_completed(tmp_path):
    """
    Verify that completing sprints via timer and then clicking mark as completed / finish
    never duplicates focus data beyond the task's required sprint target.
    """
    db_file = str(tmp_path / "test_no_dupes.db")
    database.init_db(db_file)

    # 2 hours = 4 sprints
    t_id = database.add_task("Bio Chemistry", "", "Q1_DO", estimated_duration=120, db_path=db_file)

    # Simulate user skipping or completing 4 sprints in Pomodoro timer
    for _ in range(4):
        database.log_pomodoro_session(t_id, 25, "work", db_path=db_file)

    # Attempting to log a 5th sprint is capped and does not duplicate
    database.log_pomodoro_session(t_id, 25, "work", db_path=db_file)

    sessions_before = database.get_pomodoro_sessions(task_id=t_id, session_type="work", db_path=db_file)
    assert len(sessions_before) == 4

    # Now click "Congrats, You Did It! Mark Completed & Finish" (update_task or toggle_task_completion)
    database.update_task(t_id, is_completed=1, db_path=db_file)

    sessions_after = database.get_pomodoro_sessions(task_id=t_id, session_type="work", db_path=db_file)
    assert len(sessions_after) == 4

    stats = database.get_daily_pomodoro_stats(db_path=db_file)
    assert stats["sprints_count"] == 4
    # Sprints count is exactly 4, never 8
    assert stats["sprints_count"] == 4


def test_daily_focus_only_counts_scheduled_date_tasks(tmp_path):
    """
    Verify that Today's Focus only counts focus sprints and minutes for tasks scheduled
    for that specific date (e.g. 7th October), and excludes tasks scheduled for other days
    (e.g. 8th October, 9th October).
    """
    db_file = str(tmp_path / "test_date_isolation.db")
    database.init_db(db_file)

    # 1. Task scheduled for Oct 7 (2 hours = 4 sprints)
    t_oct7 = database.add_task(
        "Chem Lab", "", "Q1_DO",
        due_date="2026-10-07",
        estimated_duration=120,
        db_path=db_file,
    )
    database.toggle_task_completion(t_oct7, db_path=db_file)

    # 2. Task scheduled for Oct 8 (2 hours = 4 sprints)
    t_oct8 = database.add_task(
        "Bio Study", "", "Q1_DO",
        due_date="2026-10-08",
        estimated_duration=120,
        db_path=db_file,
    )
    database.toggle_task_completion(t_oct8, db_path=db_file)

    # 3. Task scheduled for Oct 9 (3 hours = 6 sprints)
    t_oct9 = database.add_task(
        "Physics Revision", "", "Q1_DO",
        due_date="2026-10-09",
        estimated_duration=180,
        db_path=db_file,
    )
    database.toggle_task_completion(t_oct9, db_path=db_file)

    # Today's focus for Oct 7 must ONLY count Oct 7 task (4 sprints, 100m)
    stats_oct7 = database.get_daily_pomodoro_stats("2026-10-07", db_path=db_file)
    assert stats_oct7["sprints_count"] == 4
    assert stats_oct7["total_focus_minutes"] == 100

    # Stats for Oct 8 must ONLY count Oct 8 task (4 sprints, 100m)
    stats_oct8 = database.get_daily_pomodoro_stats("2026-10-08", db_path=db_file)
    assert stats_oct8["sprints_count"] == 4
    assert stats_oct8["total_focus_minutes"] == 100

    # Stats for Oct 9 must ONLY count Oct 9 task (6 sprints, 150m)
    stats_oct9 = database.get_daily_pomodoro_stats("2026-10-09", db_path=db_file)
    assert stats_oct9["sprints_count"] == 6
    assert stats_oct9["total_focus_minutes"] == 150

    # Lifetime deep work across all 3 days is 14 sprints (350m = 5h 50m)
    lifetime = database.get_all_time_pomodoro_summary(db_path=db_file)
    assert lifetime["total_sprints"] == 14
    assert lifetime["total_focus_minutes"] == 350
    assert lifetime["active_days_count"] == 3


def test_focus_metrics_strictly_limited_to_red_section_tasks(tmp_path):
    """
    Verify that Deep Work & Pomodoro Focus metrics ONLY collect data for tasks in the red
    section (Q1_DO), and completely ignore tasks in the green (Q2), orange (Q3), and blue (Q4) sections.
    """
    db_file = str(tmp_path / "test_red_only.db")
    database.init_db(db_file)

    # 1. Add and complete a green section task (Q2_SCHEDULE)
    t_green = database.add_task("Doctor Appointment", "", "Q2_SCHEDULE", estimated_duration=120, db_path=db_file)
    database.toggle_task_completion(t_green, db_path=db_file)

    # 2. Add and complete an orange section task (Q3_DELEGATE)
    t_orange = database.add_task("Forward email", "", "Q3_DELEGATE", estimated_duration=60, db_path=db_file)
    database.toggle_task_completion(t_orange, db_path=db_file)

    # 3. Add and complete a blue section task (Q4_ELIMINATE)
    t_blue = database.add_task("Sort old files", "", "Q4_ELIMINATE", estimated_duration=90, db_path=db_file)
    database.toggle_task_completion(t_blue, db_path=db_file)

    # Deep work metrics must be completely 0
    stats = database.get_daily_pomodoro_stats(quadrant="Q1_DO", db_path=db_file)
    assert stats["sprints_count"] == 0
    assert stats["total_focus_minutes"] == 0

    lifetime = database.get_all_time_pomodoro_summary(quadrant="Q1_DO", db_path=db_file)
    assert lifetime["total_sprints"] == 0
    assert lifetime["total_focus_minutes"] == 0

    # Ensure no pomodoro sessions were inserted for non-Q1 tasks
    assert len(database.get_pomodoro_sessions(task_id=t_green, db_path=db_file)) == 0
    assert len(database.get_pomodoro_sessions(task_id=t_orange, db_path=db_file)) == 0
    assert len(database.get_pomodoro_sessions(task_id=t_blue, db_path=db_file)) == 0

    # 4. Now add and complete a red section task (Q1_DO)
    t_red = database.add_task("Math Exam Prep", "", "Q1_DO", estimated_duration=120, db_path=db_file)
    database.toggle_task_completion(t_red, db_path=db_file)

    # Red task data must now be present in Deep Work metrics (4 sprints, 100m)
    stats_red = database.get_daily_pomodoro_stats(quadrant="Q1_DO", db_path=db_file)
    assert stats_red["sprints_count"] == 4
    assert stats_red["total_focus_minutes"] == 100

    lifetime_red = database.get_all_time_pomodoro_summary(quadrant="Q1_DO", db_path=db_file)
    assert lifetime_red["total_sprints"] == 4
    assert lifetime_red["total_focus_minutes"] == 100

    # 5. Moving the red task to green clears its pomodoro sessions
    database.update_task(t_red, quadrant="Q2_SCHEDULE", db_path=db_file)
    stats_after_move = database.get_daily_pomodoro_stats(quadrant="Q1_DO", db_path=db_file)
    assert stats_after_move["sprints_count"] == 0
    assert stats_after_move["total_focus_minutes"] == 0


def test_delete_pomodoro_sessions_for_task(tmp_path):
    """Verify that delete_pomodoro_sessions_for_task deletes only the specified task's sessions."""
    db_file = str(tmp_path / "test_pomodoro_cleanup.db")
    database.init_db(db_file)

    t1 = database.add_task("Task 1", "", "Q1_DO", estimated_duration=60, db_path=db_file)
    t2 = database.add_task("Task 2", "", "Q1_DO", estimated_duration=60, db_path=db_file)

    database.log_pomodoro_session(t1, 25, "work", db_path=db_file)
    database.log_pomodoro_session(t1, 25, "work", db_path=db_file)
    database.log_pomodoro_session(t2, 25, "work", db_path=db_file)

    assert len(database.get_pomodoro_sessions(task_id=t1, db_path=db_file)) == 2
    assert len(database.get_pomodoro_sessions(task_id=t2, db_path=db_file)) == 1

    deleted = database.delete_pomodoro_sessions_for_task(t1, db_path=db_file)
    assert deleted == 2

    assert len(database.get_pomodoro_sessions(task_id=t1, db_path=db_file)) == 0
    assert len(database.get_pomodoro_sessions(task_id=t2, db_path=db_file)) == 1


# ============================================================================
# 16. Tests for Task Archiving and Analytics Preservation
# ============================================================================

def test_filter_tasks_archived():
    """Verify that filter_tasks excludes archived tasks by default and includes them when requested."""
    sample = [
        {"id": 1, "title": "Active Task", "quadrant": "Q1_DO", "is_completed": 0, "is_archived": 0},
        {"id": 2, "title": "Completed Task", "quadrant": "Q1_DO", "is_completed": 1, "is_archived": 0},
        {"id": 3, "title": "Archived Task", "quadrant": "Q1_DO", "is_completed": 1, "is_archived": 1},
    ]

    # Default (include_archived=False) excludes archived task
    res_default = filter_tasks(sample)
    assert len(res_default) == 2
    assert [t["id"] for t in res_default] == [1, 2]

    # Explicit include_archived=True includes all
    res_with_arch = filter_tasks(sample, include_archived=True)
    assert len(res_with_arch) == 3
    assert [t["id"] for t in res_with_arch] == [1, 2, 3]


def test_archive_task_preserves_analytics_and_sessions(tmp_path):
    """
    Verify that archive_task marks the task as archived while preserving the task record
    and its linked pomodoro focus sessions for analytics.
    """
    db_file = str(tmp_path / "test_archive.db")
    database.init_db(db_file)

    task_id = database.add_task("High Priority Work", "", "Q1_DO", estimated_duration=60, db_path=db_file)
    database.log_pomodoro_session(task_id, 25, "work", db_path=db_file)
    database.log_pomodoro_session(task_id, 25, "work", db_path=db_file)
    database.update_task(task_id, is_completed=True, db_path=db_file)

    # Initial state: 1 task, 2 sessions
    t_before = database.get_task_by_id(task_id, db_path=db_file)
    assert t_before is not None
    assert t_before["is_archived"] == 0
    assert len(database.get_pomodoro_sessions(task_id=task_id, db_path=db_file)) == 2

    # Archive the task
    assert database.archive_task(task_id, db_path=db_file) is True

    # Verification: Task still exists with is_archived = 1
    t_after = database.get_task_by_id(task_id, db_path=db_file)
    assert t_after is not None
    assert t_after["is_archived"] == 1

    # Verification: Pomodoro focus sessions are 100% PRESERVED
    sessions_after = database.get_pomodoro_sessions(task_id=task_id, db_path=db_file)
    assert len(sessions_after) == 2

    # Verification: Daily pomodoro stats still count the focus minutes
    stats = database.get_daily_pomodoro_stats(quadrant="Q1_DO", db_path=db_file)
    assert stats["sprints_count"] == 2
    assert stats["total_focus_minutes"] == 50









