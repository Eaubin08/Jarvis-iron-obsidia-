"""Jarjar desktop HUD.

Donor-inspired patterns:
- HUD is a presentation shell, not the agent authority.
- cognition/voice work runs outside the Tk main thread.
- avatar visual reacts to canonical HUD states.
"""
from __future__ import annotations

import math
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

from .hud_controller import HUDController
from .hud_state import HUDState


STATE_COLORS = {
    HUDState.IDLE.value: "#4dd8ff",
    HUDState.LISTENING.value: "#38ff9c",
    HUDState.THINKING.value: "#ffb347",
    HUDState.SPEAKING.value: "#d86cff",
    HUDState.ERROR.value: "#ff4567",
}

WAKE_COLOR = "#4dd8ff"
SESSION_COLOR = "#38ff9c"


class JarjarHUD(tk.Tk):
    def __init__(self, controller: HUDController):
        super().__init__()
        self.controller = controller
        self.title("JARJAR // Desktop Companion")
        self.geometry("1080x720")
        self.minsize(860, 560)
        self.configure(bg="#05080d")

        self._ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._angle = 0.0
        self._message_count = 0
        self._voice_busy = threading.Lock()
        self._voice_stop = threading.Event()
        self._voice_thread: threading.Thread | None = None
        self._closing = False

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(30, self._animate_avatar)
        self.after(75, self._drain_ui_queue)
        self.after(150, self._sync_model)
        self.after(300, self._ensure_auto_voice)

    def _build(self) -> None:
        top = tk.Frame(self, bg="#05080d")
        top.pack(fill="x", padx=18, pady=(14, 8))

        tk.Label(
            top,
            text="JARJAR",
            fg="#d8f8ff",
            bg="#05080d",
            font=("Consolas", 24, "bold"),
        ).pack(side="left")
        self.status = tk.Label(
            top,
            text="● IDLE",
            fg=STATE_COLORS[HUDState.IDLE.value],
            bg="#05080d",
            font=("Consolas", 12, "bold"),
        )
        self.status.pack(side="right")

        self.governance = tk.Label(
            top,
            text="",
            fg="#7f98a3",
            bg="#05080d",
            font=("Consolas", 10, "bold"),
        )
        self.governance.pack(side="right", padx=(0, 18))

        body = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            bg="#0c1720",
            bd=0,
            relief=tk.FLAT,
        )
        body.pack(fill="both", expand=True, padx=18, pady=8)

        avatar_panel = tk.Frame(body, bg="#071019", width=380)
        chat_panel = tk.Frame(body, bg="#09121a")
        body.add(avatar_panel, minsize=320)
        body.add(chat_panel, minsize=440)

        self.canvas = tk.Canvas(
            avatar_panel,
            bg="#071019",
            highlightthickness=0,
            width=360,
            height=420,
        )
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)

        self.avatar_caption = tk.Label(
            avatar_panel,
            text="DESKTOP COMPANION // ALWAYS LISTENING",
            fg="#688b9b",
            bg="#071019",
            font=("Consolas", 10),
        )
        self.avatar_caption.pack(pady=(0, 18))

        transcript_frame = tk.Frame(chat_panel, bg="#09121a")
        transcript_frame.pack(fill="both", expand=True, padx=14, pady=(14, 8))

        self.transcript = tk.Text(
            transcript_frame,
            wrap="word",
            bg="#071019",
            fg="#b8dce8",
            insertbackground="#d8f8ff",
            relief=tk.FLAT,
            font=("Consolas", 11),
            padx=14,
            pady=14,
            state="disabled",
        )
        scroll = ttk.Scrollbar(
            transcript_frame, orient="vertical", command=self.transcript.yview
        )
        self.transcript.configure(yscrollcommand=scroll.set)
        self.transcript.tag_configure("speaker_you", foreground="#62e6ff", font=("Consolas", 11, "bold"))
        self.transcript.tag_configure("text_you", foreground="#bff7ff")
        self.transcript.tag_configure("speaker_jarjar", foreground="#ffd166", font=("Consolas", 11, "bold"))
        self.transcript.tag_configure("text_jarjar", foreground="#f2f7fa")
        self.transcript.tag_configure("source", foreground="#607681", font=("Consolas", 9))
        self.transcript.tag_configure("system", foreground="#7f98a3")
        self.transcript.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        controls = tk.Frame(chat_panel, bg="#09121a")
        controls.pack(fill="x", padx=14, pady=(0, 14))

        self.entry = tk.Entry(
            controls,
            bg="#0d1a24",
            fg="#ecfbff",
            insertbackground="#ecfbff",
            relief=tk.FLAT,
            font=("Consolas", 11),
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=10)
        self.entry.bind("<Return>", lambda _event: self._submit_text())

        tk.Button(
            controls,
            text="SEND",
            command=self._submit_text,
            bg="#102b39",
            fg="#bff5ff",
            activebackground="#17465a",
            activeforeground="white",
            relief=tk.FLAT,
            padx=18,
        ).pack(side="left", padx=(8, 0), ipady=6)

        self.voice_button = tk.Button(
            controls,
            text="VOICE ON",
            command=self._toggle_voice,
            bg="#103428",
            fg="#a9ffd2",
            activebackground="#14553d",
            activeforeground="white",
            relief=tk.FLAT,
            padx=14,
        )
        self.voice_button.pack(side="left", padx=(8, 0), ipady=6)

        tk.Button(
            controls,
            text="LISTEN",
            command=self._start_voice_turn,
            bg="#102b39",
            fg="#bff5ff",
            activebackground="#17465a",
            activeforeground="white",
            relief=tk.FLAT,
            padx=14,
        ).pack(side="left", padx=(8, 0), ipady=6)

    def _submit_text(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        threading.Thread(target=self._text_worker, args=(text,), daemon=True).start()

    def _text_worker(self, text: str) -> None:
        # Do not let microphone capture race a spoken text response.
        with self._voice_busy:
            try:
                self.controller.submit_text(text)
            except Exception as exc:
                print(f"JARJAR_VOICE_LOOP: ERROR {type(exc).__name__}: {exc}")
                self.controller.model.append("SYSTEM", f"{type(exc).__name__}: {exc}")

    def _start_voice_turn(self) -> None:
        threading.Thread(target=self._manual_voice_worker, daemon=True).start()

    def _manual_voice_worker(self) -> None:
        if not self._voice_busy.acquire(blocking=False):
            return
        try:
            result = self.controller.run_voice_turn()
            if result is not None:
                self.controller.voice_finished()
        except Exception as exc:
            self.controller.model.append("SYSTEM", f"{type(exc).__name__}: {exc}")
        finally:
            self._voice_busy.release()

    def _ensure_auto_voice(self) -> None:
        if self._closing:
            return

        snap = self.controller.model.snapshot()
        if (
            snap["voice_enabled"]
            and (self._voice_thread is None or not self._voice_thread.is_alive())
        ):
            self._voice_stop.clear()
            self._voice_thread = threading.Thread(
                target=self._auto_voice_loop,
                name="jarjar-always-listening",
                daemon=True,
            )
            self._voice_thread.start()
            print("JARJAR_VOICE_LOOP: STARTED")

        # Watchdog: if the always-listening thread ever exits unexpectedly,
        # restart it automatically instead of leaving the HUD silently deaf.
        self.after(1000, self._ensure_auto_voice)

    def _auto_voice_loop(self) -> None:
        print("JARJAR_VOICE_LOOP: LISTENING")
        while not self._voice_stop.is_set():
            snap = self.controller.model.snapshot()
            if not snap["voice_enabled"]:
                return
            if snap["state"] in {HUDState.THINKING.value, HUDState.SPEAKING.value}:
                self._voice_stop.wait(0.1)
                continue

            if not self._voice_busy.acquire(timeout=0.2):
                continue
            try:
                result = self.controller.run_voice_turn()
                if result is None:
                    # Wake was detected but no usable command survived capture/STT.
                    # Fully reset the transient session so the next loop returns
                    # immediately to wake-word monitoring.
                    self.controller.model.set_session_open(False)
                    self.controller.model.set_state(HUDState.IDLE)
                    print("JARJAR_WAKE: READY (reset after empty wake turn)")
                    continue
                self.controller.voice_finished()
                self.controller.model.set_session_open(True)

                # Conversation Runtime V1:
                # one wake opens a bounded dialogue session. Short silent
                # windows do not force another wake word; only sustained
                # inactivity expires the session.
                last_activity = time.monotonic()
                while (
                    not self._voice_stop.is_set()
                    and self.controller.model.snapshot()["voice_enabled"]
                    and self.controller.follow_up_turn_handler is not None
                ):
                    follow = self.controller.run_follow_up_turn()
                    if follow is None:
                        idle_for = time.monotonic() - last_activity
                        if idle_for < self.controller.conversation_idle_seconds:
                            continue
                        print(
                            f"JARJAR_SESSION: CLOSED (idle {idle_for:.1f}s)"
                        )
                        self.controller.model.set_session_open(False)
                        break
                    last_activity = time.monotonic()
                    self.controller.voice_finished()
            except Exception as exc:
                self.controller.model.append("SYSTEM", f"{type(exc).__name__}: {exc}")
                self.controller.model.set_session_open(False)
                self.controller.model.set_state(HUDState.IDLE)
                self._voice_stop.wait(0.5)
            finally:
                self._voice_busy.release()

    def _toggle_voice(self) -> None:
        enabled = self.controller.toggle_voice()
        self.voice_button.configure(
            text="VOICE ON" if enabled else "VOICE OFF",
            bg="#103428" if enabled else "#32151c",
            fg="#a9ffd2" if enabled else "#ff9aaa",
        )
        self.avatar_caption.configure(
            text=(
                "DESKTOP COMPANION // ALWAYS LISTENING"
                if enabled
                else "DESKTOP COMPANION // VOICE PAUSED"
            )
        )
        if enabled:
            self._ensure_auto_voice()
        else:
            self.controller.model.set_session_open(False)
            self._voice_stop.set()

    def _sync_model(self) -> None:
        snap = self.controller.model.snapshot()
        state = snap["state"]
        session_open = snap.get("session_open", False)

        if state == HUDState.LISTENING.value and session_open:
            status_text = "● PARLE // ÉCOUTE"
            color = SESSION_COLOR
        elif state == HUDState.LISTENING.value:
            status_text = "● WAKE // ÉCOUTE"
            color = WAKE_COLOR
        elif state == HUDState.THINKING.value:
            status_text = "● RÉFLEXION"
            color = STATE_COLORS[state]
        elif state == HUDState.SPEAKING.value:
            status_text = "● JARJAR PARLE"
            color = STATE_COLORS[state]
        elif session_open:
            status_text = "● CONVERSATION OUVERTE"
            color = SESSION_COLOR
        else:
            status_text = f"● {state.upper()}"
            color = STATE_COLORS.get(state, WAKE_COLOR)

        self.status.configure(text=status_text, fg=color)

        if snap.get("governance_active"):
            authority = snap.get("decision_authority") or "UNKNOWN"
            source = snap.get("governance_source") or "GOVERNED"
            phase = snap.get("governance_phase") or "GOVERNED"
            self.governance.configure(
                text=f"◆ {authority} // {phase} // {source}",
                fg="#ffd166",
            )
        else:
            self.governance.configure(text="")

        if not snap["voice_enabled"]:
            caption = "DESKTOP COMPANION // VOICE PAUSED"
        elif session_open:
            caption = "PARLE // JE T'ÉCOUTE"
        else:
            caption = "WAKE MODE // DIS « HEY JARVIS »"
        self.avatar_caption.configure(text=caption, fg=color)

        messages = snap["messages"]
        if len(messages) > self._message_count:
            for item in messages[self._message_count:]:
                self._append_transcript(item["speaker"], item["text"])
            self._message_count = len(messages)

        self.after(150, self._sync_model)

    def _append_transcript(self, speaker: str, text: str) -> None:
        self.transcript.configure(state="normal")

        if speaker == "YOU":
            self.transcript.insert("end", "YOU> ", "speaker_you")
            self.transcript.insert("end", text + "\n\n", "text_you")

        elif speaker.startswith("JARJAR"):
            self.transcript.insert("end", f"{speaker}> ", "speaker_jarjar")

            source_markers = (
                "\n**Sources de référence",
                "\nSources de référence",
                "\n_Brody",
                "\nBrody — réponse structurée",
            )
            positions = [
                text.find(marker)
                for marker in source_markers
                if text.find(marker) >= 0
            ]
            if positions:
                split_at = min(positions)
                main = text[:split_at].rstrip()
                source = text[split_at:].strip()
            else:
                main, source = text, ""

            self.transcript.insert("end", main + "\n", "text_jarjar")
            if source:
                self.transcript.insert("end", source + "\n", "source")
            self.transcript.insert("end", "\n")

        else:
            self.transcript.insert("end", f"{speaker}> {text}\n\n", "system")

        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def _animate_avatar(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 320)
        height = max(self.canvas.winfo_height(), 360)
        cx, cy = width / 2, height / 2
        snap = self.controller.model.snapshot()
        state = snap["state"]
        session_open = snap.get("session_open", False)

        if state == HUDState.THINKING.value:
            color = STATE_COLORS[state]
            speed = 0.070
            pulse_depth = 0.14
        elif state == HUDState.SPEAKING.value:
            color = STATE_COLORS[state]
            speed = 0.055
            pulse_depth = 0.18
        elif session_open:
            color = SESSION_COLOR
            speed = 0.045
            pulse_depth = 0.12
        else:
            color = WAKE_COLOR
            speed = 0.025
            pulse_depth = 0.05

        self._angle = (self._angle + speed) % (math.pi * 2)
        pulse = 1.0 + pulse_depth * math.sin(self._angle * 3)

        radius = min(width, height) * 0.19 * pulse
        for ring in range(4):
            r = radius + ring * 18
            start = math.degrees(self._angle * (1 if ring % 2 == 0 else -1))
            self.canvas.create_arc(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                start=start,
                extent=210 - ring * 15,
                style="arc",
                outline=color,
                width=max(1, 4 - ring),
            )

        core_r = radius * 0.47
        self.canvas.create_oval(
            cx - core_r,
            cy - core_r,
            cx + core_r,
            cy + core_r,
            outline=color,
            width=3,
        )
        self.canvas.create_text(
            cx,
            cy,
            text="J",
            fill=color,
            font=("Consolas", int(core_r * 0.9), "bold"),
        )

        for i in range(10):
            a = self._angle + i * (math.pi * 2 / 10)
            rr = radius * 1.7
            x = cx + math.cos(a) * rr
            y = cy + math.sin(a) * rr
            self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline="")

        self.after(30, self._animate_avatar)

    def _drain_ui_queue(self) -> None:
        self.after(75, self._drain_ui_queue)

    def _close(self) -> None:
        self._closing = True
        self._voice_stop.set()
        print("JARJAR_HUD: close requested")
        self.destroy()


def run_hud(controller: HUDController) -> None:
    print("JARJAR_HUD: creating window")
    app = JarjarHUD(controller)
    app.update_idletasks()
    app.deiconify()
    app.lift()
    try:
        app.attributes("-topmost", True)
        app.after(1200, lambda: app.attributes("-topmost", False))
    except tk.TclError:
        pass
    print("JARJAR_HUD: entering mainloop")
    app.mainloop()
    print(f"JARJAR_HUD: mainloop returned closing={app._closing}")
    if not app._closing:
        raise RuntimeError("Jarjar HUD mainloop exited unexpectedly")
