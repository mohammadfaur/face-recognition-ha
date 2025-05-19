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

## ⚙️ Configuration (`config.json`)

```json
{
  "camera": {
    "rtsp_url": "rtsp://your-camera-stream",
    "timeout_sec": 5
  },
  "recognition": {
    "tolerance": 0.5
  },
  "home_assistant": {
    "base_url": "http://localhhost_of_HomeAsistant:8123",
    "token": "<LONG_LIVED_ACCESS_TOKEN>",
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

```yaml
shell_command:
  trigger_face_recognition: ssh -i /config/ssh/id_rsa -o 'StrictHostKeyChecking=no' username@192.168.50.124 'sudo /bin/systemctl start face_recognition.service'
```

Ensure key is copied:

```bash
ssh-copy-id -i /config/ssh/id_rsa.pub username@192.168.50.124
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

```bash
sudo systemctl daemon-reexec
sudo systemctl enable face_recognition.service
```

---

## 🚧 Samba Shared Folder Permissions

Ensure:

* The folder `ha_tmp_share` is shared via Home Assistant (`/config/www/tmp`)
* It's mounted on Ubuntu with read/write access by `username`
* You can delete the video file from Ubuntu within 30 seconds

---

## 📅 Timeline

* 10s warm-up delay after HA triggers
* 10s video capture
* Notification and video sent to HA
* `unknown_latest.mp4` deleted after 30 seconds

---

## 🤝 Credits

* Dlib + face\_recognition
* OpenCV + PIL
* Home Assistant + Telegram
* Project built with love by Mohammad + GPT :)
