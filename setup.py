"""
setup.py
------------
Desktop installer GUI for the Email Response Agent.

Inject  → copies agent files to AppData, writes config.json,
          registers a Windows Task Scheduler task to run on login,
          then starts the agent immediately.
Remove  → deletes the Task Scheduler task.

After injecting, this setup_app.py can be deleted.
The agent will continue running from AppData on every login.

Requirements:
    pip install customtkinter winotify
"""

import customtkinter as ctk
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import time

AGENT_EXE = "agent.exe"

#  Constants 

APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "EmailAgent"
TASK_NAME   = "EmailResponseAgent"


#  App

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SetupApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Email Response Agent")
        self.geometry("500x720")
        self.resizable(False, False)
        self._build_ui()
        self._check_injection_status()

    #  UI construction

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#363636", corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="Email Response Agent",
            font=ctk.CTkFont("Courier New", size=20, weight="bold"),
            text_color="#ffffff",
        ).pack(pady=(24, 4))

        ctk.CTkLabel(
            header,
            text="Watches your inbox. Reminds you what needs a reply.",
            font=ctk.CTkFont(size=12),
            text_color="#FFFFFF",
        ).pack(pady=(0, 20))

        # Scrollable form
        self.form = ctk.CTkScrollableFrame(self, width=460, height=440, fg_color="#363636")
        self.form.pack(padx=20, fill="x")

        # ── Credentials 
        self._section("Credentials")

        self.email_var    = ctk.StringVar()
        self.password_var = ctk.StringVar()
        self.groq_var     = ctk.StringVar()

        self._field("Gmail address",    self.email_var)
        self._field("Gmail app password", self.password_var, secret=True)
        self._field("Groq API key",     self.groq_var,     secret=True)

        # - Timing 
        self._section("Timing")

        self.days_threshold_var = ctk.StringVar(value="3")
        self.hours_interval_var = ctk.StringVar(value="8")

        self._field("Stop reminding after N days",   self.days_threshold_var)
        self._field("Remind every N hours",          self.hours_interval_var)

        # Toggles 
        self._section("Features")
        
        self.notif_var = ctk.BooleanVar(value=True)


        ctk.CTkSwitch(
            self.form,
            text="New email notifications",
            variable=self.notif_var,
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=6, padx=8)


        self.status_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            wraplength=440,
        ).pack(pady=(10, 0))


        self.btn_row = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_row.pack(pady=14, padx=20, fill="x")

        ctk.CTkButton(
            self.btn_row,
            text="Inject",
            fg_color="#3B89FF",
            hover_color="#2E59B6",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=46,
            command=self._inject,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            self.btn_row,
            text="Remove",
            fg_color="#b91c1c",
            hover_color="#7f1d1d",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=46,
            command=self._disinject,
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

    def _section(self, title):
        ctk.CTkLabel(
            self.form,
            text=title.upper(),
            font=ctk.CTkFont("Courier New", size=11, weight="bold"),
            text_color="#ffffff",
            anchor="w",
        ).pack(fill="x", pady=(16, 4), padx=8)

    def _field(self, label, var, secret=False):
        ctk.CTkLabel(
            self.form,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color="#ffffff",
            anchor="w",
        ).pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkEntry(
            self.form,
            textvariable=var,
            height=36,
            show="•" if secret else "",
            fg_color="#ffffff",
            border_color="#ffffff",
            text_color="#000000"
        ).pack(fill="x", padx=8)

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _build_config(self):
        return {
            "EMAIL":       self.email_var.get().strip(),
            "PASSWORD":    self.password_var.get().strip(),
            "groq_api_key": self.groq_var.get().strip(),
            "start_date":  datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "followup_reminders": {
                "enabled":        True,
                "days_threshold": int(self.days_threshold_var.get() or 3),
                "hours_intervals": int(self.hours_interval_var.get() or 8),
            },
            "new_email_notifications": {
                "enabled": self.notif_var.get(),
            },
        }

    def _inject(self):
        try:
            config = self._build_config()

            if not config["EMAIL"] or not config["PASSWORD"] or not config["groq_api_key"]:
                self._status("Please fill in all credentials.", "red")
                return

            APPDATA_DIR.mkdir(parents=True, exist_ok=True)

            # Extract agent.exe from inside the bundled exe
            if getattr(sys, "frozen", False):
                src = Path(sys._MEIPASS) / AGENT_EXE   # _MEIPASS is the dir, no .parent needed
            else:
                src = Path(__file__).parent / AGENT_EXE
            if not src.exists():
                self._status("agent.exe not found in bundle. Rebuild with PyInstaller.", "red")
                return

            shutil.copy(src, APPDATA_DIR / AGENT_EXE)

            # Write config
            with open(APPDATA_DIR / "config.json", "w") as f:
                json.dump(config, f, indent=2)

            # Task Scheduler points at agent.exe directly 
            agent_exe_path = str(APPDATA_DIR / AGENT_EXE)

            subprocess.run([
                "schtasks", "/create",
                "/tn", TASK_NAME,
                "/tr", f'"{agent_exe_path}"',
                "/sc", "onlogon",
                "/rl", "highest",
                "/f",
            ], check=True, capture_output=True)

            # Launch immediately
            subprocess.Popen(
                [agent_exe_path],
                cwd=str(APPDATA_DIR),
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            )

            self._status("Agent is running and will auto-start on every login...", "#ffffff")
            self._set_inject_enabled(False)

        except subprocess.CalledProcessError as e:
            self._status(f"Task Scheduler error: {e.stderr.decode()}", "red")
        except Exception as e:
            self._status(f"{e}", "red")

    def _disinject(self):
        try:
            # Kill the running agent
            subprocess.run(["taskkill", "/f", "/im", "agent.exe"], capture_output=True)
            time.sleep(1)

            # Remove Task Scheduler task
            subprocess.run(
                ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                capture_output=True,
            )

            # Delete everything in AppData folder
            if APPDATA_DIR.exists():
                shutil.rmtree(APPDATA_DIR)

            self._status("Agent removed successfully.", "#ffffff")
            self._status("Agent removed successfully.", "#ffffff")
            self._set_inject_enabled(True)

        except Exception as e:
            self._status(f"{e}", "red")

    def _check_injection_status(self):
        result = subprocess.run(
            ["schtasks", "/query", "/tn", TASK_NAME],
            capture_output=True,
        )
        if result.returncode == 0:
            self._status("Agent is already running. Remove it before injecting again.", "#ffffff")
            self._set_inject_enabled(False)
        else:
            self._status("Agent is not injected yet.", "#ffffff")
            self._set_inject_enabled(True)

    def _set_inject_enabled(self, enabled: bool):
        for widget in self.btn_row.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "Inject":
                widget.configure(state="normal" if enabled else "disabled")
                break

    def _status(self, msg, color="#ffffff"):
        self.status_var.set(msg)
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkLabel) and widget.cget("textvariable") == str(self.status_var):
                widget.configure(text_color=color)
                break
        # Simpler: just configure by reference
        self._status_color = color
        self.update_idletasks()


if __name__ == "__main__":
    app = SetupApp()
    app.mainloop()