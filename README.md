# 🧠 Face Recognition Triggered by Motion (Home Assistant Integration)

This project connects an RTSP-based camera to a face recognition system triggered by Home Assistant. Based on recognition results, it triggers appropriate HA automations like unlocking gates, sending Telegram alerts, or saving video clips.

---

## 📆 Project Layout

```
face_project/
├── add_known_face.py             # Add a known person's face
├── detect_face.py                # Triggered by Home Assistant to recognize faces
├── ha_integration.py             # Notifies HA (REST API)
├── config.json                   # All project configuration
├── ha_tmp_share/                 # Shared folder with HA (via Samba)
├── known_faces/                  # JPEGs of known persons
├── encodings/                    # Encoded face DB (.pkl file)
├── face_env/                     # Virtual environment
├── face_recognition.service      # systemd unit file for detection service
```

---

## 🛠️ Full Setup Instructions

Follow these steps to install and configure the system from scratch.

---

### 🧾 1. Install System Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv build-essential cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev libboost-all-dev ffmpeg -y
```

> These are required for `face_recognition`, `opencv-python`, and video processing.

---

### 📁 2. Set Up Project Directory

```bash
cd ~
mkdir -p face_project/{known_faces,encodings,ha_tmp_share}
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

If you face issues with `dlib`,install it manually or try:

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
    "tolerance": 0.5,
    "min_frames": 3
  },
  "home_assistant": {
    "base_url": "ENV_HA_BASE_URL",
    "token": "ENV_HA_TOKEN",
    "known_face_sensor": "input_boolean.known_face_detected",
    "unknown_face_endpoint": "/api/webhook/unknown_face",
    "no_face_sensor": "input_boolean.no_face_detected"
  },
  "paths": {
    "encodings": "./encodings/faces.pkl",
    "unknown_face_output": "./ha_tmp_share/unknown_latest.mp4"
  },
  "video": {
    "fps": 15,
    "codec": "mp4v",
    "duration": 10
  }
}
```

---

## 👤 Register New Faces

```bash
source face_env/bin/activate
python add_known_face.py /path/to/image.jpg name
```

---

## 🚮 Delete Face Entry

Currently manual:

* Remove face from `known_faces/`
* Rebuild the `faces.pkl` file by re-running registration.

---

## 🔄 Manual Testing

```bash
source face_env/bin/activate
python detect_face.py
```

---

## 🚀 Home Assistant Setup

### Shell Command (in `configuration.yaml`)

* replace username and 192.168.xxx.xxx by yours, (local device ip) 
```yaml
shell_command:
  trigger_face_recognition: ssh -i /config/ssh/id_rsa -o 'StrictHostKeyChecking=no' username@192.168.xxx.xxx 'sudo /bin/systemctl start face_recognition.service'
```

Ensure key is copied:

```bash
ssh-copy-id -i /config/ssh/id_rsa.pub username@192.168.xxx.xxx 
```

---

## 🧠 Home Assistant Automations

### Trigger on Motion

```yaml
- alias: faceRecogniction project - Trigger Face Recognition on Motion
  trigger:
    - platform: state
      entity_id: input_boolean.motion_trigger_test
      to: 'on'
  action:
    - service: shell_command.trigger_face_recognition
    - delay: '00:00:03'
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.motion_trigger_test
```

### No Face Detected

```yaml
- alias: faceRecogniction project - Alert on no face (false alarm)
  trigger:
    - platform: state
      entity_id: input_boolean.no_face_detected
      to: 'on'
  action:
    - service: telegram_bot.send_message
      data:
        message: "📹 Motion detected but no person found."
    - delay: '00:00:05'
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.no_face_detected
```

### Unknown Face (send video)

```yaml
- alias: faceRecogniction project - Send video when unknown face is detected
  trigger:
    - platform: state
      entity_id: input_boolean.unknown_face_detected
      to: 'on'
  action:
    - service: telegram_bot.send_video
      data:
        caption: "🚨 Unknown face detected!"
        file: /config/www/tmp/unknown_latest.mp4
    - delay: '00:00:05'
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.unknown_face_detected
```

### Known Face (Unlock Gate)

```yaml
- alias: faceRecogniction project - Unlock gate when known face is detected
  trigger:
    - platform: state
      entity_id: input_boolean.known_face_detected
      to: 'on'
  action:
    - service: switch.toggle
      target:
        entity_id: switch.entrancein_2
    - delay: '00:00:05'
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.known_face_detected
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

## 🧩 Samba Shared Folder Permissions

Ensure:

- The folder `ha_tmp_share` is shared via Home Assistant (`/config/www/tmp`)
- It's mounted on Ubuntu with read/write access by `username`
- You can delete the video file from Ubuntu within 30 seconds

---

### 📦 Mounting the Shared Folder on Ubuntu

Install required package:

```bash
sudo apt install cifs-utils -y
```

Create the mount point:

```bash
sudo mkdir -p /home/username/face_project/ha_tmp_share
```

Create a credentials file:

```bash
sudo nano /etc/samba_creds
```

Add the following (replace with your actual credentials):

```
username=homeassistant_user_in_samba_addon
password=your_password_in_samba_addon
```

Secure the credentials file:

```bash
sudo chmod 600 /etc/samba_creds
```

Mount the shared folder, change homeassistant.local with homeassistant local ip, and username with your os username

```bash
sudo mount -t cifs //homeassistant.local/config/www/tmp /home/username/face_project/ha_tmp_share -o credentials=/etc/samba_creds,uid=$(id -u),gid=$(id -g),rw,iocharset=utf8,file_mode=0775,dir_mode=0775
```

---

### 🔁 Auto-mount at Boot (via /etc/fstab)

Edit fstab:

```bash
sudo nano /etc/fstab
```

Add this line (edit paths and host accordingly):

```fstab
//homeassistant.local/config/www/tmp  /home/username/face_project/ha_tmp_share  cifs  credentials=/etc/samba_creds,uid=1000,gid=1000,rw,iocharset=utf8,file_mode=0775,dir_mode=0775  0  0
```

Test it works:

```bash
sudo umount /home/username/face_project/ha_tmp_share
sudo mount -a
```

Now the shared folder will auto-mount on reboot with the correct permissions.

Ensure:

- The folder `ha_tmp_share` is shared via Home Assistant (`/config/www/tmp`)
- It's mounted on Ubuntu with read/write access by `username`
- You can delete the video file from Ubuntu within 30 seconds

---

## 📅 Timeline

* 10s warm-up delay after HA triggers for test purposes
* 10s video capture
* Notification and video sent to HA
* `unknown_latest.mp4` deleted after 30 seconds

---

## 🤝 Credits

* Dlib + face\_recognition
* OpenCV + PIL
* Home Assistant + Telegram
* Project built with love by Mohammad + GPT :)