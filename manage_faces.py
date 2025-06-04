import os
import cv2
import pickle
import face_recognition
from dotenv import load_dotenv
import argparse
from collections import Counter

# === Load env ===
load_dotenv()
USERNAME = os.getenv("USERNAME") or os.getenv("USER")

if not USERNAME:
    print("❌ USERNAME not set in environment.")
    exit(1)

# === Paths ===
BASE_DIR = f"/home/{USERNAME}/face_project"
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
ENCODINGS_PATH = os.path.join(BASE_DIR, "encodings", "faces.pkl")

def encode_person(person_name):
    person_dir = os.path.join(KNOWN_FACES_DIR, person_name)
    if not os.path.isdir(person_dir):
        print(f"❌ No such person folder: {person_name}")
        return [], []

    encodings = []
    names = []
    print(f"👤 Adding person: {person_name}")

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

    return encodings, names

def load_encodings():
    if not os.path.exists(ENCODINGS_PATH):
        return [], []
    with open(ENCODINGS_PATH, "rb") as f:
        data = pickle.load(f)
        return data["encodings"], data["names"]

def save_encodings(encodings, names):
    os.makedirs(os.path.dirname(ENCODINGS_PATH), exist_ok=True)
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump({"encodings": encodings, "names": names}, f)
    print(f"💾 Saved {len(encodings)} encodings to {ENCODINGS_PATH}")

def remove_person(person_name):
    encodings, names = load_encodings()
    new_encodings = []
    new_names = []
    removed = 0

    for i, name in enumerate(names):
        if name != person_name:
            new_encodings.append(encodings[i])
            new_names.append(name)
        else:
            removed += 1

    if removed == 0:
        print(f"❗ No encodings found for '{person_name}'.")
    else:
        print(f"🗑️ Removed {removed} encodings for '{person_name}'.")

    save_encodings(new_encodings, new_names)

def add_all():
    all_encodings = []
    all_names = []
    for person in os.listdir(KNOWN_FACES_DIR):
        encs, nms = encode_person(person)
        all_encodings.extend(encs)
        all_names.extend(nms)
    save_encodings(all_encodings, all_names)

def add_person(person_name):
    encs, nms = encode_person(person_name)
    if not encs:
        print(f"❌ No encodings for {person_name}. Skipping.")
        return

    existing_encodings, existing_names = load_encodings()
    existing_encodings.extend(encs)
    existing_names.extend(nms)
    save_encodings(existing_encodings, existing_names)

def show_stats():
    if not os.path.exists(ENCODINGS_PATH):
        print("❌ faces.pkl does not exist.")
        return

    _, names = load_encodings()
    count = Counter(names)

    print("📊 Face Encoding Stats:")
    for name, qty in count.items():
        print(f"  - {name}: {qty} image(s)")
    print(f"👥 Total known persons: {len(count)}")
    print(f"🧠 Total encodings: {len(names)}")

def list_names():
    if not os.path.exists(ENCODINGS_PATH):
        print("❌ faces.pkl does not exist.")
        return

    _, names = load_encodings()
    persons = sorted(set(names))
    print("📇 Persons in faces.pkl:")
    for person in persons:
        print(f"  - {person}")

# === CLI ===
parser = argparse.ArgumentParser(description="Manage known face encodings")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--add-all", action="store_true", help="Bulk add all persons")
group.add_argument("--add", metavar="PERSON", help="Add one person")
group.add_argument("--remove", metavar="PERSON", help="Remove one person")
group.add_argument("--stats", action="store_true", help="Show stats from faces.pkl")
group.add_argument("--list", action="store_true", help="List all persons in faces.pkl")

args = parser.parse_args()

if args.add_all:
    add_all()
elif args.add:
    add_person(args.add)
elif args.remove:
    remove_person(args.remove)
elif args.stats:
    show_stats()
elif args.list:
    list_names()
