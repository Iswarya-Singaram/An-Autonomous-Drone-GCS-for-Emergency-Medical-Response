# File: backend.py (Updated for Safety, Preview, and Video)
# Location: Save this in your project folder on the Raspberry Pi
# Description: The complete backend server with all requested features.

import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pymavlink import mavutil
import requests
import logging
from typing import List, Dict, Any

# --- CONFIGURATION ---
# Your API key is already included here.
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImNiN2UyNmNjZDZkNTQzMDc5NDUxMWE2ZWU4ZGQzZjNhIiwiaCI6Im11cm11cjY0In0="

PIXHAWK_CONNECTION_STRING = '/dev/serial0'
PIXHAWK_BAUD_RATE = 57600

# --- SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = FastAPI()
telemetry_data = {"lat": 0, "lon": 0, "alt": 0, "heading": 0, "groundspeed": 0, "mode": "UNKNOWN", "battery": 0, "sats": 0, "armed": False}
# This will store the detailed mission after a preview is generated
cached_mission_items = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
master = None

# --- MAVLINK COMMUNICATION & SAFETY ACTIONS ---

async def connect_to_pixhawk():
    global master
    while True:
        try:
            logging.info(f"Attempting to connect to Pixhawk at {PIXHAWK_CONNECTION_STRING}...")
            master = mavutil.mavlink_connection(PIXHAWK_CONNECTION_STRING, baud=PIXHAWK_BAUD_RATE, autoreconnect=True)
            master.wait_heartbeat()
            logging.info("Pixhawk heartbeat received! Connection established.")
            return
        except Exception as e:
            logging.error(f"Failed to connect to Pixhawk: {e}. Retrying in 5 seconds...")
            master = None
            await asyncio.sleep(5)

async def listen_to_pixhawk():
    global master
    while True:
        if not master:
            await asyncio.sleep(1)
            continue
        try:
            msg = master.recv_match(blocking=False)
            if not msg:
                await asyncio.sleep(0.01)
                continue
            msg_type = msg.get_type()
            if msg_type == 'GLOBAL_POSITION_INT':
                telemetry_data.update({'lat': msg.lat / 1e7, 'lon': msg.lon / 1e7, 'alt': msg.relative_alt / 1000.0, 'heading': msg.hdg / 100.0})
            elif msg_type == 'VFR_HUD':
                telemetry_data['groundspeed'] = msg.groundspeed
            elif msg_type == 'HEARTBEAT':
                telemetry_data.update({'mode': mavutil.mode_string_v10(msg), 'armed': (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0})
            elif msg_type == 'SYS_STATUS':
                telemetry_data['battery'] = msg.voltage_battery
            elif msg_type == 'GPS_RAW_INT':
                telemetry_data['sats'] = msg.satellites_visible
        except Exception as e:
            logging.error(f"Error reading from Pixhawk: {e}")
            await asyncio.sleep(2)

async def broadcast_telemetry():
    while True:
        await manager.broadcast(json.dumps({"type": "telemetry", "payload": telemetry_data}))
        await asyncio.sleep(0.5)

async def handle_safety_command(websocket: WebSocket, command: str):
    if not master:
        await websocket.send_text(json.dumps({"type": "status", "message": "Error: Drone not connected"}))
        return
    try:
        if command == 'arm':
            logging.info("Sending ARM command...")
            master.arducopter_arm()
            await websocket.send_text(json.dumps({"type": "status", "message": "Arm command sent."}))
        elif command == 'disarm':
            logging.info("Sending DISARM command...")
            master.arducopter_disarm()
            await websocket.send_text(json.dumps({"type": "status", "message": "Disarm command sent."}))
        elif command == 'rtl':
            logging.info("Sending RTL command...")
            master.set_mode_rtl()
            await websocket.send_text(json.dumps({"type": "status", "message": "RTL command sent."}))
    except Exception as e:
        logging.error(f"Failed to send {command} command: {e}")
        await websocket.send_text(json.dumps({"type": "status", "message": f"Error sending {command} command."}))

# --- API ENDPOINTS ---

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(connect_to_pixhawk())
    await asyncio.sleep(2)
    asyncio.create_task(listen_to_pixhawk())
    asyncio.create_task(broadcast_telemetry())

@app.get("/")
async def get():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message['type']
            
            if msg_type in ['arm', 'disarm', 'rtl']:
                await handle_safety_command(websocket, msg_type)
            elif msg_type == 'preview_path':
                await handle_preview_mission(websocket, message['payload'])
            elif msg_type == 'upload_mission':
                await handle_upload_mission(websocket)
            elif msg_type == 'execute_mission':
                await handle_execute_mission(websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- MISSION HANDLING LOGIC ---

async def get_road_path(start_coords, end_coords):
    headers = {'Authorization': ORS_API_KEY, 'Content-Type': 'application/json'}
    body = {'coordinates': [[start_coords['lon'], start_coords['lat']], [end_coords['lon'], end_coords['lat']]]}
    try:
        response = requests.post('https://api.openrouteservice.org/v2/directions/driving-car/geojson', json=body, headers=headers)
        response.raise_for_status()
        route_data = response.json()
        return route_data['features'][0]['geometry']['coordinates']
    except requests.exceptions.RequestException as e:
        logging.error(f"ORS API request failed: {e}")
        return None

async def handle_preview_mission(websocket: WebSocket, payload: Dict[str, Any]):
    """Generates the detailed mission and sends the path back for preview."""
    global cached_mission_items
    cached_mission_items = [] # Clear previous cache
    
    mission_plan = payload['plan']
    current_location = payload['start_location']
    
    full_path_for_frontend = []
    last_location = current_location

    for item in mission_plan:
        cmd = item['command']
        if cmd == 'TAKEOFF':
            cached_mission_items.append({'command': mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 'alt': item['alt'], 'lat': 0, 'lon': 0})
        elif cmd == 'WAYPOINT':
            waypoint_dest = {'lat': item['lat'], 'lon': item['lon']}
            road_coords = await get_road_path(last_location, waypoint_dest)
            if road_coords:
                for lon, lat in road_coords:
                    cached_mission_items.append({'command': mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 'alt': item['alt'], 'lat': lat, 'lon': lon})
                    full_path_for_frontend.append([lat, lon])
                last_location = waypoint_dest
            else:
                await websocket.send_text(json.dumps({"type": "status", "message": "Could not calculate path."}))
                return
        elif cmd == 'LAND':
            cached_mission_items.append({'command': mavutil.mavlink.MAV_CMD_NAV_LAND, 'alt': 0, 'lat': last_location['lat'], 'lon': last_location['lon']})

    logging.info(f"Generated preview with {len(cached_mission_items)} items.")
    await websocket.send_text(json.dumps({"type": "mission_path_preview", "payload": {"full_path": full_path_for_frontend}}))

async def handle_upload_mission(websocket: WebSocket):
    """Uploads the cached mission to the Pixhawk."""
    if not master:
        await websocket.send_text(json.dumps({"type": "status", "message": "Error: Drone not connected"}))
        return
    if not cached_mission_items:
        await websocket.send_text(json.dumps({"type": "status", "message": "No mission preview has been generated."}))
        return

    logging.info(f"Uploading cached mission with {len(cached_mission_items)} items.")
    try:
        master.waypoint_clear_all_send()
        master.recv_match(type='MISSION_ACK', blocking=True)
        master.waypoint_count_send(len(cached_mission_items))
        
        for i, mission_item in enumerate(cached_mission_items):
            master.recv_match(type='MISSION_REQUEST', blocking=True)
            master.mav.mission_item_send(
                master.target_system, master.target_component, i,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mission_item['command'], 0, 1, 0, 0, 0, 0,
                mission_item['lat'], mission_item['lon'], mission_item['alt']
            )
        
        final_ack = master.recv_match(type='MISSION_ACK', blocking=True)
        if final_ack.type == 0:
            logging.info("Mission upload successful.")
            await websocket.send_text(json.dumps({"type": "mission_uploaded"}))
        else:
            logging.error(f"Mission upload failed with code: {final_ack.type}")
            await websocket.send_text(json.dumps({"type": "status", "message": f"Mission upload failed: {final_ack.type}"}))
    except Exception as e:
        logging.error(f"Error during mission upload: {e}")
        await websocket.send_text(json.dumps({"type": "status", "message": f"Error: {e}"}))

async def handle_execute_mission(websocket: WebSocket):
    """Commands the drone to switch to AUTO mode and start the mission."""
    if not master:
        await websocket.send_text(json.dumps({"type": "status", "message": "Error: Drone not connected"}))
        return
    try:
        logging.info("Setting mode to AUTO...")
        master.set_mode_auto()
        master.mav.command_long_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_CMD_MISSION_START,
            0, 0, 0, 0, 0, 0, 0, 0
        )
        logging.info("Mission start command sent.")
        await websocket.send_text(json.dumps({"type": "status", "message": "Executing mission..."}))
    except Exception as e:
        logging.error(f"Failed to execute mission: {e}")
        await websocket.send_text(json.dumps({"type": "status", "message": f"Error executing mission: {e}"}))
