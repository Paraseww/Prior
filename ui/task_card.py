"""
ui/task_card.py
Interactive Task Card widget for Eisenhower Matrix and List Views.
Supports wireframe shuffle-on-hover effect:
- Normal state: Standard task card with checkbox, title, tags, and action buttons.
- Hover state (Q1): Solid emerald card displaying "Focus with Pomodoro" + 🍅 icon.
- Hover state (Q2): Solid blue card displaying "Schedule tasks using calendar" + 📅 icon.
- Clicking the hover card triggers the respective focus timer or scheduling action.
"""

from typing import Any, Callable, Dict, Optional
import customtkinter as ctk

from project import format_due_status
from ui import theme


class TaskCard(ctk.CTkFrame):
    """
    Component representing a single task card with wireframe hover transformations.
    """

    def __init__(
        self,
        master: Any,
        task: Dict[str, Any],
        on_toggle: Callable[[int], None],
        on_edit: Callable[[Dict[str, Any]], None],
        on_move: Callable[[int, str], None],
        on_delete: Callable[[int], None],
        on_pomodoro: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_schedule: Optional[Callable[[Dict[str, Any]], None]] = None,
        find_target_quadrant: Optional[Callable[[int, int], Optional[str]]] = None,
        highlight_target_quadrant: Optional[Callable[[Optional[str]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
            **kwargs,
        )
        self.task = task
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_move = on_move
        self.on_delete = on_delete
        self.on_pomodoro = on_pomodoro
        self.on_schedule = on_schedule
        self.find_target_quadrant = find_target_quadrant
        self.highlight_target_quadrant = highlight_target_quadrant

        # Hover state flag
        self.is_hovered = False
        self.is_completed = bool(self.task.get("is_completed", 0))

        # Quadrant Theme Details
        self.q_key = self.task.get("quadrant", "Q1_DO")
        self.q_info = theme.QUADRANTS.get(self.q_key, theme.QUADRANTS["Q1_DO"])
        self.q_color = self.q_info["color"]
        self.q_border = self.q_info["border"]

        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=self.q_border,
            **kwargs,
        )
        self.task = task
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_move = on_move
        self.on_delete = on_delete
        self.on_pomodoro = on_pomodoro
        self.on_schedule = on_schedule
        self.find_target_quadrant = find_target_quadrant
        self.highlight_target_quadrant = highlight_target_quadrant

        self._build_normal_ui()

        # Hover shuffle is active for Q1 (Do First) and Q2 (Schedule) tasks
        if self.q_key in ("Q1_DO", "Q2_SCHEDULE"):
            self._setup_hover_config()
            self._build_hover_ui()
            self._bind_hover_events()

        self._setup_drag_and_drop()

    def _setup_hover_config(self) -> None:
        """Sets up the hover text, icons, and colors for Q1 (Pomodoro) and Q2 (Schedule)."""
        if self.q_key == "Q1_DO":
            self.hover_text = "Focus with Pomodoro"
            self.hover_icon = "🍅"
            self.hover_bg = ("#FEE2E2", "#7F1D1D")
            self.hover_text_color = ("#991B1B", "#FEF2F2")
            self.hover_action = self._on_pomodoro_click
        elif self.q_key == "Q2_SCHEDULE":
            self.hover_text = "Schedule Date & Reminder Time"
            self.hover_icon = "📅"
            self.hover_bg = ("#ECFDF5", "#064E3B")
            self.hover_text_color = ("#065F46", "#ECFDF5")
            self.hover_action = self._on_schedule_click

    def _build_normal_ui(self) -> None:
        """Builds the standard task card view with clean left-aligned typography."""
        self.normal_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.normal_frame.pack(fill="both", expand=True, padx=12, pady=10)

        # 1. Left Vertical Quadrant Accent Stripe
        stripe_color = ("#94A3B8", "#64748B") if self.is_completed else self.q_color
        self.stripe = ctk.CTkFrame(
            self.normal_frame,
            width=4,
            corner_radius=2,
            fg_color=stripe_color,
        )
        self.stripe.pack(side="left", fill="y", padx=(0, 8))

        # 2. Checkbox Section anchored to top-left
        left_box = ctk.CTkFrame(self.normal_frame, fg_color="transparent")
        left_box.pack(side="left", fill="y", anchor="n", padx=(0, 8))

        self.check_var = ctk.BooleanVar(value=self.is_completed)
        self.cb = ctk.CTkCheckBox(
            left_box,
            text="",
            variable=self.check_var,
            width=20,
            height=20,
            corner_radius=5,
            fg_color=self.q_color,
            hover_color=self.q_info["color_dark"],
            border_color=self.q_color if not self.is_completed else theme.BORDER_COLOR,
            border_width=2,
            command=lambda: self.on_toggle(self.task["id"]),
        )
        self.cb.pack(side="top", pady=(2, 0))

        # 3. Right Section: Action buttons anchored to top-right
        right_box = ctk.CTkFrame(self.normal_frame, fg_color="transparent")
        right_box.pack(side="right", fill="y", anchor="n", padx=(4, 0))

        btn_del = ctk.CTkButton(
            right_box,
            text="✕",
            width=22,
            height=22,
            corner_radius=5,
            fg_color="transparent",
            hover_color=("#FEE2E2", "#7F1D1D"),
            text_color=("#EF4444", "#F87171"),
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=lambda: self.on_delete(self.task["id"]),
        )
        btn_del.pack(side="right", padx=(2, 0))

        btn_edit = ctk.CTkButton(
            right_box,
            text="✎",
            width=22,
            height=22,
            corner_radius=5,
            fg_color="transparent",
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, 11),
            command=lambda: self.on_edit(self.task),
        )
        btn_edit.pack(side="right", padx=(2, 0))

        # 4. Center Section: Left-aligned Title, Description, and Badges
        self.center_box = ctk.CTkFrame(self.normal_frame, fg_color="transparent")
        self.center_box.pack(side="left", fill="both", expand=True)

        # Title
        title_text = self.task.get("title", "Untitled Task")
        title_color = theme.TEXT_MUTED if self.is_completed else theme.TEXT_PRIMARY

        self.lbl_title = ctk.CTkLabel(
            self.center_box,
            text=title_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=title_color,
            anchor="w",
            justify="left",
            wraplength=220,
            cursor="fleur" if not self.is_completed else "arrow",
        )
        self.lbl_title.pack(fill="x", anchor="w")

        # Description (if present)
        description = self.task.get("description", "").strip()
        if description:
            self.lbl_desc = ctk.CTkLabel(
                self.center_box,
                text=description,
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_MUTED if self.is_completed else theme.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=220,
            )
            self.lbl_desc.pack(fill="x", anchor="w", pady=(3, 2))

        # Badges Row: Persistent Quadrant Category Badge + Due Date Badge + Reminder Time Badge
        badges_row = ctk.CTkFrame(self.center_box, fg_color="transparent")
        badges_row.pack(anchor="w", pady=(5, 0))

        # 4a. Priority Category Badge
        if self.is_completed:
            badge_bg = ("#E2E8F0", "#334155")
            badge_border = ("#CBD5E1", "#475569")
            badge_text_color = ("#64748B", "#94A3B8")
            badge_title = f"✓ {self.q_info['badge']}"
        else:
            badge_bg = self.q_info["bg_header"]
            badge_border = self.q_info["border"]
            badge_text_color = self.q_info["text"]
            badge_title = f"● {self.q_info['badge']}"

        quad_badge = ctk.CTkFrame(
            badges_row,
            fg_color=badge_bg,
            corner_radius=6,
            height=20,
            border_width=1,
            border_color=badge_border,
        )
        quad_badge.pack(side="left", padx=(0, 6))

        lbl_quad = ctk.CTkLabel(
            quad_badge,
            text=badge_title,
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=badge_text_color,
        )
        lbl_quad.pack(padx=6, pady=1)

        # 4b. Due Date Badge & Reminder Time Badge
        due_date_str = self.task.get("due_date")
        reminder_time_str = self.task.get("reminder_time")

        has_due = False
        due_info = None
        if due_date_str:
            due_info = format_due_status(due_date_str)
            if due_info.get("status") not in ("NO_DUE_DATE", "INVALID_DATE"):
                has_due = True

        has_reminder = bool(reminder_time_str and str(reminder_time_str).strip())

        if has_due and due_info:
            status_type = due_info.get("status")
            if status_type == "OVERDUE":
                due_bg = ("#FEE2E2", "#7F1D1D")
                due_border = ("#FECACA", "#B91C1C")
                due_text = ("#991B1B", "#F87171")
            elif status_type == "TODAY":
                due_bg = ("#FEF3C7", "#78350F")
                due_border = ("#FDE68A", "#B45309")
                due_text = ("#92400E", "#FBBF24")
            else:
                due_bg = theme.BG_INPUT
                due_border = theme.BORDER_COLOR
                due_text = theme.TEXT_SECONDARY

            due_badge = ctk.CTkFrame(
                badges_row,
                fg_color=due_bg,
                corner_radius=6,
                height=20,
                border_width=1,
                border_color=due_border,
            )
            due_badge.pack(side="left", padx=(0, 6))

            lbl_due = ctk.CTkLabel(
                due_badge,
                text=f"📅 {due_info['label']}",
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=due_text,
            )
            lbl_due.pack(padx=6, pady=1)

        if has_reminder:
            time_badge = ctk.CTkFrame(
                badges_row,
                fg_color=theme.BG_INPUT,
                corner_radius=6,
                height=20,
                border_width=1,
                border_color=theme.BORDER_COLOR,
            )
            time_badge.pack(side="left")

            lbl_time = ctk.CTkLabel(
                time_badge,
                text=f"⏰ {str(reminder_time_str).strip()}",
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=theme.TEXT_SECONDARY,
            )
            lbl_time.pack(padx=6, pady=1)

        # Responsive wraplength adjustment based on container width
        def _on_resize(event: Any) -> None:
            wrap_w = max(140, event.width - 6)
            self.lbl_title.configure(wraplength=wrap_w)
            if hasattr(self, "lbl_desc"):
                self.lbl_desc.configure(wraplength=wrap_w)

        self.center_box.bind("<Configure>", _on_resize)

    def _setup_drag_and_drop(self) -> None:
        """Binds mouse dragging to move tasks across quadrants seamlessly."""
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False
        self._drag_ghost: Optional[ctk.CTkToplevel] = None

        # Bind drag events to card container, normal frame, and title
        drag_widgets = [self, self.normal_frame, self.lbl_title, self.center_box]
        if hasattr(self, "stripe"):
            drag_widgets.append(self.stripe)
        if hasattr(self, "lbl_desc"):
            drag_widgets.append(self.lbl_desc)
        if hasattr(self, "hover_frame"):
            drag_widgets.extend([self.hover_frame, self.inner_hover, self.lbl_action, self.lbl_icon])

        for widget in drag_widgets:
            widget.bind("<ButtonPress-1>", self._on_drag_start, add="+")
            widget.bind("<B1-Motion>", self._on_drag_motion, add="+")
            widget.bind("<ButtonRelease-1>", self._on_drag_release, add="+")

    def _on_drag_start(self, event: Any) -> None:
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._is_dragging = False

    def _on_drag_motion(self, event: Any) -> None:
        dx = abs(event.x_root - self._drag_start_x)
        dy = abs(event.y_root - self._drag_start_y)

        # Start drag after passing movement threshold
        if not self._is_dragging and (dx > 6 or dy > 6):
            self._is_dragging = True
            try:
                self._drag_ghost = ctk.CTkToplevel(self)
                self._drag_ghost.overrideredirect(True)
                self._drag_ghost.attributes("-topmost", True)
                self._drag_ghost.attributes("-alpha", 0.92)
                self._drag_ghost.configure(fg_color=self.q_color)

                ghost_inner = ctk.CTkFrame(self._drag_ghost, fg_color=self.q_color, corner_radius=8)
                ghost_inner.pack(padx=8, pady=4)

                short_title = self.task.get("title", "Task")
                if len(short_title) > 22:
                    short_title = short_title[:20] + "..."

                lbl = ctk.CTkLabel(
                    ghost_inner,
                    text=f"✋ Move: {short_title}",
                    font=(theme.FONT_FAMILY, 11, "bold"),
                    text_color="#FFFFFF",
                )
                lbl.pack()
            except Exception:
                self._drag_ghost = None

        if self._is_dragging and self._drag_ghost:
            try:
                self._drag_ghost.geometry(f"+{event.x_root + 15}+{event.y_root + 10}")
            except Exception:
                pass

            if self.find_target_quadrant and self.highlight_target_quadrant:
                target_q = self.find_target_quadrant(event.x_root, event.y_root)
                self.highlight_target_quadrant(target_q)

    def _on_drag_release(self, event: Any) -> None:
        if self._is_dragging:
            self._is_dragging = False

            if self._drag_ghost:
                try:
                    self._drag_ghost.destroy()
                except Exception:
                    pass
                self._drag_ghost = None

            if self.highlight_target_quadrant:
                self.highlight_target_quadrant(None)

            if self.find_target_quadrant and self.on_move:
                target_q = self.find_target_quadrant(event.x_root, event.y_root)
                if target_q and target_q != self.q_key:
                    self.on_move(self.task["id"], target_q)
        else:
            # Click action on hover overlay (opens Pomodoro for Q1, Schedule for Q2)
            if self.is_hovered and self.q_key in ("Q1_DO", "Q2_SCHEDULE"):
                self._on_hover_click()

    def _build_hover_ui(self) -> None:
        """Builds the full-card hover transformation as an overlay."""
        self.hover_frame = ctk.CTkFrame(
            self,
            fg_color=self.hover_bg,
            corner_radius=9,
            cursor="fleur",
        )

        self.inner_hover = ctk.CTkFrame(self.hover_frame, fg_color="transparent")
        self.inner_hover.pack(fill="both", expand=True, padx=14, pady=10)

        self.lbl_action = ctk.CTkLabel(
            self.inner_hover,
            text=self.hover_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=self.hover_text_color,
            anchor="w",
            cursor="fleur",
        )
        self.lbl_action.pack(side="left", fill="x", expand=True)

        self.lbl_icon = ctk.CTkLabel(
            self.inner_hover,
            text=self.hover_icon,
            font=(theme.FONT_FAMILY, 18),
            cursor="fleur",
        )
        self.lbl_icon.pack(side="right", padx=(4, 0))

    def _on_pomodoro_click(self) -> None:
        if self.on_pomodoro:
            self.on_pomodoro(self.task)
        else:
            self.on_edit(self.task)

    def _on_schedule_click(self) -> None:
        if self.on_schedule:
            self.on_schedule(self.task)
        else:
            self.on_edit(self.task)

    def _on_hover_click(self) -> None:
        if self.hover_action:
            self.hover_action()

    def _bind_hover_events(self) -> None:
        """Recursively binds hover triggers for seamless, flicker-free shuffle for Q1 and Q2."""
        if self.q_key not in ("Q1_DO", "Q2_SCHEDULE"):
            return
        self._bind_to_widget(self)
        if hasattr(self, "hover_frame"):
            self._bind_to_widget(self.hover_frame)

    def _bind_to_widget(self, widget: Any) -> None:
        widget.bind("<Enter>", self._on_mouse_enter, add="+")
        widget.bind("<Leave>", self._on_mouse_leave, add="+")
        for child in widget.winfo_children():
            # Exclude interactive controls that have native click handling
            if not isinstance(child, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkOptionMenu)):
                self._bind_to_widget(child)

    def _on_mouse_enter(self, event: Any = None) -> None:
        # Only active Q1 and Q2 tasks perform the hover shuffle
        if self.q_key not in ("Q1_DO", "Q2_SCHEDULE") or self.is_completed:
            return

        if self.is_hovered or not hasattr(self, "hover_frame"):
            return
        self.is_hovered = True

        # Use place() overlay to maintain exact dimensions without shifting adjacent cards
        self.hover_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.hover_frame.lift()
        self.configure(
            border_color=self.q_color,
            border_width=2,
        )

    def _on_mouse_leave(self, event: Any = None) -> None:
        if self.q_key not in ("Q1_DO", "Q2_SCHEDULE"):
            return

        # Check if cursor is still within the bounding box of TaskCard
        try:
            x, y = self.winfo_pointerx(), self.winfo_pointery()
            rx, ry = self.winfo_rootx(), self.winfo_rooty()
            rw, rh = self.winfo_width(), self.winfo_height()
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return  # Still inside card boundary
        except Exception:
            pass

        if not self.is_hovered or not hasattr(self, "hover_frame"):
            return
        self.is_hovered = False

        # Hide overlay without altering parent container dimensions
        self.hover_frame.place_forget()
        self.configure(
            border_color=theme.BORDER_COLOR,
            border_width=1,
        )
