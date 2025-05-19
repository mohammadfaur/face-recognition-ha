import pickle
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

ENCODINGS_PATH = config["paths"]["encodings"]
TARGET_NAME = os.getenv("USERNAME")

# Load encodings
with open(ENCODINGS_PATH, "rb") as f:
    data = pickle.load(f)

encodings = data["encodings"]
names = data["names"]

# Filter out the target name
new_encodings = [enc for enc, name in zip(encodings, names) if name != TARGET_NAME]
new_names = [name for name in names if name != TARGET_NAME]

removed = len(names) - len(new_names)
if removed == 0:
    print(f"⚠️ No entry found for name: {TARGET_NAME}")
else:
    # Save updated data
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump({"encodings": new_encodings, "names": new_names}, f)
    print(f"✅ Removed {removed} encoding(s) labeled as '{TARGET_NAME}'")
