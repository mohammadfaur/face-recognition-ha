import face_recognition
import os
import pickle
import sys
import dlib
import json
from PIL import Image
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USERNAME = os.getenv("USERNAME")
ENCODINGS_PATH = f"/home/{USERNAME}/face_project/encodings/faces.pkl"
TMP_IMG = "/tmp/tmp_face.jpg"

def save_encoding(image_path, name):
    try:
        # Force PIL save as RGB JPEG
        pil = Image.open(image_path).convert("RGB")
        pil.save(TMP_IMG, "JPEG")

        # Use face_recognition loader instead of dlib
        image = face_recognition.load_image_file(TMP_IMG)

        print(f"📐 Final image shape: {image.shape}, dtype: {image.dtype}")

        encodings = face_recognition.face_encodings(image)
        if not encodings:
            print("❌ No face found in the image.")
            return

        encoding = encodings[0]

    except Exception as e:
        print(f"❌ face_recognition failed: {e}")
        return

    # Load or create encodings file
    if os.path.exists(ENCODINGS_PATH):
        with open(ENCODINGS_PATH, "rb") as f:
            data = pickle.load(f)
        known_encodings = data.get("encodings", [])
        known_names = data.get("names", [])
    else:
        known_encodings = []
        known_names = []

    known_encodings.append(encoding)
    known_names.append(name)

    os.makedirs(os.path.dirname(ENCODINGS_PATH), exist_ok=True)
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump({"encodings": known_encodings, "names": known_names}, f)

    print(f"✅ Successfully added '{name}' to known faces.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python add_known_face.py <image_path> <name>")
        sys.exit(1)

    image_path = sys.argv[1]
    name = sys.argv[2]

    save_encoding(image_path, name)
