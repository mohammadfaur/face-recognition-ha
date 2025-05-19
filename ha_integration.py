import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("HA_BASE_URL")
TOKEN = os.getenv("HA_TOKEN")

def send_to_home_assistant(config, result, video_path=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    if result == "no_face":
        entity = config["home_assistant"].get("no_face_sensor", "")
        if entity:
            print("📩 Updating HA: no_face_detected ON")
            requests.post(f"{BASE_URL}/api/services/input_boolean/turn_on", headers=headers,
                          data=json.dumps({"entity_id": entity}))

    elif result == "known":
        entity = config["home_assistant"].get("known_face_sensor", "")
        if entity:
            print("📩 Updating HA: known_face_detected ON")
            requests.post(f"{BASE_URL}/api/services/input_boolean/turn_on", headers=headers,
                          data=json.dumps({"entity_id": entity}))

    elif result == "unknown":
        entity = config["home_assistant"].get("unknown_face_sensor", "")
        if entity:
            print("📩 Updating HA: unknown_face_detected ON")
            requests.post(f"{BASE_URL}/api/services/input_boolean/turn_on", headers=headers,
                          data=json.dumps({"entity_id": entity}))
        else:
            print("⚠️ Unknown face trigger skipped (no sensor set)")
