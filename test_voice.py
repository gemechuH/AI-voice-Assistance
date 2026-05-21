import asyncio
import edge_tts

async def speak():
    communicate = edge_tts.Communicate("Hello! Your voice alarm is working.", "en-US-JennyNeural")
    await communicate.save("test.mp3")

asyncio.run(speak())
print("Audio saved! Now playing...")

import pygame
import time

pygame.mixer.init()
pygame.mixer.music.load("test.mp3")
pygame.mixer.music.play()

while pygame.mixer.music.get_busy():
    time.sleep(0.1)

print("Done!")
