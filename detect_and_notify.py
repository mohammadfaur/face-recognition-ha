import cv2
import face_recognition
import json
import time
import os
import pickle
from datetime import datetime
from ha_integration import send_to_home_assistant
from dotenv import load_dotenv

# === Load .env variables ===
load_dotenv()
RTSP_URL = os.getenv("RTSP_URL")
USERNAME = os.getenv("USERNAME")

# === Load config ===
with open("config.json") as f:
    config = json.load(f)

ENCODINGS_PATH = f"/home/{USERNAME}/face_project/encodings/faces.pkl"
UNKNOWN_OUTPUT_PATH = f"/home/{USERNAME}/ha_tmp_share"
TOLERANCE = config["recognition"].get("tolerance", 0.5)
CAPTURE_DURATION = 3  # seconds to record for unknown

# === Load known faces ===
if os.path.exists(ENCODINGS_PATH):
    with open(ENCODINGS_PATH, "rb") as f:
        data = pickle.load(f)
        known_encodings = data.get("encodings", [])
        known_names = data.get("names", [])
else:
    known_encodings, known_names = [], []
    print("⚠️ No encodings found. Proceeding with empty DB.")

# === Triggered by Home Assistant ===
# print("🚨 Triggered by HA. Waiting 10s to stabilize camera...")
# time.sleep(10)

cap = cv2.VideoCapture(RTSP_URL)
if not cap.isOpened():
    print("❌ Could not open RTSP stream.")
    send_to_home_assistant(config, "no_face")
    exit(1)

print("📷 Reading frame...")
ret, frame = cap.read()
cap.release()

if not ret or frame is None:
    print("❌ Failed to read a frame.")
    send_to_home_assistant(config, "no_face")
    exit(1)

# Convert to RGB
rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
encodings = face_recognition.face_encodings(rgb)

if not encodings:
    print("🙈 No faces detected.")
    send_to_home_assistant(config, "no_face")
    exit(0)

# Assume one face max
encoding = encodings[0]
matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=TOLERANCE)

if True in matches:
    matched_name = known_names[matches.index(True)]
    print(f"✅ Known face: {matched_name}")
    send_to_home_assistant(config, "known")
else:
    print("❓ Unknown face detected. Recording 3 seconds from RTSP...")
    cap = cv2.VideoCapture(RTSP_URL)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(UNKNOWN_OUTPUT_PATH, f"unknown_{timestamp}.mp4")
    out = cv2.VideoWriter(out_path, fourcc, 10.0, (int(cap.get(3)), int(cap.get(4))))

    start = time.time()
    while time.time() - start < CAPTURE_DURATION:
        ret, frame = cap.read()
        if ret:
            out.write(frame)

    cap.release()
    out.release()
    print(f"💾 Saved unknown face video to {out_path}")
    send_to_home_assistant(config, "unknown", video_path=out_path)

print("✅ Done. Shutting down stream.")
