# 🧠 Face Recognition Triggered by Motion (Home Assistant Integration)

This project connects an RTSP-based camera to a face recognition system triggered by Home Assistant. Based on recognition results, it triggers appropriate HA automations like unlocking gates, sending Telegram alerts, or saving video clips.

---

## 📁 Project Layout

```
face_project/
├── manage_faces.py               # CLI tool to manage faces
├── add_known_face.py             # (legacy) Add a known person's face manually
├── detect_face.py                # Triggered by Home Assistant to recognize faces
├── ha_integration.py             # Notifies HA (REST API)
├── config.json                   # All project configuration
├── known_faces/                  # JPEGs of known persons
├── encodings/                    # Encoded face DB (.pkl file)
├── ha_tmp_share/                 # Shared folder with HA (via Samba)
├── face_env/                     # Virtual environment
├── face_recognition.service      # systemd unit file for detection service
```

---

## 🛠️ Full Setup Instructions

Follow these steps to install and configure the system from scratch.

---

### 📟 1. Install System Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv build-essential cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev libboost-all-dev ffmpeg -y
```

> These are required for `face_recognition`, `opencv-python`, and video processing.

---

### 📁 2. Set Up Project Directory

```bash
cd ~
mkdir -p face_project/{known_faces,encodings}
mkdir -p /home/username/ha_tmp_share
cd face_project
```

Clone your project files or create them in this directory.

---

### 🐍 3. Create Virtual Environment

```bash
python3 -m venv face_env
source face_env/bin/activate
```

---

### 📦 4. Install Python Packages

```bash
pip install --upgrade pip
pip install face_recognition opencv-python pillow python-dotenv requests
```

If you face issues with `dlib`, install it manually or try:

```bash
pip install dlib --verbose
```

---

### 🔐 5. Create `.env` File

At the root of `face_project`, create a `.env` file:

```ini
RTSP_URL=rtsp://your-camera-url
HA_BASE_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_token
USERNAME=your_linux_username
HOME=/home/username
```

---

### ⚙️ 6. Configure `config.json`

Update `config.json` like so:

```json
{
  "camera": {
    "rtsp_url": "ENV_RTSP_URL",
    "timeout_sec": 5
  },
  "recognition": {
    "tolerance": 0.45,
    "min_frames": 3
  },
  "video": {
    "fps": 10,
    "codec": "mp4v"
  },
  "home_assistant": {
    "base_url": "ENV_HA_BASE_URL",
    "token": "ENV_HA_TOKEN",
    "known_face_sensor": "input_boolean.known_face_detected",
    "unknown_face_sensor": "input_boolean.unknown_face_detected",
    "no_face_sensor": "input_boolean.no_face_detected",
    "name_text_entity": "input_text.last_known_person",
    "latest_unknown_video_text": "input_text.latest_unknown_video"
  },
  "paths": {
    "face_db": "ENV_HOME/face_project/face_db",
    "encodings": "ENV_HOME/face_project/encodings/faces.pkl",
    "log_file": "ENV_HOME/face_project/logs/events.log",
    "unknown_face_output": "ENV_HOME/ha_tmp_share/",
    "known_faces": "ENV_HOME/face_project/known_faces"
  }
}
```

---

## 🧪 Manual Testing

```bash
source face_env/bin/activate
python detect_face.py
```

---

## 🚀 Home Assistant Setup

### 📂 Add to `configuration.yaml`

```yaml
sensor:
  - platform: template
    sensors:
      telegram_chat_id:
        friendly_name: "Chat ID"
        value_template: !secret telegram_chat_id
      telegram_token:
        friendly_name: "Telegram's Token"
        value_template: !secret Telegram_API_KEY

input_text:
  latest_unknown_video:
    name: Latest Unknown Video
    max: 100
  last_known_person:
    name: 'Last Known Person'

input_boolean:
  known_face_detected:
    name: Known Face Detected
    initial: off
    icon: mdi:account-check
  unknown_face_detected:
    name: Unknown Face Detected
    initial: off
    icon: mdi:account-off
  no_face_detected:
    name: No Face Detected
    initial: off
    icon: mdi:alert-octagon

shell_command:
  trigger_face_recognition: ssh -i /config/ssh/id_rsa -o 'StrictHostKeyChecking=no' username@192.168.xxx.xxx 'sudo /bin/systemctl start face_recognition.service'
  send_unknown_video_telegram: >
    bash /config/scripts/send_telegram.sh
    '{{ states.sensor.telegram_token.state }}'
    '{{ states.sensor.telegram_chat_id.state }}'
    '{{ states("input_text.latest_unknown_video") }}'
```

### 🔑 SSH Key Setup

Ensure SSH key is copied:

```bash
ssh-copy-id -i /config/ssh/id_rsa.pub username@192.168.xxx.xxx
```

---
## 🤖 Home Assistant Automations

### 1. 📸 Trigger Face Recognition on Motion

```yaml
- alias: faceRecognition project - Trigger Face Recognition on Motion
  trigger:
    - platform: state
      entity_id: input_boolean.motion_trigger_test
      to: 'on'
  action:
    - service: shell_command.trigger_face_recognition
    - delay: 3
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.motion_trigger_test
  mode: single
```

### 2. ❌ Alert on No Face Detected (False Alarm)

```yaml
- alias: faceRecognition project - Alert on no face (false alarm)
  trigger:
    - platform: state
      entity_id: input_boolean.no_face_detected
      to: 'on'
  action:
    - service: telegram_bot.send_message
      data:
        message: "📹 Motion detected but no person found (probably animal or wind)."
    - delay: 5
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.no_face_detected
  mode: single
```

### 3. 🕵️ Send Video for Unknown Face Detection

```yaml
- alias: faceRecognition project - Send video when unknown face is detected
  trigger:
    - platform: state
      entity_id: input_boolean.unknown_face_detected
      to: 'on'
  action:
    - service: shell_command.send_unknown_video_telegram
    - delay: 5
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.unknown_face_detected
  mode: single
```

### 4. 🔓 Unlock Gate for Known Face

```yaml
- alias: faceRecognition project - Unlock gate when known face is detected
  trigger:
    - platform: state
      entity_id: input_boolean.known_face_detected
      to: 'on'
  action:
    - service: switch.toggle
      target:
        entity_id: switch.entrancein_2
    - delay: 2
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.known_face_detected
  mode: single
```

### 5. 👋 Send Welcome Message to Telegram

```yaml
- alias: faceRecognition project - Send welcome message to telegram
  trigger:
    - platform: state
      entity_id: input_text.last_known_person
  condition:
    - condition: template
      value_template: >
        {{ not states('input_text.last_known_person') in ['Unknown', 'unknown', ''] }}
  action:
    - service: telegram_bot.send_message
      data:
        message: "Welcome {{ states('input_text.last_known_person') }}!"
    - service: input_text.set_value
      data:
        value: Unknown
      target:
        entity_id: input_text.last_known_person
  mode: single
```

---

## 🚧 systemd Setup (Ubuntu)

Create `face_recognition.service` in `/etc/systemd/system/`:

```ini
[Unit]
Description=Face recognition detection triggered by HA
After=network.target

[Service]
User=username
WorkingDirectory=/home/username/face_project
ExecStart=/home/username/face_project/face_env/bin/python detect_face.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reexec
sudo systemctl enable face_recognition.service
```

---

## 🧹 Samba Shared Folder Permissions

Ensure:

* The folder `ha_tmp_share` is shared via Home Assistant (`/config/www/tmp`)
* It's mounted on Ubuntu with read/write access by `username`
* You can delete the video file from Ubuntu within 30 seconds

---

### 📦 Mounting the Shared Folder on Ubuntu

Install required package:

```bash
sudo apt install cifs-utils -y
```

Create the mount point:

```bash
sudo mkdir -p /home/username/ha_tmp_share
```

Create a credentials file:

```bash
sudo nano /etc/samba_creds
```

Add the following:

```
username=homeassistant_user_in_samba_addon
password=your_password_in_samba_addon
```

Secure the credentials file:

```bash
sudo chmod 600 /etc/samba_creds
```

Mount the shared folder:

```bash
sudo mount -t cifs //homeassistant.local/config/www/tmp /home/username/ha_tmp_share -o credentials=/etc/samba_creds,uid=$(id -u),gid=$(id -g),rw,iocharset=utf8,file_mode=0775,dir_mode=0775
```

---

### 🔁 Auto-mount at Boot (via /etc/fstab)

Edit fstab:

```bash
sudo nano /etc/fstab
```

Add this line:

```fstab
//homeassistant.local/config/www/tmp  /home/username/ha_tmp_share  cifs  credentials=/etc/samba_creds,uid=1000,gid=1000,rw,iocharset=utf8,file_mode=0775,dir_mode=0775  0  0
```

Test it:

```bash
sudo umount /home/username/ha_tmp_share
sudo mount -a
```

---

## 👤 Face Encoding Management

Use `manage_faces.py` to manage known face encodings for your system.

### 🔧 Usage Examples

```bash
# Bulk add all persons in /known_faces/
python manage_faces.py --add-all

# Add a specific person (must have images in /known_faces/PERSON_NAME)
python manage_faces.py --add Adam

# Remove a specific person from faces.pkl
python manage_faces.py --remove Yourname

# Show encoding stats (how many encodings per person)
python manage_faces.py --stats

# List all persons currently in faces.pkl
python manage_faces.py --list
```

---

## 🗕️ Timeline

* \~5s warm-up delay after HA triggers
* \~10s video capture
* Notification and video sent to HA
* `unknown_latest.mp4` deleted after \~30 seconds

---

## 🤝 Credits

* Dlib + face\_recognition
* OpenCV + PIL
* Home Assistant + Telegram
* Project built with ❤️ by Mohammad + GPT :)
