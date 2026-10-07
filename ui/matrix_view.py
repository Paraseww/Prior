"""
ui/matrix_view.py
The core 4-Quadrant Eisenhower Matrix workspace view for Prior.
Displays tasks categorized into Do First, Schedule, Delegate, and Eliminate.
"""

from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk

from project import is_task_delayed
from ui import theme
from ui.dot_pattern import DottedCardFrame, DottedScrollableFrame
from ui.task_card import TaskCard


class MatrixView(ctk.CTkFrame):
    """
    4-Quadrant Eisenhower Grid View with dot-matrix sketchbook canvas inside each quadrant.
    """

    def __init__(
        self,
        master: Any,
        tasks: List[Dict[str, Any]],
        on_toggle: Callable[[int], None],
        on_edit: Callable[[Dict[str, Any]], None],
        on_move: Callable[[int, str], None],
        on_delete: Callable[[int], None],
        on_quick_add: Callable[[str], None],
        on_archive: Optional[Callable[[int], None]] = None,
        on_reorder: Optional[Callable[[int, str, int], None]] = None,
        on_pomodoro: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_schedule: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.tasks = tasks
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_move = on_move
        self.on_delete = on_delete
        self.on_archive = on_archive or on_delete
        self.on_quick_add = on_quick_add
        self.on_reorder = on_reorder
        self.on_pomodoro = on_pomodoro
        self.on_schedule = on_schedule

        # Track collapsed/expanded state of completed tasks per quadrant
        self.completed_expanded: Dict[str, bool] = {
            "Q1_DO": False,
            "Q2_SCHEDULE": False,
            "Q3_DELEGATE": False,
            "Q4_ELIMINATE": False,
        }

        # Cache of current task signatures per quadrant to prevent unnecessary re-rendering
        self.current_quadrant_signatures: Dict[str, Any] = {}
        self.current_quadrant_tasks: Dict[str, List[Dict[str, Any]]] = {
            "Q1_DO": [],
            "Q2_SCHEDULE": [],
            "Q3_DELEGATE": [],
            "Q4_ELIMINATE": [],
        }

        self._build_ui()

    def _build_ui(self) -> None:
        # 2x2 Grid Configuration
        self.grid_rowconfigure(0, weight=1, uniform="row")
        self.grid_rowconfigure(1, weight=1, uniform="row")
        self.grid_columnconfigure(0, weight=1, uniform="col")
        self.grid_columnconfigure(1, weight=1, uniform="col")

        # Create 4 Quadrant Panes
        self.panes = {
            "Q1_DO": self._create_quadrant_pane("Q1_DO", row=0, col=0),
            "Q2_SCHEDULE": self._create_quadrant_pane("Q2_SCHEDULE", row=0, col=1),
            "Q3_DELEGATE": self._create_quadrant_pane("Q3_DELEGATE", row=1, col=0),
            "Q4_ELIMINATE": self._create_quadrant_pane("Q4_ELIMINATE", row=1, col=1),
        }

        self._populate_tasks(force=True)

    def _create_quadrant_pane(self, q_key: str, row: int, col: int) -> Dict[str, Any]:
        info = theme.QUADRANTS[q_key]

        # Container Frame with border and dot-grid canvas
        container = DottedCardFrame(
            self,
            fg_color=theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=info["border"],
        )
        container.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # Top Header Bar
        header = ctk.CTkFrame(
            container,
            fg_color=info["bg_header"],
            corner_radius=10,
            height=46,
        )
        header.pack(fill="x", padx=8, pady=(8, 4))
        header.pack_propagate(False)

        # Left: Color Dot + Title + Count Badge
        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", fill="y", padx=10)

        dot = ctk.CTkFrame(header_left, width=10, height=10, corner_radius=5, fg_color=info["color"])
        dot.pack(side="left", padx=(0, 6), pady=18)

        lbl_title = ctk.CTkLabel(
            header_left,
            text=info["title"],
            font=(theme.FONT_DISPLAY, 13, "bold"),
            text_color=info["text"],
        )
        lbl_title.pack(side="left", padx=(0, 8), pady=12)

        lbl_count = ctk.CTkLabel(
            header_left,
            text="0",
            font=(theme.FONT_FAMILY, 11, "bold"),
            fg_color=info["color"],
            text_color="#FFFFFF",
            corner_radius=8,
            width=22,
            height=20,
        )
        lbl_count.pack(side="left", pady=13)

        # Info / Guide button (ⓘ)
        btn_info = ctk.CTkButton(
            header_left,
            text="ⓘ",
            width=22,
            height=22,
            corner_radius=11,
            fg_color="transparent",
            hover_color=theme.BG_CARD_HOVER,
            text_color=info["color"],
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=lambda k=q_key: self._show_quadrant_guide(k),
        )
        btn_info.pack(side="left", padx=(6, 0), pady=12)

        # Right: Quick Add Button (+)
        btn_add = ctk.CTkButton(
            header,
            text="+ Add",
            font=(theme.FONT_FAMILY, 11, "bold"),
            width=60,
            height=26,
            corner_radius=6,
            fg_color=info["color"],
            hover_color=info["color_dark"],
            text_color="#FFFFFF",
            command=lambda: self.on_quick_add(q_key),
        )
        btn_add.pack(side="right", padx=10, pady=10)

        # Scrollable Task Container with matching dot-grid background
        scroll_frame = DottedScrollableFrame(
            container,
            corner_radius=8,
        )
        scroll_frame.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        return {
            "container": container,
            "count_label": lbl_count,
            "scroll_frame": scroll_frame,
            "info": info,
        }

    def _populate_tasks(self, force: bool = False) -> None:
        """Groups tasks and populates quadrants, only updating those that changed."""
        grouped: Dict[str, List[Dict[str, Any]]] = {
            "Q1_DO": [],
            "Q2_SCHEDULE": [],
            "Q3_DELEGATE": [],
            "Q4_ELIMINATE": [],
        }

        for task in self.tasks:
            q = task.get("quadrant", "Q1_DO")
            if q in grouped:
                grouped[q].append(task)

        for q_key in ("Q1_DO", "Q2_SCHEDULE", "Q3_DELEGATE", "Q4_ELIMINATE"):
            self._populate_quadrant(q_key, grouped[q_key], force=force)

    def _populate_quadrant(self, q_key: str, q_tasks: List[Dict[str, Any]], force: bool = False) -> None:
        """Populates a single quadrant, skipping if its tasks and states have not changed."""
        signature = [(dict(t), is_task_delayed(t)) for t in q_tasks]
        if not force and self.current_quadrant_signatures.get(q_key) == signature:
            return  # No changes in this quadrant! Do NOT touch it!

        self.current_quadrant_signatures[q_key] = signature
        self.current_quadrant_tasks[q_key] = [dict(t) for t in q_tasks]

        pane = self.panes[q_key]
        scroll_frame = pane["scroll_frame"]

        # Preserve scroll position if scrolled
        yview_pos = 0.0
        try:
            if hasattr(scroll_frame, "_parent_canvas"):
                yview_pos = scroll_frame._parent_canvas.yview()[0]
        except Exception:
            pass

        active_tasks = [t for t in q_tasks if not bool(t.get("is_completed", 0))]
        completed_tasks = [t for t in q_tasks if bool(t.get("is_completed", 0))]

        # Update count pill (show active count; if 0 active and some completed, show ✓)
        if len(active_tasks) > 0:
            pane["count_label"].configure(text=str(len(active_tasks)))
        elif len(completed_tasks) > 0:
            pane["count_label"].configure(text="✓")
        else:
            pane["count_label"].configure(text="0")

        # Clear previous widgets in this quadrant only
        for child in scroll_frame.winfo_children():
            child.destroy()

        if not q_tasks:
            empty_lbl = ctk.CTkLabel(
                scroll_frame,
                text="No tasks in this quadrant.\nClick '+ Add' to create one.",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_MUTED,
                justify="center",
            )
            empty_lbl.pack(pady=40, fill="x")
        else:
            # 1. Render active tasks at top
            if active_tasks:
                for task in active_tasks:
                    card = TaskCard(
                        scroll_frame,
                        task=task,
                        on_toggle=self.on_toggle,
                        on_edit=self.on_edit,
                        on_move=self.on_move,
                        on_reorder=self.on_reorder,
                        on_delete=self.on_delete,
                        on_archive=self.on_archive,
                        on_pomodoro=self.on_pomodoro,
                        on_schedule=self.on_schedule,
                        find_target_quadrant=self.get_quadrant_at_pointer,
                        find_drop_target=self.get_drop_target,
                        highlight_target_quadrant=self.highlight_quadrant,
                    )
                    card.pack(fill="x", pady=4, padx=2)
            elif completed_tasks:
                all_done_lbl = ctk.CTkLabel(
                    scroll_frame,
                    text="All tasks completed! 🎉",
                    font=(theme.FONT_FAMILY, 12, "bold"),
                    text_color=theme.TEXT_MUTED,
                    justify="center",
                )
                all_done_lbl.pack(pady=(24, 8), fill="x")

            # 2. Render collapsible completed section at the bottom if completed tasks exist
            if completed_tasks:
                is_expanded = self.completed_expanded.get(q_key, False)
                num_completed = len(completed_tasks)

                toggle_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                toggle_frame.pack(fill="x", pady=(12, 4), padx=2)

                arrow = "▾" if is_expanded else "▸"
                btn_toggle = ctk.CTkButton(
                    toggle_frame,
                    text=f"{arrow} Completed ({num_completed})",
                    font=(theme.FONT_FAMILY, 11, "bold"),
                    height=28,
                    corner_radius=6,
                    fg_color="transparent",
                    hover_color=theme.BG_CARD_HOVER,
                    text_color=theme.TEXT_MUTED,
                    anchor="w",
                    command=lambda k=q_key: self._toggle_completed(k),
                )
                btn_toggle.pack(fill="x")

                if is_expanded:
                    completed_box = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                    completed_box.pack(fill="x", pady=(0, 4))
                    for c_task in completed_tasks:
                        card = TaskCard(
                            completed_box,
                            task=c_task,
                            on_toggle=self.on_toggle,
                            on_edit=self.on_edit,
                            on_move=self.on_move,
                            on_reorder=self.on_reorder,
                            on_delete=self.on_delete,
                            on_archive=self.on_archive,
                            on_pomodoro=self.on_pomodoro,
                            on_schedule=self.on_schedule,
                            find_target_quadrant=self.get_quadrant_at_pointer,
                            find_drop_target=self.get_drop_target,
                            highlight_target_quadrant=self.highlight_quadrant,
                        )
                        card.pack(fill="x", pady=4, padx=2)

        # Restore scroll position if previously scrolled
        if yview_pos > 0.0:
            try:
                scroll_frame._parent_canvas.yview_moveto(yview_pos)
            except Exception:
                pass

    def _toggle_completed(self, q_key: str) -> None:
        """Toggles the visibility of the completed tasks section for a quadrant without touching other quadrants."""
        self.completed_expanded[q_key] = not self.completed_expanded.get(q_key, False)
        self._populate_quadrant(q_key, self.current_quadrant_tasks.get(q_key, []), force=True)

    def _show_quadrant_guide(self, q_key: str) -> None:
        """Opens the quadrant guide and analytics explanation modal."""
        from ui.quadrant_guide_modal import QuadrantGuideModal
        QuadrantGuideModal(self.winfo_toplevel(), q_key=q_key)

    def get_drop_target(self, root_x: int, root_y: int) -> tuple[Optional[str], int]:
        """
        Identifies which quadrant container and position index is under the screen coordinates.
        Returns (quadrant_key, insert_index).
        """
        for q_key, pane in self.panes.items():
            container = pane["container"]
            try:
                rx = container.winfo_rootx()
                ry = container.winfo_rooty()
                rw = container.winfo_width()
                rh = container.winfo_height()
                if rx <= root_x <= rx + rw and ry <= root_y <= ry + rh:
                    scroll_frame = pane["scroll_frame"]
                    cards = [w for w in scroll_frame.winfo_children() if isinstance(w, TaskCard)]
                    if not cards:
                        return q_key, 0

                    for idx, card in enumerate(cards):
                        try:
                            cy = card.winfo_rooty()
                            ch = card.winfo_height()
                            mid_y = cy + ch / 2
                            if root_y < mid_y:
                                return q_key, idx
                        except Exception:
                            continue
                    return q_key, len(cards)
            except Exception:
                continue
        return None, 0

    def get_quadrant_at_pointer(self, root_x: int, root_y: int) -> Optional[str]:
        """Identifies which quadrant container is under the screen coordinates."""
        q_key, _ = self.get_drop_target(root_x, root_y)
        return q_key

    def highlight_quadrant(self, target_q: Optional[str]) -> None:
        """Visual highlight on quadrant container during mouse dragging."""
        for q_key, pane in self.panes.items():
            container = pane["container"]
            info = pane["info"]
            if q_key == target_q:
                container.configure(border_width=3, border_color=info["color"])
            else:
                container.configure(border_width=1, border_color=info["border"])

    def refresh_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Refreshes the matrix with an updated task list, updating only affected quadrants."""
        self.tasks = tasks
        self._populate_tasks(force=False)
