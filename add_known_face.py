import os
import cv2
import pickle
import face_recognition
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
USERNAME = os.getenv("USERNAME")

# === Paths ===
BASE_DIR = f"/home/{USERNAME}/face_project"
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
ENCODINGS_PATH = os.path.join(BASE_DIR, "encodings", "faces.pkl")

encodings = []
names = []

print("🧠 Scanning known_faces directory...")

# === Traverse each person folder ===
for person_name in os.listdir(KNOWN_FACES_DIR):
    person_dir = os.path.join(KNOWN_FACES_DIR, person_name)
    if not os.path.isdir(person_dir):
        continue

    print(f"👤 Processing person: {person_name}")
    for file_name in os.listdir(person_dir):
        img_path = os.path.join(person_dir, file_name)

        try:
            image = face_recognition.load_image_file(img_path)
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb)

            if not locations:
                print(f"❌ No face found in {file_name}, skipping.")
                continue

            encoding = face_recognition.face_encodings(rgb, known_face_locations=locations)[0]
            encodings.append(encoding)
            names.append(person_name)
            print(f"✅ Encoded face from {file_name}")

        except Exception as e:
            print(f"❌ Error processing {file_name}: {e}")

# === Save encodings to disk ===
if not encodings:
    print("❌ No encodings were generated. Aborting.")
else:
    os.makedirs(os.path.dirname(ENCODINGS_PATH), exist_ok=True)
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump({"encodings": encodings, "names": names}, f)
    print(f"💾 Saved {len(encodings)} face encodings to: {ENCODINGS_PATH}")
