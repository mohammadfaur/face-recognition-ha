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

#test purposes
time.sleep(5) 

# === Load environment variables ===
load_dotenv()
RTSP_URL = os.getenv("RTSP_URL")
USERNAME = os.getenv("USERNAME")

# === Load configuration ===
with open("config.json", "r") as f:
    config = json.load(f)

ENCODINGS_PATH = f"/home/{USERNAME}/face_project/encodings/faces.pkl"
UNKNOWN_OUTPUT = f"/home/{USERNAME}/ha_tmp_share"
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

print(f"🧠 Loaded {len(known_encodings)} known face encodings.")

# === Connect to RTSP ===
print("🎥 Connecting to RTSP stream...")
cap = cv2.VideoCapture(RTSP_URL)
cap.set(cv2.CAP_PROP_FPS, FPS)

if not cap.isOpened():
    print("❌ Failed to connect to the RTSP stream.")
    send_to_home_assistant(config, "no_face")
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
        frames.append(frame)
    time.sleep(1 / FPS)
cap.release()

if not frames:
    print("❌ No frames captured from stream.")
    send_to_home_assistant(config, "no_face")
    exit(0)

print(f"🔍 Searching all frames for a visible face...")
found_face = False
for idx, frame in enumerate(frames):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    try:
        encodings = face_recognition.face_encodings(rgb)
        if encodings:
            found_face = True
            print(f"🔍 Found {len(encodings)} face encoding(s) in frame {idx}")
            break
    except Exception as e:
        print(f"⚠️ Frame {idx} failed face recognition: {e}")

if not found_face:
#####
    debug_path = "/tmp/debug_frame.jpg"
    cv2.imwrite(debug_path, frames[len(frames) // 2])
    print(f"🖼️ Saved debug frame to: {debug_path}")
####
    print("❌ No faces found in any captured frame.")
    send_to_home_assistant(config, "no_face")
    exit(0)

rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
Image.fromarray(rgb).save("/tmp/debug_mid_frame.png")

# === Ensure proper format ===
if rgb.dtype != np.uint8:
    rgb = rgb.astype(np.uint8)

if rgb.shape[2] == 4:
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGRA2RGB)
elif rgb.ndim != 3 or rgb.shape[2] != 3:
    print("❌ Invalid image format after conversion.")
    send_to_home_assistant(config, "no_face")
    exit(0)

# === Try face encoding ===
try:
    encodings = face_recognition.face_encodings(rgb)
    print(f"🔍 Found {len(encodings)} face encoding(s) in mid-frame")
except Exception as e:
    print(f"❌ face_recognition error: {e}")
    Image.fromarray(rgb).save("/tmp/face_encoding_error_frame.png")
    send_to_home_assistant(config, "no_face")
    exit(0)

if not encodings:
    print("❌ No faces found in the frame.")
    send_to_home_assistant(config, "no_face")
    exit(0)

# === Check if face is known ===
detected_names = set()
for encoding in encodings:
    matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=TOLERANCE)
    for i, match in enumerate(matches):
        if match:
            detected_names.add(known_names[i])

if detected_names:
    name_str = ", ".join(sorted(detected_names))
    print(f"✅ Recognized known face(s): {name_str}")
    send_to_home_assistant(config, "known", name=name_str)
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
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"unknown_{timestamp}.mp4"
out_path = os.path.join(UNKNOWN_OUTPUT, filename)

symlink_path = os.path.join(UNKNOWN_OUTPUT, "unknown_latest.mp4")


fourcc = cv2.VideoWriter_fourcc(*CODEC)
height, width = frames[0].shape[:2]
out = cv2.VideoWriter(out_path, fourcc, FPS, (width, height))
for f in frames:
    out.write(f)
out.release()
print(f"💾 Saved unknown face clip to: {out_path}")

# Create/replace symlink to point to latest
try:
    if os.path.islink(symlink_path) or os.path.exists(symlink_path):
        os.remove(symlink_path)
    os.symlink(filename, symlink_path)
    print(f"🔗 Updated symlink: {symlink_path} -> {filename}")
except Exception as e:
    print(f"⚠️ Failed to update symlink: {e}")

print(f"💾 Saved unknown face clip to: {out_path}")

# Wait up to 5 seconds for the file to appear (for network FS delays)
for i in range(5):
    if os.path.exists(out_path):
        print(f"✅ Confirmed video file exists.")
        break
    print(f"⏳ Waiting for file to appear ({i+1}/5)...")
    time.sleep(1)
else:
    print(f"❌ File did not appear: {out_path}")

send_to_home_assistant(config, "unknown", video_path=out_path)
schedule_deletion(out_path, delay=50)
