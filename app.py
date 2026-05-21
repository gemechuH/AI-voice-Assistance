import customtkinter as ctk
import asyncio
import edge_tts
import pygame
import time
import json
import os
import threading

ALARMS_FILE = "alarms.json"

def save_alarms(alarms):
    with open(ALARMS_FILE, "w") as f:
        json.dump(alarms, f)

def load_alarms():
    if os.path.exists(ALARMS_FILE):
        with open(ALARMS_FILE, "r") as f:
            return json.load(f)
    return []

async def speak(message):
    communicate = edge_tts.Communicate(message, "en-US-JennyNeural")
    await communicate.save("alarm.mp3")

def play_audio():
    pygame.mixer.init()
    pygame.mixer.music.load("alarm.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    pygame.mixer.music.unload()
    pygame.mixer.quit()

def convert_to_24h(alarm_time):
    try:
        t = time.strptime(alarm_time, "%I:%M %p")
        return time.strftime("%H:%M", t)
    except ValueError:
        try:
            t = time.strptime(alarm_time, "%H:%M")
            return time.strftime("%H:%M", t)
        except ValueError:
            return None


class AlarmApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Voice Alarm System")
        self.geometry("420x620")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.alarms = load_alarms()
        self.running = False

        self.build_ui()
        self.refresh_list()

    def build_ui(self):
        ctk.CTkLabel(self, text="VOICE ALARM SYSTEM",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(20, 5))

        self.clock_label = ctk.CTkLabel(self, text="",
                                        font=ctk.CTkFont(size=36, weight="bold"),
                                        text_color="#3498db")
        self.clock_label.pack(pady=(0, 15))
        self.update_clock()

        ctk.CTkLabel(self, text="Set Alarm Time").pack()

        time_frame = ctk.CTkFrame(self, fg_color="transparent")
        time_frame.pack(pady=5)

        hours = [f"{h:02d}" for h in range(1, 13)]
        minutes = [f"{m:02d}" for m in range(0, 60)]

        self.hour_var = ctk.StringVar(value="07")
        self.min_var = ctk.StringVar(value="00")
        self.ampm_var = ctk.StringVar(value="AM")

        ctk.CTkOptionMenu(time_frame, values=hours, variable=self.hour_var, width=80).pack(side="left", padx=5)
        ctk.CTkLabel(time_frame, text=":", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkOptionMenu(time_frame, values=minutes, variable=self.min_var, width=80).pack(side="left", padx=5)
        ctk.CTkOptionMenu(time_frame, values=["AM", "PM"], variable=self.ampm_var, width=80).pack(side="left", padx=5)

        ctk.CTkLabel(self, text="Message").pack()
        self.msg_entry = ctk.CTkEntry(self, width=320, placeholder_text="Enter alarm message...")
        self.msg_entry.pack(pady=5)

        ctk.CTkButton(self, text="Add Alarm", width=320,
                      command=self.add_alarm).pack(pady=10)

        ctk.CTkLabel(self, text="Your Alarms:").pack()
        self.listbox = ctk.CTkTextbox(self, width=320, height=160, state="disabled")
        self.listbox.pack(pady=5)

        ctk.CTkButton(self, text="Delete Alarm", width=320,
                      fg_color="#c0392b", hover_color="#96281b",
                      command=self.delete_alarm).pack(pady=5)

        self.status_label = ctk.CTkLabel(self, text="", text_color="green")
        self.status_label.pack(pady=5)

        self.start_btn = ctk.CTkButton(self, text="Start Alarms", width=320,
                                       fg_color="#27ae60", hover_color="#1e8449",
                                       command=self.start_alarms)
        self.start_btn.pack(pady=10)

    def update_clock(self):
        current = time.strftime("%I:%M:%S %p")
        self.clock_label.configure(text=current)
        self.after(1000, self.update_clock)

    def add_alarm(self):
        message = self.msg_entry.get().strip()

        if not message:
            self.set_status("Please enter an alarm message.", "red")
            return

        alarm_time_str = f"{self.hour_var.get()}:{self.min_var.get()} {self.ampm_var.get()}"
        converted = convert_to_24h(alarm_time_str)

        self.alarms.append((converted, message))
        save_alarms(self.alarms)
        self.refresh_list()
        self.msg_entry.delete(0, "end")
        self.set_status(f"Alarm added: {converted} — {message}", "green")

    def refresh_list(self):
        self.listbox.configure(state="normal")
        self.listbox.delete("1.0", "end")
        if self.alarms:
            for i, (t, m) in enumerate(self.alarms, 1):
                self.listbox.insert("end", f"{i}.  {t}  —  {m}\n")
        else:
            self.listbox.insert("end", "No alarms set yet.")
        self.listbox.configure(state="disabled")

    def delete_alarm(self):
        if not self.alarms:
            self.set_status("No alarms to delete.", "red")
            return
        dialog = ctk.CTkInputDialog(text="Enter alarm number to delete:", title="Delete Alarm")
        num = dialog.get_input()
        try:
            num = int(num)
            removed = self.alarms.pop(num - 1)
            save_alarms(self.alarms)
            self.refresh_list()
            self.set_status(f"Deleted: {removed[0]} — {removed[1]}", "orange")
        except (ValueError, IndexError, TypeError):
            self.set_status("Invalid number.", "red")

    def set_status(self, message, color="green"):
        self.status_label.configure(text=message, text_color=color)

    def start_alarms(self):
        if not self.alarms:
            self.set_status("No alarms to start.", "red")
            return
        if self.running:
            self.set_status("Alarms already running.", "orange")
            return
        self.running = True
        self.start_btn.configure(text="Running...", state="disabled")
        self.set_status("Alarms are running...", "green")
        thread = threading.Thread(target=self.alarm_loop, daemon=True)
        thread.start()

    def alarm_loop(self):
        remaining = self.alarms.copy()
        while remaining:
            current_time = time.strftime("%H:%M")
            triggered = []
            for alarm_time, message in remaining:
                if current_time == alarm_time:
                    self.set_status(f"Alarm triggered: {alarm_time}", "yellow")
                    asyncio.run(speak(message))
                    play_audio()
                    triggered.append((alarm_time, message))
            for alarm in triggered:
                remaining.remove(alarm)
            time.sleep(10)

        self.running = False
        self.start_btn.configure(text="Start Alarms", state="normal")
        self.set_status("All alarms done!", "green")


app = AlarmApp()
app.mainloop()
