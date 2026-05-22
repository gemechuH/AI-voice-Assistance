import customtkinter as ctk
import asyncio
import edge_tts
import pygame
import time
import json
import os
import threading
import speech_recognition as sr
import re

ALARMS_FILE = "alarms.json"

def save_alarms(alarms):
    with open(ALARMS_FILE, "w") as f:
        json.dump(alarms, f)

def load_alarms():
    if os.path.exists(ALARMS_FILE):
        with open(ALARMS_FILE, "r") as f:
            return json.load(f)
    return []

VOICES = {
    "Jenny (Female)":      "en-US-JennyNeural",
    "Aria (Female)":       "en-US-AriaNeural",
    "Ava (Female)":        "en-US-AvaNeural",
    "Emma (Female)":       "en-US-EmmaNeural",
    "Michelle (Female)":   "en-US-MichelleNeural",
    "Andrew (Male)":       "en-US-AndrewNeural",
    "Brian (Male)":        "en-US-BrianNeural",
    "Christopher (Male)":  "en-US-ChristopherNeural",
    "Guy (Male)":          "en-US-GuyNeural",
    "Roger (Male)":        "en-US-RogerNeural",
}

async def speak(message, voice):
    communicate = edge_tts.Communicate(message, voice)
    await communicate.save("alarm.mp3")

def play_audio(volume=0.8):
    pygame.mixer.init()
    pygame.mixer.music.load("alarm.mp3")
    pygame.mixer.music.set_volume(volume)
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
        self.geometry("460x620")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.alarms = load_alarms()
        self.running = False
        self.stop_requested = False

        self.build_ui()
        self.refresh_list()

    def build_ui(self):
        # Title + clock side by side at top
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=15, pady=(12, 4))
        ctk.CTkLabel(top_frame, text="VOICE ALARM",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.clock_label = ctk.CTkLabel(top_frame, text="",
                                        font=ctk.CTkFont(size=18, weight="bold"),
                                        text_color="#3498db")
        self.clock_label.pack(side="right")
        self.update_clock()

        ctk.CTkFrame(self, height=1, fg_color="#444").pack(fill="x", padx=15, pady=4)

        # Row: Time + Voice
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=4)

        time_col = ctk.CTkFrame(row1, fg_color="transparent")
        time_col.pack(side="left")
        ctk.CTkLabel(time_col, text="Time", font=ctk.CTkFont(size=12)).pack(anchor="w")
        time_inner = ctk.CTkFrame(time_col, fg_color="transparent")
        time_inner.pack()

        hours = [f"{h:02d}" for h in range(1, 13)]
        minutes = [f"{m:02d}" for m in range(0, 60)]
        self.hour_var = ctk.StringVar(value="07")
        self.min_var = ctk.StringVar(value="00")
        self.ampm_var = ctk.StringVar(value="AM")

        ctk.CTkOptionMenu(time_inner, values=hours, variable=self.hour_var, width=60).pack(side="left", padx=2)
        ctk.CTkLabel(time_inner, text=":", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkOptionMenu(time_inner, values=minutes, variable=self.min_var, width=60).pack(side="left", padx=2)
        ctk.CTkOptionMenu(time_inner, values=["AM", "PM"], variable=self.ampm_var, width=65).pack(side="left", padx=2)

        voice_col = ctk.CTkFrame(row1, fg_color="transparent")
        voice_col.pack(side="right")
        ctk.CTkLabel(voice_col, text="Voice", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.voice_var = ctk.StringVar(value="Jenny (Female)")
        ctk.CTkOptionMenu(voice_col, values=list(VOICES.keys()),
                          variable=self.voice_var, width=170).pack()
        ctk.CTkButton(voice_col, text="Preview Voice", width=170, height=28,
                      fg_color="#8e44ad", hover_color="#6c3483",
                      command=self.preview_voice).pack(pady=(4, 0))

        # Row: Message + Add
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(row2, text="Message", font=ctk.CTkFont(size=12)).pack(anchor="w")
        msg_row = ctk.CTkFrame(row2, fg_color="transparent")
        msg_row.pack(fill="x")
        self.msg_entry = ctk.CTkEntry(msg_row, placeholder_text="Enter alarm message...")
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(msg_row, text="Add", width=70,
                      command=self.add_alarm).pack(side="right")

        ctk.CTkButton(row2, text="🎤  Set Alarm by Voice", width=320, height=32,
                      fg_color="#8e44ad", hover_color="#6c3483",
                      command=self.set_alarm_by_voice).pack(pady=(6, 0))
        self.heard_label = ctk.CTkLabel(row2, text="", font=ctk.CTkFont(size=11),
                                        text_color="#aaaaaa", wraplength=400)
        self.heard_label.pack(anchor="w", pady=(2, 0))

        # Alarm list
        ctk.CTkLabel(self, text="Your Alarms:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=15)
        self.listbox = ctk.CTkTextbox(self, height=120, state="disabled")
        self.listbox.pack(fill="x", padx=15, pady=4)

        # Volume slider
        vol_row = ctk.CTkFrame(self, fg_color="transparent")
        vol_row.pack(fill="x", padx=15, pady=(0, 4))
        ctk.CTkLabel(vol_row, text="Volume:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.volume_var = ctk.DoubleVar(value=0.8)
        ctk.CTkSlider(vol_row, from_=0, to=1, variable=self.volume_var,
                      width=200).pack(side="left", padx=8)
        self.vol_label = ctk.CTkLabel(vol_row, text="80%", font=ctk.CTkFont(size=12))
        self.vol_label.pack(side="left")
        self.volume_var.trace_add("write", self.update_vol_label)

        # Delete + status row
        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.pack(fill="x", padx=15, pady=4)
        ctk.CTkButton(row3, text="Delete Alarm", width=130,
                      fg_color="#c0392b", hover_color="#96281b",
                      command=self.delete_alarm).pack(side="left")
        self.status_label = ctk.CTkLabel(row3, text="", text_color="green",
                                         font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left", padx=10)

        ctk.CTkFrame(self, height=1, fg_color="#444").pack(fill="x", padx=15, pady=6)

        # Start + Stop buttons side by side
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 12))
        self.start_btn = ctk.CTkButton(btn_row, text="Start Alarms",
                                       fg_color="#27ae60", hover_color="#1e8449",
                                       command=self.start_alarms)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.stop_btn = ctk.CTkButton(btn_row, text="Stop Alarms",
                                      fg_color="#7f8c8d", hover_color="#616a6b",
                                      command=self.stop_alarms, state="disabled")
        self.stop_btn.pack(side="right", expand=True, fill="x", padx=(5, 0))

    def set_alarm_by_voice(self):
        self.set_status("Listening... speak now!", "orange")
        threading.Thread(target=self.listen_and_set, daemon=True).start()

    def listen_and_set(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=6)
            text = recognizer.recognize_google(audio).lower()
            self.heard_label.configure(text=f'Heard: "{text}"')
            self.after(100, lambda t=text: self.parse_voice_alarm(t))
        except sr.WaitTimeoutError:
            self.set_status("No speech detected. Try again.", "red")
        except sr.UnknownValueError:
            self.set_status("Could not understand. Try again.", "red")
        except sr.RequestError:
            self.set_status("Internet needed for voice recognition.", "red")

    def parse_voice_alarm(self, text):
        text = text.replace("a.m.", "am").replace("p.m.", "pm")
        text = text.replace("o'clock", "00").replace("oclock", "00")

        word_to_num = {
            "one": "1", "two": "2", "three": "3", "four": "4",
            "five": "5", "six": "6", "seven": "7", "eight": "8",
            "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
            "thirty": "30", "fifteen": "15", "forty five": "45",
            "forty": "40", "twenty": "20", "zero": "00",
        }
        for word, num in word_to_num.items():
            text = text.replace(word, num)

        hour, minute, ampm, end_pos = None, "00", None, 0

        # pattern 1: "9 30 pm" or "9:30 pm"
        m = re.search(r'(\d{1,2})[: ](\d{2})\s*(am|pm)', text)
        if m:
            hour, minute, ampm, end_pos = m.group(1), m.group(2), m.group(3).upper(), m.end()

        # pattern 2: "9 pm" or "9pm"
        if not hour:
            m = re.search(r'(\d{1,2})\s*(am|pm)', text)
            if m:
                hour, ampm, end_pos = m.group(1), m.group(2).upper(), m.end()

        if not hour:
            self.msg_entry.delete(0, "end")
            self.msg_entry.insert(0, text)
            self.set_status("No time found — edit message & click Add.", "orange")
            return

        converted = convert_to_24h(f"{hour}:{minute} {ampm}")
        message = text[end_pos:].strip() or "Alarm!"

        self.alarms.append((converted, message))
        save_alarms(self.alarms)
        self.refresh_list()
        self.set_status(f"Voice alarm set: {converted} — {message}", "green")

    def preview_voice(self):
        self.set_status("Previewing voice...", "orange")
        voice = VOICES[self.voice_var.get()]
        def run():
            asyncio.run(speak("Hello! This is a preview of your selected alarm voice.", voice))
            play_audio(self.volume_var.get())
            self.set_status("Preview done.", "green")
        threading.Thread(target=run, daemon=True).start()

    def update_vol_label(self, *args):
        pct = int(self.volume_var.get() * 100)
        self.vol_label.configure(text=f"{pct}%")

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
        self.stop_requested = False
        self.start_btn.configure(text="Running...", state="disabled")
        self.stop_btn.configure(state="normal", fg_color="#e74c3c", hover_color="#c0392b")
        self.set_status("Alarms are running...", "green")
        thread = threading.Thread(target=self.alarm_loop, daemon=True)
        thread.start()

    def stop_alarms(self):
        self.stop_requested = True
        self.set_status("Stopping alarms...", "orange")

    def show_snooze_popup(self, alarm_time, message):
        popup = ctk.CTkToplevel(self)
        popup.title("Alarm!")
        popup.geometry("320x220")
        popup.resizable(False, False)
        popup.grab_set()
        popup.lift()

        ctk.CTkLabel(popup, text="ALARM!", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#e74c3c").pack(pady=(20, 5))
        ctk.CTkLabel(popup, text=alarm_time, font=ctk.CTkFont(size=18)).pack()
        ctk.CTkLabel(popup, text=message, font=ctk.CTkFont(size=13),
                     wraplength=280).pack(pady=10)

        self.snooze_choice = None

        def on_snooze():
            self.snooze_choice = "snooze"
            popup.destroy()

        def on_dismiss():
            self.snooze_choice = "dismiss"
            popup.destroy()

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Snooze 5 min", width=130,
                      fg_color="#e67e22", hover_color="#ca6f1e",
                      command=on_snooze).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Dismiss", width=130,
                      fg_color="#c0392b", hover_color="#96281b",
                      command=on_dismiss).pack(side="left", padx=10)

        popup.wait_window()
        return self.snooze_choice

    def alarm_loop(self):
        remaining = self.alarms.copy()
        while remaining and not self.stop_requested:
            current_time = time.strftime("%H:%M")
            triggered = []
            for alarm_time, message in remaining:
                if current_time == alarm_time:
                    self.set_status(f"Alarm triggered: {alarm_time}", "yellow")
                    voice = VOICES[self.voice_var.get()]
                    asyncio.run(speak(message, voice))
                    play_audio(self.volume_var.get())
                    choice = self.show_snooze_popup(alarm_time, message)
                    if choice == "snooze":
                        snoozed = time.strptime(alarm_time, "%H:%M")
                        snoozed_minutes = snoozed.tm_hour * 60 + snoozed.tm_min + 5
                        new_hour = (snoozed_minutes // 60) % 24
                        new_min = snoozed_minutes % 60
                        new_time = f"{new_hour:02}:{new_min:02}"
                        remaining.append((new_time, message))
                        self.set_status(f"Snoozed until {new_time}", "orange")
                    triggered.append((alarm_time, message))
            for alarm in triggered:
                remaining.remove(alarm)
            time.sleep(10)

        self.running = False
        self.stop_requested = False
        self.start_btn.configure(text="Start Alarms", state="normal")
        self.stop_btn.configure(state="disabled", fg_color="#7f8c8d", hover_color="#616a6b")
        self.set_status("All alarms done!" if not self.stop_requested else "Alarms stopped.", "green")


app = AlarmApp()
app.mainloop()
