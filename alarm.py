import asyncio
import edge_tts
import pygame
import time
import json
import os

ALARMS_FILE = "alarms.json"

def save_alarms(alarms):
    with open(ALARMS_FILE, "w") as f:
        json.dump(alarms, f)
    print("Alarms saved.")

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

def get_alarms_from_user():
    alarms = []
    print("\n--- Voice Alarm Setup ---")
    print("Enter time as  '1:34 PM' or '13:34'")
    while True:
        alarm_time = input("Enter alarm time or 'done' to finish: ")
        if alarm_time.lower() == "done":
            break
        converted = convert_to_24h(alarm_time)
        if not converted:
            print("Invalid time format. Try '1:34 PM' or '13:34'")
            continue
        message = input("Enter alarm message: ")
        alarms.append((converted, message))
        print(f"Alarm added: {converted} — {message}")
    return alarms

def run_alarms(alarms):
    print("\nAlarms set:")
    for alarm_time, message in alarms:
        print(f"  {alarm_time} — {message}")

    remaining = alarms.copy()

    while remaining:
        current_time = time.strftime("%H:%M")
        triggered = []

        for alarm_time, message in remaining:
            if current_time == alarm_time:
                print(f"\nAlarm triggered: {alarm_time}")
                asyncio.run(speak(message))
                play_audio()
                choice = input("Snooze 5 minutes? (y/n): ").strip().lower()
                if choice == "y":
                    snoozed = time.strptime(alarm_time, "%H:%M")
                    snoozed_minutes = snoozed.tm_hour * 60 + snoozed.tm_min + 2
                    new_hour = (snoozed_minutes // 60) % 24
                    new_min = snoozed_minutes % 60
                    new_time = f"{new_hour:02}:{new_min:02}"
                    print(f"Snoozed! Will ring again at {new_time}")
                    remaining.append((new_time, message))
                triggered.append((alarm_time, message))

        for alarm in triggered:
            remaining.remove(alarm)

        time.sleep(10)

    print("All alarms done!")


def show_menu():
    while True:
        print("\n=============================")
        print("     VOICE ALARM SYSTEM      ")
        print("=============================")
        print("1. Set new alarms")
        print("2. Load saved alarms")
        print("3. View saved alarms")
        print("4. Delete an alarm")
        print("5. Exit")
        print("=============================")
        choice = input("Choose an option (1-5): ").strip()

        if choice == "1":
            alarms = get_alarms_from_user()
            if alarms:
                save_alarms(alarms)
                run_alarms(alarms)

        elif choice == "2":
            alarms = load_alarms()
            if alarms:
                print(f"\nLoaded {len(alarms)} alarm(s).")
                run_alarms(alarms)
            else:
                print("No saved alarms found.")

        elif choice == "3":
            alarms = load_alarms()
            if alarms:
                print("\nSaved alarms:")
                for i, (t, m) in enumerate(alarms, 1):
                    print(f"  {i}. {t} — {m}")
            else:
                print("No saved alarms found.")

        elif choice == "4":
            alarms = load_alarms()
            if not alarms:
                print("No saved alarms to delete.")
                continue
            print("\nSaved alarms:")
            for i, (t, m) in enumerate(alarms, 1):
                print(f"  {i}. {t} — {m}")
            try:
                num = int(input("Enter number to delete: "))
                removed = alarms.pop(num - 1)
                save_alarms(alarms)
                print(f"Deleted: {removed[0]} — {removed[1]}")
            except (ValueError, IndexError):
                print("Invalid number.")

        elif choice == "5":
            print("Goodbye!")
            break

        else:
            print("Invalid option. Choose 1-5.")

show_menu()
