# detect_and_handle.py
import time
import cv2
import numpy as np
import face_recognition
import json
import requests
import os
import pickle
from datetime import datetime
from ha_integration import notify_no_person, notify_known_person, notify_unknown_person
from dotenv import load_dotenv

# === Load .env ===
load_dotenv()

RTSP_URL = os.getenv("RTSP_URL")
USERNAME = os.getenv("USERNAME")

# === Load config ===
with open("config.json") as f:
    config = json.load(f)

TOLERANCE = config["recognition"].get("tolerance", 0.5)
ENCODINGS_PATH = f"/home/{USERNAME}/face_project/encodings/faces.pkl"
TMP_VIDEO_PATH = f"/home/{USERNAME}/ha_tmp_share/unknown_latest.mp4"

# === Load Known Encodings ===
if not os.path.exists(ENCODINGS_PATH):
    known_encodings, known_names = [], []
else:
    with open(ENCODINGS_PATH, "rb") as f:
        data = pickle.load(f)
        known_encodings = data.get("encodings", [])
        known_names = data.get("names", [])

# === Open Stream ===
print("📡 Connecting to RTSP stream...")
cap = cv2.VideoCapture(RTSP_URL)

if not cap.isOpened():
    print("❌ Failed to open RTSP stream.")
    notify_no_person("Camera connection failed")
    cap.release()
    exit(1)

print("🎥 Stream opened. Capturing 3 seconds of frames...")
frames = []
start = time.time()

while time.time() - start < 3:
    ret, frame = cap.read()
    if ret:
        frames.append(frame)

cap.release()

if not frames:
    print("❌ No frames captured.")
    notify_no_person("No frames captured")
    exit(0)

# === Try to Detect Faces ===
found_face = False
found_known = False
matched_name = None

for frame in frames:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb)

    if not encodings:
        continue

    found_face = True
    for enc in encodings:
        matches = face_recognition.compare_faces(known_encodings, enc, tolerance=TOLERANCE)
        if True in matches:
            found_known = True
            matched_name = known_names[matches.index(True)]
            break
    if found_known:
        break

# === Notify HA ===
if not found_face:
    print("📭 No human detected.")
    notify_no_person("Motion detected but no human found")
elif found_known:
    print(f"✅ Known face detected: {matched_name}")
    notify_known_person(matched_name)
else:
    print("❓ Unknown face detected. Saving 3s video...")
    h, w = frames[0].shape[:2]
    out = cv2.VideoWriter(TMP_VIDEO_PATH, cv2.VideoWriter_fourcc(*"mp4v"), 10, (w, h))
    for f in frames:
        out.write(f)
    out.release()
    notify_unknown_person(TMP_VIDEO_PATH)

print("✅ Detection flow complete.")
