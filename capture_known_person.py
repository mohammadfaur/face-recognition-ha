#in terminal run: python capture_known_person.py Name
#this script store the entered Name as a folder in /known_faces
#run python add_known_face.py or use mange_faces.py
import os
import sys
import cv2
import time
import face_recognition
from dotenv import load_dotenv
from datetime import datetime
import subprocess


#test purposes
#time.sleep(10)

# === Load environment variables ===
load_dotenv()
RTSP_URL = os.getenv("RTSP_URL")
USERNAME = os.getenv("USERNAME")

# === Input Arguments ===
if len(sys.argv) < 2:
    print("❌ Usage: python capture_known_person.py <PersonName>")
    sys.exit(1)

person_name = sys.argv[1]
output_dir = f"/home/{USERNAME}/face_project/known_faces/{person_name}"
os.makedirs(output_dir, exist_ok=True)

# === File paths ===
video_path = "/tmp/capture_known.mp4"

# === Step 1: Use ffmpeg to capture 15 seconds of native RTSP video ===
print("🎥 Capturing 15 seconds of raw stream using ffmpeg...")
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-rtsp_transport", "tcp",
    "-i", RTSP_URL,
    "-t", "15",
    "-c", "copy",  # no re-encoding
    video_path
]

try:
    subprocess.run(ffmpeg_cmd, check=True)
except subprocess.CalledProcessError:
    print("❌ ffmpeg failed to capture stream.")
    sys.exit(1)

# === Step 2: Analyze video frame-by-frame ===
print("🧠 Extracting frames with faces...")
cap = cv2.VideoCapture(video_path)
saved = 0
frame_id = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb)

    if locations:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        out_path = os.path.join(output_dir, f"{timestamp}.jpg")
        cv2.imwrite(out_path, frame)
        saved += 1

    frame_id += 1

cap.release()
print(f"✅ Done. Saved {saved} frames with faces to: {output_dir}")
