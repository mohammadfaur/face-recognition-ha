import requests
import json
import os
from dotenv import load_dotenv
import time

load_dotenv()

BASE_URL = os.getenv("HA_BASE_URL")
TOKEN = os.getenv("HA_TOKEN")

def post_to_ha(service, payload):
    url = f"{BASE_URL}/api/services/{service}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    for attempt in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=5)
            if r.status_code == 200:
                return True
            else:
                print(f"⚠️ HA responded with status {r.status_code}: {r.text}")
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed to reach HA: {e}")
        time.sleep(2)

    print("❌ Failed to contact Home Assistant after 3 attempts.")
    return False

def send_to_home_assistant(config, result, video_path=None, name=None):
    if result == "no_face":
        entity = config["home_assistant"].get("no_face_sensor")
        if entity:
            print(f"📩 Turning ON: {entity}")
            post_to_ha("input_boolean/turn_on", {"entity_id": entity})

    elif result == "known":
        entity = config["home_assistant"].get("known_face_sensor")
#        name_entity = config["home_assistant"].get("name_text_entity")
        if entity:
            print(f"📩 Turning ON: {entity}")
            post_to_ha("input_boolean/turn_on", {"entity_id": entity})
#        if name_entity and name:
#            print(f"📩 Updating HA: {name_entity} = '{name}'")
#            post_to_ha("input_text/set_value", {"entity_id": name_entity, "value": name})

    elif result == "setText":
        name_entity = config["home_assistant"].get("name_text_entity")
        if name_entity and name:
            print(f"📩 Updating HA: {name_entity} = '{name}'")
            post_to_ha("input_text/set_value", {"entity_id": name_entity, "value": name})      

    elif result == "unknown":
        video_name_entity = config["home_assistant"].get("latest_unknown_video_text")
        filename = os.path.basename(video_path) if video_path else None
        if video_name_entity and filename:
            print(f"📝 Updating {video_name_entity} = '{filename}'")
            post_to_ha("input_text/set_value", {"entity_id": video_name_entity, "value": filename})

        entity = config["home_assistant"].get("unknown_face_sensor")
        if entity:
            print(f"📩 Turning ON: {entity}")
            post_to_ha("input_boolean/turn_on", {"entity_id": entity})
