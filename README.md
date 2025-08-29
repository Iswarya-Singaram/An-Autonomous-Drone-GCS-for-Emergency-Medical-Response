# An Autonomous Drone GCS for Emergency Medical Response

A web-based Ground Control Station (GCS) designed to dispatch a reconnaissance drone as a first responder to accident scenes, providing medical professionals with "eyes on the scene" for remote triage before an ambulance arrives.

---

<!-- Add your GCS interface screenshot here -->

<img width="1600" height="899" alt="image" src="https://github.com/user-attachments/assets/f44cb1dd-2547-43df-be1c-447cd13cdabd" />

*Fig: The AeroMed Rescue GCS Interface in Operation.*

---

## ✨ Key Features

-   **🌐 Web-Based GCS:** A fully responsive and platform-independent interface accessible from any device with a web browser.
-   **🗺️ Interactive Mission Planning:** Simply click on a map to set the patient's location and automatically generate an intelligent flight path along road networks.
-   **📹 Live Video Streaming:** A low-latency video feed from the drone's onboard camera for real-time patient assessment.
-   **📊 Real-Time Telemetry:** Live data streaming via WebSockets for critical flight information (altitude, speed, battery, GPS).
-   **🔒 Robust Safety Features:** Essential controls like **Arm**, **Disarm**, and **Return to Launch (RTL)** for complete operator control.
-   **🛰️ Onboard Intelligence:** The entire system is hosted on a Raspberry Pi 4 mounted on the drone, creating a self-contained unit.

---

<img width="1280" height="808" alt="image" src="https://github.com/user-attachments/assets/e106002a-c0e6-4a94-8d6e-f9b088af95d9" />


## 🚀 Tech Stack

-   **Backend:** Python, FastAPI, DroneKit, OpenCV
-   **Frontend:** HTML, CSS, JavaScript, Leaflet.js
-   **Communication:** WebSockets, MAVLink Protocol
-   **Hardware:** Raspberry Pi 4, Pixhawk 4

---

<img width="1016" height="1280" alt="image" src="https://github.com/user-attachments/assets/42ff8ebb-7045-4d01-87e3-1e6c08f0cafa" />


## 🛠️ Hardware Setup & Pin Connections

### 1. Pixhawk to Raspberry Pi Connection

This serial connection is the communication link between the flight controller and the onboard computer.

| Pixhawk (TELEM2) | Signal  | Raspberry Pi (GPIO) | Physical Pin # |
| :--------------- | :------ | :------------------ | :------------- |
| Pin 2 (TX)       | Transmit| GPIO 15 (RXD)       | Pin 10         |
| Pin 3 (RX)       | Receive | GPIO 14 (TXD)       | Pin 8          |
| Pin 6 (GND)      | Ground  | Ground              | Pin 6          |

<!-- Add your wiring diagram here -->
<img width="1092" height="569" alt="image" src="https://github.com/user-attachments/assets/34663db1-c4c5-443f-b907-68a734b7dd58" />

*Fig: Wiring diagram for the Pixhawk and Raspberry Pi.*

### 2. Power System (Buck Converter)

A buck converter (LM2596) is used to step down the drone's battery voltage to provide a stable 5V to the Raspberry Pi.

| Source              | Buck Converter | Destination                  |
| :------------------ | :------------- | :--------------------------- |
| PDB VCC (Battery +) | IN+            | -                            |
| PDB GND (Battery -) | IN-            | -                            |
| -                   | OUT+           | Raspberry Pi 5V (Pin 2 or 4) |
| -                   | OUT-           | Raspberry Pi GND (Pin 6)     |

<!-- Add your power system diagram here -->
<img width="897" height="672" alt="image" src="https://github.com/user-attachments/assets/6f0c56f8-b8d6-4e52-8758-785a24791f76" />

*Fig: Wiring diagram for the power system.*

---

## 🎥 Demonstration

<!-- Add a link to your project demo video here -->
https://drive.google.com/file/d/1m0giZ5LuGIBBDrSzM_qQ9kbx6r65udKC/view?usp=drive_link
