import nuvo
import time

with nuvo.NUVO('COM3') as audio:
    audio.queryZone(2)
