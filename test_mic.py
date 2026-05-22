import speech_recognition as sr

recognizer = sr.Recognizer()

print("Listening... speak now!")

with sr.Microphone() as source:
    recognizer.adjust_for_ambient_noise(source, duration=1)
    audio = recognizer.listen(source, timeout=5)

print("Processing...")

try:
    text = recognizer.recognize_google(audio)
    print(f"You said: {text}")
except sr.UnknownValueError:
    print("Could not understand audio.")
except sr.RequestError:
    print("Internet connection needed for Google STT.")
