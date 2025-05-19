import cv2
import face_recognition
import json
import time
import os
import pickle
import numpy as np
from datetime import datetime
from PIL import Image
from ha_integration import send_to_home_assistant
import threading
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
RTSP_URL = os.getenv("RTSP_URL")
USERNAME = os.getenv("USERNAME")

# === Load configuration ===
with open("config.json", "r") as f:
    config = json.load(f)

ENCODINGS_PATH = f"/home/{USERNAME}/face_project/encodings/faces.pkl"
UNKNOWN_OUTPUT = f"/home/{USERNAME}/face_project/ha_tmp_share"
TOLERANCE = config["recognition"]["tolerance"]
FPS = config.get("video", {}).get("fps", 10)
CODEC = config.get("video", {}).get("codec", "mp4v")
DURATION = 10  # seconds to record video

# === Load known encodings ===
if not os.path.exists(ENCODINGS_PATH):
    print("❌ No encodings file found. Please run add_known_face.py first.")
    exit(1)

with open(ENCODINGS_PATH, "rb") as f:
    data = pickle.load(f)
known_encodings = data["encodings"]
known_names = data["names"]

# === Simulate HA-trigger delay ===
time.sleep(10)

# === Connect to RTSP ===
print("🎥 Connecting to RTSP stream...")
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_FPS, FPS)

if not cap.isOpened():
    print("❌ Failed to connect to the RTSP stream.")
    exit(1)

# === Warm-up stream ===
print("📹 Warming up stream (discarding initial noisy frames)...")
for _ in range(15):
    cap.read()
    time.sleep(1 / FPS)

# === Capture frames ===
print("📹 Capturing frames...")
frames = []
frame_count = int(FPS * DURATION)
for _ in range(frame_count):
    ret, frame = cap.read()
    if ret:
        frame = cv2.GaussianBlur(frame, (3, 3), 0)  # Slight blur to reduce artifacts
        frames.append(frame)
    time.sleep(1 / FPS)
cap.release()

if not frames:
    print("❌ No frames captured from stream.")
    send_to_home_assistant(config, "no_face")
    exit(0)

# === Pick mid-frame for face recognition ===
frame = frames[len(frames) // 2]
rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
rgb_image = Image.fromarray(rgb).convert("RGB")
rgb_array = np.ascontiguousarray(np.asarray(rgb_image, dtype=np.uint8))

print(f"🔍 Final image: dtype={rgb_array.dtype}, shape={rgb_array.shape}, contiguous={rgb_array.flags['C_CONTIGUOUS']}")

encodings = face_recognition.face_encodings(rgb_array)

if not encodings:
    print("❌ No faces found in the frame.")
    send_to_home_assistant(config, "no_face")
    exit(0)

# === Check if face is known ===
for encoding in encodings:
    matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=TOLERANCE)
    if True in matches:
        name = known_names[matches.index(True)]
        print(f"✅ Recognized known face: {name}")
        send_to_home_assistant(config, "known")
        exit(0)

# === Schedule video deletion ===
def schedule_deletion(path, delay=50):
    def delete_later():
        print(f"⏳ Will attempt to delete video after {delay} seconds: {path}")
        time.sleep(delay)
        for attempt in range(3):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"🧹 Deleted video: {path}")
                    break
                except Exception as e:
                    print(f"❌ Attempt {attempt + 1}: Failed to delete {path} — {e}")
                    time.sleep(5)
            else:
                print(f"ℹ️ File already gone: {path}")
                break
    threading.Thread(target=delete_later, daemon=True).start()

# === Handle unknown face ===
print("❓ Unknown face detected. Saving video snippet...")
out_path = os.path.join(UNKNOWN_OUTPUT, "unknown_latest.mp4")

fourcc = cv2.VideoWriter_fourcc(*CODEC)
height, width = frames[0].shape[:2]
out = cv2.VideoWriter(out_path, fourcc, FPS, (width, height))
for f in frames:
    out.write(f)
out.release()

print(f"💾 Saved unknown face clip to: {out_path}")
send_to_home_assistant(config, "unknown", video_path=out_path)
schedule_deletion(out_path, delay=50)
