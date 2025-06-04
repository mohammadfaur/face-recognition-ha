import os
import cv2
import json
import time
import pickle
import numpy as np
import subprocess
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv
from ha_integration import send_to_home_assistant
import face_recognition
import threading
from sklearn.cluster import DBSCAN

#test purposes
#time.sleep(7) 

# === Load environment variables ===
load_dotenv()
RTSP_URL = os.getenv("RTSP_URL")
USERNAME = os.getenv("USERNAME")

# === Load configuration ===
with open("config.json", "r") as f:
    config = json.load(f)

ENCODINGS_PATH = os.path.expandvars(config["paths"]["encodings"].replace("ENV_HOME", f"/home/{USERNAME}"))
UNKNOWN_OUTPUT = os.path.expandvars(config["paths"]["unknown_face_output"].replace("ENV_HOME", f"/home/{USERNAME}"))
TOLERANCE = config["recognition"]["tolerance"]
FPS = config["video"].get("fps", 8)
CODEC = config["video"].get("codec", "mp4v")
RESOLUTION = config["video"].get("resolution", None)
DURATION = 10  # seconds

# === Load known encodings ===
if not os.path.exists(ENCODINGS_PATH):
    print("❌ No encodings file found. Please run add_known_face.py first.")
    exit(1)

with open(ENCODINGS_PATH, "rb") as f:
    data = pickle.load(f)
known_encodings = data["encodings"]
known_names = data["names"]

print(f"🧠 Loaded {len(known_encodings)} known face encodings.")

# === Capture frames using FFmpeg ===
print("🎥 Capturing stream using FFmpeg...")
tmp_dir = "/tmp/ffmpeg_frames"
os.makedirs(tmp_dir, exist_ok=True)
for f in os.listdir(tmp_dir):
    os.remove(os.path.join(tmp_dir, f))

ffmpeg_cmd = [
    "ffmpeg", "-hide_banner", "-loglevel", "error",
    "-rtsp_transport", "tcp",
    "-i", RTSP_URL,
    "-t", str(DURATION),
    "-r", str(FPS),
    "-qscale:v", "2",
    "-f", "image2",
]
if RESOLUTION:
    ffmpeg_cmd += ["-s", RESOLUTION]
ffmpeg_cmd += [os.path.join(tmp_dir, "frame_%03d.jpg")]

try:
    subprocess.run(ffmpeg_cmd, check=True)
except subprocess.CalledProcessError:
    print("❌ FFmpeg failed to capture stream.")
    send_to_home_assistant(config, "no_face")
    exit(1)

frame_paths = sorted([os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.endswith(".jpg")])
if not frame_paths:
    print("❌ No frames captured.")
    send_to_home_assistant(config, "no_face")
    exit(0)

# === First Pass: Quick Scan for any known face ===
print("🔍 Quick scanning for known faces...")
detected_names = set()
mid_frame_path = frame_paths[len(frame_paths) // 2]

for idx, frame_path in enumerate(frame_paths):
    try:
        img = face_recognition.load_image_file(frame_path)
        encs = face_recognition.face_encodings(img)
#        print(f"📸 Frame {idx}: {len(encs)} face(s) found")
        for encoding in encs:
            matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=TOLERANCE)
            for i, match in enumerate(matches):
                if match:
                    detected_names.add(known_names[i])
        if detected_names:
            print(f"✅ Early known face(s) found: {detected_names}")
            break
    except Exception as e:
        print(f"⚠️ Failed reading {frame_path}: {e}")

# === Respond immediately if known face is found ===
if detected_names:
    print(f"📩 Updating input_boolean.known_face_detected (fast path)...")
    send_to_home_assistant(config, "known")

    def analyze_all():
        print("🔎 Detailed scan for input_text.last_known_person...")
        all_encodings = []
        name_labels = []

        for path in frame_paths:
            try:
                img = face_recognition.load_image_file(path)
                encs = face_recognition.face_encodings(img)
                for encoding in encs:
                    matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=TOLERANCE)
                    matched_names = [known_names[i] for i, match in enumerate(matches) if match]
                    if matched_names:
                        all_encodings.append(encoding)
                        name_labels.append(matched_names[0])
                    else:
                        all_encodings.append(encoding)
                        name_labels.append(None)
            except Exception as e:
                print(f"⚠️ Error in detailed analysis frame: {e}")

        if not all_encodings:
            send_to_home_assistant(config, "no_face")
            return

        # Cluster to remove duplicate faces of same person across frames
        clustering = DBSCAN(eps=0.6, min_samples=1, metric="euclidean").fit(all_encodings)
        unique_labels = set(clustering.labels_)
        known_clusters = set()
        unknown_clusters = 0

        for cluster_id in unique_labels:
            indices = [i for i, label in enumerate(clustering.labels_) if label == cluster_id]
            names_in_cluster = [name_labels[i] for i in indices if name_labels[i] is not None]
            if names_in_cluster:
                known_clusters.update(names_in_cluster)
            else:
                unknown_clusters += 1

        # Compose label
        sorted_names = sorted(known_clusters)
        if len(sorted_names) == 1:
            label = sorted_names[0]
        elif len(sorted_names) == 2:
            label = f"{sorted_names[0]} and {sorted_names[1]}"
        elif len(sorted_names) > 2:
            label = ", ".join(sorted_names[:-1]) + f" and {sorted_names[-1]}"
        else:
            label = ""

        if unknown_clusters:
            if label:
                label += f" and {unknown_clusters} unknown person{'s' if unknown_clusters > 1 else ''}"
            else:
                label = f"{unknown_clusters} unknown person{'s' if unknown_clusters > 1 else ''}"

        print(f"📝 Sending label to HA: {label}")
        send_to_home_assistant(config, "setText", name=label)

    t = threading.Thread(target=analyze_all)
    t.start()
    t.join()
    exit(0)

# === If no known face, check if any face at all ===
img = face_recognition.load_image_file(mid_frame_path)
encs = face_recognition.face_encodings(img)
if not encs:
    cv2.imwrite("/tmp/debug_frame.jpg", cv2.imread(mid_frame_path))
    print("🖼️ Saved debug frame: /tmp/debug_frame.jpg")
    print("❌ No faces found in frames.")
    send_to_home_assistant(config, "no_face")
    exit(0)

# === All are unknown, save video ===
print("❓ Unknown face(s) detected. Saving video snippet...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"unknown_{timestamp}.mp4"
out_path = os.path.join(UNKNOWN_OUTPUT, filename)

frame = cv2.imread(frame_paths[0])
height, width = frame.shape[:2]
fourcc = cv2.VideoWriter_fourcc(*CODEC)
out = cv2.VideoWriter(out_path, fourcc, FPS, (width, height))
for p in frame_paths:
    f = cv2.imread(p)
    if f is not None:
        out.write(f)
out.release()

print(f"💾 Saved unknown face clip to: {out_path}")

for i in range(5):
    if os.path.exists(out_path):
        print("✅ Confirmed video file exists.")
        break
    print(f"⏳ Waiting for file to appear ({i+1}/5)...")
    time.sleep(1)
else:
    print(f"❌ File did not appear: {out_path}")

send_to_home_assistant(config, "unknown", video_path=out_path)
