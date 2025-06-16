#!/usr/bin/env python3
"""
Web GUI for LED Test Controller
A FastAPI-based web interface that provides all the functionality of the controller
with an attractive, modern web interface.
"""

import os
import sys
import json
import time
import asyncio
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import subprocess
import io
import contextlib
from contextlib import asynccontextmanager

import serial
import serial.tools.list_ports
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Get the parent directory (deploy folder)
parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)

# Import the existing controller functionality
try:
    from controller.controller import LEDTestController
except ImportError:
    print("Warning: Could not import LEDTestController. Some features may not work.")
    LEDTestController = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - sets up event loop on startup"""
    global main_event_loop
    
    # Startup
    main_event_loop = asyncio.get_event_loop()
    print("🚀 Web server started - ready for connections")  # Use print instead of add_console_message to avoid circular reference
    
    yield
    
    # Shutdown (if needed)
    pass

app = FastAPI(title="LED Test Controller - Web GUI", version="1.0.0", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
detection_server_process: Optional[subprocess.Popen] = None
controller_instance: Optional[LEDTestController] = None
controller_thread: Optional[threading.Thread] = None
server_status = {"running": False, "cameras_connected": 0}
test_status = {"running": False, "current_step": "", "awaiting_input": False, "input_prompt": "", "input_type": "buttons"}
console_messages = deque(maxlen=1000)  # Store last 1000 console messages
current_user_response = None
response_ready = threading.Event()
main_event_loop = None

# Request/Response models
class TestStartRequest(BaseModel):
    com_port: str
    test_program: str = "1340_test_led_automated_correct.py"
    server_url: str = "http://localhost:8000"
    username: str = "hsvroot"
    password: str = "BOSCO"

class UserResponseRequest(BaseModel):
    response: str

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"WebSocket error for {connection}: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

def add_console_message(message: str, message_type: str = "info"):
    """Add a message to the console with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    console_entry = {
        "timestamp": timestamp,
        "message": message,
        "type": message_type
    }
    console_messages.append(console_entry)
    
    # Print to original stdout for debugging
    print(f"[{timestamp}] {message}")
    
    # Try multiple approaches to broadcast to WebSockets
    try:
        # Approach 1: Use main_event_loop if available
        if main_event_loop and not main_event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(manager.broadcast({
                "type": "console_message",
                "data": console_entry
            }), main_event_loop)
            return
            
        # Approach 2: Try to get current running loop
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(manager.broadcast({
                "type": "console_message",
                "data": console_entry
            }))
            return
        except RuntimeError:
            pass
            
        # Approach 3: Try to get any event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(manager.broadcast({
                    "type": "console_message",
                    "data": console_entry
                }), loop)
        except:
            pass
            
    except Exception as e:
        print(f"WebSocket broadcast error (message still logged): {e}")

def update_test_status(running: bool, step: str = "", awaiting_input: bool = False, input_prompt: str = "", input_type: str = "buttons"):
    """Update the test status and broadcast to websockets"""
    global test_status
    test_status.update({
        "running": running,
        "current_step": step,
        "awaiting_input": awaiting_input,
        "input_prompt": input_prompt,
        "input_type": input_type
    })
    
    # Broadcast to all connected websockets - handle event loop gracefully
    try:
        if main_event_loop and not main_event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(manager.broadcast({
                "type": "test_status",
                "data": test_status
            }), main_event_loop)
        else:
            # Try to get current event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(manager.broadcast({
                        "type": "test_status",
                        "data": test_status
                    }))
            except:
                pass  # Silently ignore if no event loop available
    except Exception as e:
        print(f"Error in update_test_status: {e}")

def update_server_status():
    """Update server status by checking if the detection server is responding"""
    global server_status
    try:
        response = requests.get("http://localhost:8000/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            # If server is running and has camera frames, both cameras are working
            # If no frames, server failed to initialize cameras properly
            cameras_connected = data.get("cameras_connected", 0)
            if cameras_connected > 0:
                # Server is running with camera feed = both cameras working
                server_status = {"running": True, "cameras_connected": 2}
            else:
                # Server running but no camera feed = cameras failed, needs restart
                server_status = {"running": False, "cameras_connected": 0}
        else:
            server_status = {"running": False, "cameras_connected": 0}
    except:
        server_status = {"running": False, "cameras_connected": 0}
    
    # Broadcast to all connected websockets - handle event loop gracefully
    try:
        if main_event_loop and not main_event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(manager.broadcast({
                "type": "server_status",
                "data": server_status
            }), main_event_loop)
        else:
            # Try to get current event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(manager.broadcast({
                        "type": "server_status",
                        "data": server_status
                    }))
            except:
                pass  # Silently ignore if no event loop available
    except Exception as e:
        print(f"Error in update_server_status: {e}")

class ModernLEDTestController(LEDTestController):
    """Extended controller with web interface integration - USING EXACT METHODS from working controller.py"""
    
    def __init__(self, port="COM13", baudrate=115200, server_url="http://localhost:8000", test_program="1340_test_led_automated_correct.py", username="hsvroot", password="BOSCO"):
        super().__init__(port, baudrate, server_url)
        self.web_enabled = True
        self.test_program = test_program
        self.username = username
        self.password = password
    
    def send_command(self, command, wait_time=2):
        """Send command to serial and wait - EXACT COPY from working controller.py"""
        if self.serial_conn:
            print(f"Sending: {command}")
            add_console_message(f"Sending: {command}", "info")  # Also add to web console
            self.serial_conn.write(command.encode('utf-8') + b'\r\n')
            self.serial_conn.flush()
            time.sleep(wait_time)

    def read_serial_output(self, timeout=30):
        """Read serial output until timeout - SEND ALL DATA TO WEB CONSOLE"""
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.serial_conn.in_waiting > 0:
                try:
                    data = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')
                    output += data
                    print(data, end='', flush=True)  # Original behavior for terminal
                    
                    # Send ALL raw data to web interface immediately - exactly as received
                    if data:
                        # Send the raw data directly to web console, preserving formatting
                        raw_lines = data.replace('\r\n', '\n').split('\n')
                        for line in raw_lines:
                            if line.strip():  # Only send non-empty lines
                                add_console_message(line, "device")  # Use "device" type to distinguish from system messages
                    
                    # Check for specific prompts - respond quickly
                    if any(prompt in output.lower() for prompt in [
                        "login:", "password:", "[yes/no/skip]:", "[yes/no/skip/exit]:"
                    ]):
                        time.sleep(0.2)  # Just brief wait for complete prompt
                        break
                    
                    # Quick break for shell prompts to avoid delays
                    if "[root@SDX6330 ~]#" in output:
                        time.sleep(0.1)  # Very short wait for shell
                        break
                        
                except Exception as e:
                    print(f"Error reading serial: {e}")
                    add_console_message(f"Error reading serial: {e}", "error")
                    break
            time.sleep(0.05)  # Shorter sleep for more responsive reading
        
        return output

    def login_to_device(self):
        """Login to the Linux device with device booting detection"""
        add_console_message("🔄 Initiating login process...", "info")
        
        # Check if device is booting by looking for boot messages
        max_boot_wait = 300  # Wait up to 5 minutes for boot (increased from 2 minutes)
        boot_start_time = time.time()
        
        while time.time() - boot_start_time < max_boot_wait:
            # Send enter to trigger response
            self.send_command("")
            output = self.read_serial_output(10)
            add_console_message(f"Device response: {output.strip()}", "info")
            
            # Check for boot messages
            boot_indicators = ["booting", "starting", "loading", "init", "systemd", "kernel"]
            if any(indicator in output.lower() for indicator in boot_indicators):
                add_console_message("🔄 Device is booting... waiting for completion", "warning")
                time.sleep(10)
                continue
            
            # Check if already logged in (shell prompt)
            if any(prompt in output for prompt in ["#", "$", "root@"]):
                add_console_message("✅ Device already logged in", "success")
                return True
            
            # Check for login prompt
            if "login:" in output.lower():
                add_console_message(f"📝 Sending username: {self.username}", "info")
                self.send_command(self.username)
                output = self.read_serial_output(10)
                add_console_message(f"After username: {output.strip()}", "info")
                
                # Send password if prompted
                if "password:" in output.lower():
                    add_console_message("🔐 Sending password...", "info")
                    self.send_command(self.password)
                    output = self.read_serial_output(15)
                    add_console_message(f"After password: {output.strip()}", "info")
                    
                    # Check if login failed
                    if "incorrect" in output.lower() or "login:" in output.lower():
                        add_console_message("❌ Login failed - incorrect credentials", "error")
                        return False
                
                # Wait for shell prompt
                add_console_message("⏳ Waiting for shell prompt...", "info")
                time.sleep(5)
                
                # Test shell access
                self.send_command("echo 'login_test'", 2)
                test_output = self.read_serial_output(5)
                add_console_message(f"Shell test: {test_output.strip()}", "info")
                
                if "login_test" in test_output or "#" in test_output:
                    add_console_message("✅ Login successful - shell is ready", "success")
                    return True
                else:
                    add_console_message("⚠️ Shell access unclear, retrying...", "warning")
                    time.sleep(5)
                    continue
            
            # If no clear response, device might still be booting
            if not output.strip():
                add_console_message("⏳ No response from device, waiting...", "warning")
                time.sleep(5)
                continue
            
            # Unknown state, wait and retry
            add_console_message("❓ Unknown device state, retrying...", "warning")
            time.sleep(5)
        
        # Timeout reached
        add_console_message("❌ Login timeout after 5 minutes - device may need manual intervention", "error")
        add_console_message("💡 Try: Check device power, USB connection, or restart the device", "warning")
        return False

    def setup_and_run_test(self):
        """Setup USB mount and run the LED test script - EXACT COPY from working controller.py"""
        print("Setting up USB and running LED test...")
        add_console_message("Setting up USB and running LED test...", "info")
        
        # Create USB directory
        self.send_command("mkdir usb", 2)
        
        # Mount USB
        self.send_command("mount /dev/sdb1 ./usb", 3)
        
        # Run the LED test script - use the test program from GUI
        test_command = f"python usb/{self.test_program}"
        add_console_message(f"Running test program: {self.test_program}", "info")
        self.send_command(test_command, 5)
        
        return True

    def run_automated_test_web(self):
        """Run the automated test with web interface integration"""
        try:
            # Clear console for new test
            global console_messages
            console_messages.clear()
            
            # Broadcast console clear to all connected clients
            try:
                if main_event_loop and not main_event_loop.is_closed():
                    asyncio.run_coroutine_threadsafe(manager.broadcast({
                        "type": "console_clear"
                    }), main_event_loop)
            except Exception as e:
                print(f"Error broadcasting console clear: {e}")
            
            add_console_message("🚀 Starting New LED Test Session", "info")
            add_console_message("=" * 50, "info")
            update_test_status(True, "Initializing...", False, "")
            
            if not self.connect_serial():
                add_console_message("Failed to connect to serial port", "error")
                update_test_status(False, "Error - Serial connection failed", False, "")
                return False
            
            add_console_message(f"Connected to {self.port}", "success")
            update_test_status(True, "Connected to device", False, "")
            
            # Login to device
            update_test_status(True, "Logging into device...", False, "")
            if not self.login_to_device():
                add_console_message("Failed to login to device", "error")
                update_test_status(False, "Error - Login failed", False, "")
                return False
            
            add_console_message("Successfully logged into device", "success")
            
            # Setup and run test
            update_test_status(True, "Setting up USB and starting test...", False, "")
            if not self.setup_and_run_test():
                add_console_message("Failed to start test", "error")
                update_test_status(False, "Failed - Test startup error", False, "")
                return False
            
            add_console_message("Test started successfully", "success")
            
            # Monitor test execution
            test_output = ""
            failed_colors = []
            
            while True:
                update_test_status(True, "Running test - monitoring output...", False, "")
                output = self.read_serial_output(60)
                test_output += output
                
                # Extract serial number if found
                if not self.current_serial_number:
                    sn = self.extract_serial_number(output)
                    if sn:
                        self.current_serial_number = sn
                        add_console_message(f"🏷️ Detected Serial Number: {sn}", "success")
                
                # Handle LED color questions
                if "[yes/no/skip]:" in output.lower() or "[yes/no/skip/exit]:" in output.lower():
                    
                    if "are all the leds red?" in output.lower():
                        update_test_status(True, "🔴 RED LED CHECK", False, "")
                        add_console_message("=== 🔴 RED LED CHECK ===", "info")
                        add_console_message("🔍 Waiting for server to detect red LEDs...", "info")
                        
                        # Poll server until it detects red LEDs, then save image immediately
                        max_attempts = 30  # 30 seconds max
                        for attempt in range(max_attempts):
                            try:
                                all_red, failed_red_data = self.check_led_colors_via_server("red")
                                
                                # Get detection status for logging
                                debug_response = requests.get(f"{self.server_url}/debug_colors", timeout=5)
                                debug_data = debug_response.json()
                                red_count = debug_data['color_summary']['red']
                                total_detected = debug_data['total_detected']
                                
                                if red_count > 0:  # Server is detecting red LEDs
                                    add_console_message(f"✅ Server detected {red_count}/{total_detected} red LEDs - analyzing frames for optimal capture!", "success")
                                    add_console_message("🔍 Using multi-frame analysis to select best quality image...", "info")
                                    self.save_current_image_async("red", self.current_serial_number or "unknown")
                                    
                                    # Show detection details
                                    add_console_message(f"🔴 RED TEST - {red_count}/{total_detected} LEDs are red", "info")
                                    
                                    # Check for undetected LEDs
                                    undetected_response = requests.get(f"{self.server_url}/check_undetected_leds", timeout=5)
                                    undetected_data = undetected_response.json()
                                    if undetected_data['never_detected']:
                                        add_console_message(f"⚠️ UNDETECTED LEDs: {undetected_data['never_detected']}", "warning")
                                    if undetected_data['poorly_detected']:
                                        poorly = [f"{led['led_id']}({led['sample_count']})" for led in undetected_data['poorly_detected']]
                                        add_console_message(f"⚠️ POORLY DETECTED LEDs: {poorly}", "warning")
                                    break
                                else:
                                    if attempt % 5 == 0:  # Log every 5 seconds
                                        add_console_message(f"⏳ Still waiting... ({red_count}/{total_detected} red LEDs detected)", "info")
                                    time.sleep(1)
                                    
                            except Exception as e:
                                if attempt % 10 == 0:  # Log every 10 seconds
                                    add_console_message(f"⚠️ Server check failed: {str(e)}", "warning")
                                time.sleep(1)
                        else:
                            # Timeout reached - save image anyway
                            add_console_message("⚠️ Timeout waiting for red LED detection - saving current image", "warning")
                            all_red, failed_red_data = self.check_led_colors_via_server("red")
                            self.save_current_image_async("red", self.current_serial_number or "unknown")
                        
                        if all_red:
                            add_console_message("✅ PASS: All LEDs are RED", "success")
                            self.send_command("yes", wait_time=3)
                        else:
                            total_failed = len(failed_red_data)
                            add_console_message(f"❌ FAIL: Found {total_failed} non-red LEDs", "error")
                            
                            # Show detailed failed LED information
                            for i, led in enumerate(failed_red_data[:5]):  # Show first 5 failed LEDs
                                if led['color'] is None:
                                    add_console_message(f"  • {led['led_id']}: ❌ not detected", "error")
                                else:
                                    add_console_message(f"  • {led['led_id']}: {led['color']} (expected red)", "error")
                            
                            if len(failed_red_data) > 5:
                                add_console_message(f"  ... and {len(failed_red_data)-5} more failed LEDs", "error")
                            
                            failed_colors.append(("red", failed_red_data))
                            self.send_command("no", wait_time=3)
                    
                    elif "are all the leds green?" in output.lower():
                        update_test_status(True, "🟢 GREEN LED CHECK", False, "")
                        add_console_message("=== 🟢 GREEN LED CHECK ===", "info")
                        add_console_message("🔍 Waiting for server to detect green LEDs...", "info")
                        
                        # Poll server until it detects green LEDs, then save image immediately
                        max_attempts = 30  # 30 seconds max
                        for attempt in range(max_attempts):
                            try:
                                all_green, failed_green_data = self.check_led_colors_via_server("green")
                                
                                # Get detection status for logging
                                debug_response = requests.get(f"{self.server_url}/debug_colors", timeout=5)
                                debug_data = debug_response.json()
                                green_count = debug_data['color_summary']['green']
                                total_detected = debug_data['total_detected']
                                
                                if green_count > 0:  # Server is detecting green LEDs
                                    add_console_message(f"✅ Server detected {green_count}/{total_detected} green LEDs - analyzing frames for optimal capture!", "success")
                                    add_console_message("🔍 Using multi-frame analysis to select best quality image...", "info")
                                    self.save_current_image_async("green", self.current_serial_number or "unknown")
                                    
                                    # Show detection details
                                    add_console_message(f"🟢 GREEN TEST - {green_count}/{total_detected} LEDs are green", "info")
                                    
                                    # Check for undetected LEDs
                                    undetected_response = requests.get(f"{self.server_url}/check_undetected_leds", timeout=5)
                                    undetected_data = undetected_response.json()
                                    if undetected_data['never_detected']:
                                        add_console_message(f"⚠️ UNDETECTED LEDs: {undetected_data['never_detected']}", "warning")
                                    if undetected_data['poorly_detected']:
                                        poorly = [f"{led['led_id']}({led['sample_count']})" for led in undetected_data['poorly_detected']]
                                        add_console_message(f"⚠️ POORLY DETECTED LEDs: {poorly}", "warning")
                                    break
                                else:
                                    if attempt % 5 == 0:  # Log every 5 seconds
                                        add_console_message(f"⏳ Still waiting... ({green_count}/{total_detected} green LEDs detected)", "info")
                                    time.sleep(1)
                                    
                            except Exception as e:
                                if attempt % 10 == 0:  # Log every 10 seconds
                                    add_console_message(f"⚠️ Server check failed: {str(e)}", "warning")
                                time.sleep(1)
                        else:
                            # Timeout reached - save image anyway
                            add_console_message("⚠️ Timeout waiting for green LED detection - saving current image", "warning")
                            all_green, failed_green_data = self.check_led_colors_via_server("green")
                            self.save_current_image_async("green", self.current_serial_number or "unknown")
                        
                        if all_green:
                            add_console_message("✅ PASS: All LEDs are GREEN", "success")
                            self.send_command("yes", wait_time=3)
                        else:
                            total_failed = len(failed_green_data)
                            add_console_message(f"❌ FAIL: Found {total_failed} non-green LEDs", "error")
                            
                            # Show detailed failed LED information
                            for i, led in enumerate(failed_green_data[:5]):  # Show first 5 failed LEDs
                                if led['color'] is None:
                                    add_console_message(f"  • {led['led_id']}: ❌ not detected", "error")
                                else:
                                    add_console_message(f"  • {led['led_id']}: {led['color']} (expected green)", "error")
                            
                            if len(failed_green_data) > 5:
                                add_console_message(f"  ... and {len(failed_green_data)-5} more failed LEDs", "error")
                            
                            failed_colors.append(("green", failed_green_data))
                            self.send_command("no", wait_time=3)
                    
                    elif "are all the leds blue?" in output.lower():
                        update_test_status(True, "🔵 BLUE LED CHECK", False, "")
                        add_console_message("=== 🔵 BLUE LED CHECK ===", "info")
                        add_console_message("🔍 Waiting for server to detect blue LEDs...", "info")
                        
                        # Poll server until it detects blue LEDs, then save image immediately
                        max_attempts = 30  # 30 seconds max
                        for attempt in range(max_attempts):
                            try:
                                all_blue, failed_blue_data = self.check_led_colors_via_server("blue")
                                
                                # Get detection status for logging
                                debug_response = requests.get(f"{self.server_url}/debug_colors", timeout=5)
                                debug_data = debug_response.json()
                                blue_count = debug_data['color_summary']['blue']
                                total_detected = debug_data['total_detected']
                                
                                if blue_count > 0:  # Server is detecting blue LEDs
                                    add_console_message(f"✅ Server detected {blue_count}/{total_detected} blue LEDs - analyzing frames for optimal capture!", "success")
                                    add_console_message("🔍 Using multi-frame analysis to select best quality image...", "info")
                                    self.save_current_image_async("blue", self.current_serial_number or "unknown")
                                    
                                    # Show detection details
                                    add_console_message(f"🔵 BLUE TEST - {blue_count}/{total_detected} LEDs are blue", "info")
                                    
                                    # Check for undetected LEDs
                                    undetected_response = requests.get(f"{self.server_url}/check_undetected_leds", timeout=5)
                                    undetected_data = undetected_response.json()
                                    if undetected_data['never_detected']:
                                        add_console_message(f"⚠️ UNDETECTED LEDs: {undetected_data['never_detected']}", "warning")
                                    if undetected_data['poorly_detected']:
                                        poorly = [f"{led['led_id']}({led['sample_count']})" for led in undetected_data['poorly_detected']]
                                        add_console_message(f"⚠️ POORLY DETECTED LEDs: {poorly}", "warning")
                                    break
                                else:
                                    if attempt % 5 == 0:  # Log every 5 seconds
                                        add_console_message(f"⏳ Still waiting... ({blue_count}/{total_detected} blue LEDs detected)", "info")
                                    time.sleep(1)
                                    
                            except Exception as e:
                                if attempt % 10 == 0:  # Log every 10 seconds
                                    add_console_message(f"⚠️ Server check failed: {str(e)}", "warning")
                                time.sleep(1)
                        else:
                            # Timeout reached - save image anyway
                            add_console_message("⚠️ Timeout waiting for blue LED detection - saving current image", "warning")
                            all_blue, failed_blue_data = self.check_led_colors_via_server("blue")
                            self.save_current_image_async("blue", self.current_serial_number or "unknown")
                        
                        if all_blue:
                            add_console_message("✅ PASS: All ETH LEDs are BLUE", "success")
                            self.send_command("yes", wait_time=3)
                        else:
                            total_failed = len(failed_blue_data)
                            add_console_message(f"❌ FAIL: Found {total_failed} non-blue ETH LEDs", "error")
                            
                            # Show detailed failed LED information
                            for i, led in enumerate(failed_blue_data[:5]):  # Show first 5 failed LEDs
                                if led['color'] is None:
                                    add_console_message(f"  • {led['led_id']}: ❌ not detected", "error")
                                else:
                                    add_console_message(f"  • {led['led_id']}: {led['color']} (expected blue)", "error")
                            
                            if len(failed_blue_data) > 5:
                                add_console_message(f"  ... and {len(failed_blue_data)-5} more failed LEDs", "error")
                            
                            failed_colors.append(("blue", failed_blue_data))
                            self.send_command("no", wait_time=3)
                    
                    else:
                        # For non-LED tests, ask user for input via web interface
                        if "[yes/no/skip/exit]:" in output.lower():
                            valid_responses = ['yes', 'no', 'skip', 'exit']
                        else:
                            valid_responses = ['yes', 'no', 'skip']
                        
                        # Extract the prompt
                        prompt_lines = output.split('\n')
                        prompt = next((line for line in reversed(prompt_lines) if line.strip() and '[' not in line), "Please respond")
                        
                        # Check if this might need manual text input
                        if any(keyword in prompt.lower() for keyword in ['enter', 'type', 'input', 'name', 'number']):
                            user_response = self.web_input(prompt, valid_responses + ['manual'], "text")
                        else:
                            user_response = self.web_input(prompt, valid_responses, "buttons")
                        
                        self.send_command(user_response, wait_time=3)
                
                # Handle test retry questions
                elif "would you like to run this test again?" in output.lower() and "[yes/no/skip/exit]:" in output.lower():
                    add_console_message("Test asking to retry - Answering NO", "info")
                    self.send_command("no", wait_time=3)
                
                # Check if test is complete
                if "test completed" in output.lower() or "please contact hw4" in output.lower():
                    add_console_message("🎉 Test completed!", "success")
                    update_test_status(False, "Success - Test completed", False, "")
                    break
                
                # Check for timeout or error
                if "connection lost" in output.lower() or len(output) == 0:
                    add_console_message("⚠️ Connection issue or timeout", "error")
                    update_test_status(False, "Error - Connection timeout", False, "")
                    break
            
            # Cleanup
            add_console_message("🧹 Cleaning up...", "info")
            self.send_command("umount ./usb", 2)
            self.send_command("rm -r usb", 2)
            
            # Report results
            if failed_colors:
                add_console_message("⚠️ MANUAL VERIFICATION REQUIRED", "warning")
                add_console_message(f"🏷️ Serial Number: {self.current_serial_number}", "info")
                add_console_message(f"📁 Images saved in '{self.results_folder}' folder", "info")
                
                # Show detailed failed LED summary
                for color, failed_leds in failed_colors:
                    add_console_message(f"❌ Failed {color.upper()} LEDs: {len(failed_leds)}", "error")
                    
                    # List specific failed LEDs
                    failed_led_ids = []
                    for led in failed_leds[:10]:  # Show up to 10 failed LEDs in summary
                        if led['color'] is None:
                            failed_led_ids.append(f"{led['led_id']} (not detected)")
                        else:
                            failed_led_ids.append(f"{led['led_id']} ({led['color']})")
                    
                    if failed_led_ids:
                        add_console_message(f"   📍 Check these LEDs: {', '.join(failed_led_ids)}", "error")
                        if len(failed_leds) > 10:
                            add_console_message(f"   ... and {len(failed_leds)-10} more", "error")
            else:
                add_console_message("🎉 ALL LED TESTS PASSED!", "success")
                add_console_message(f"🏷️ Serial Number: {self.current_serial_number}", "info")
                add_console_message(f"📁 Images saved in '{self.results_folder}' folder", "info")
            
            return True
            
        except Exception as e:
            add_console_message(f"❌ Error during automated test: {e}", "error")
            update_test_status(False, f"Error: {str(e)}", False, "")
            return False
        
        finally:
            if self.serial_conn:
                self.serial_conn.close()
                add_console_message("🔌 Serial connection closed", "info")
            
            # Set final status based on test results
            if failed_colors:
                # Manual verification required - set pink background
                update_test_status(False, "Manual verification required", False, "")
            else:
                # All tests passed - set green background
                update_test_status(False, "Success - All tests passed", False, "")

    def web_input(self, prompt: str, valid_responses: List[str], input_type: str = "buttons") -> str:
        """Get input from web interface"""
        global current_user_response, response_ready
        
        # Update test status to show we're awaiting input
        add_console_message(f"[INPUT REQUIRED] {prompt}", "input")
        update_test_status(True, "Awaiting user input", True, prompt, input_type)
        
        # Wait for user response via web interface
        response_ready.clear()
        current_user_response = None
        
        # Wait for response (with timeout)
        if response_ready.wait(timeout=300):  # 5 minute timeout
            response = current_user_response
            if response and response.lower() in [r.lower() for r in valid_responses]:
                add_console_message(f"User response: {response}", "success")
                update_test_status(True, f"Processing {response}...", False, "")
                return response.lower()
            else:
                add_console_message(f"Invalid response '{response}'. Using 'skip' as default.", "warning")
                update_test_status(True, "Processing skip...", False, "")
                return "skip"
        else:
            add_console_message("Input timeout. Using 'skip' as default.", "warning")
            update_test_status(True, "Processing skip...", False, "")
            return "skip"

# API Routes
@app.get("/", response_class=HTMLResponse)
async def get_main_page():
    """Serve the main HTML page"""
    template_path = Path(__file__).parent / "templates" / "index.html"
    return FileResponse(str(template_path))

@app.get("/api/com-ports")
async def get_com_ports():
    """Get available COM ports"""
    try:
        ports = [port.device for port in serial.tools.list_ports.comports()]
        add_console_message(f"📡 Found {len(ports)} COM ports: {', '.join(ports) if ports else 'None'}", "info")
        return {"ports": ports}
    except Exception as e:
        add_console_message(f"❌ Error getting COM ports: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test-programs")
async def get_test_programs():
    """Get available test programs"""
    try:
        # Common test program names
        programs = [
            "1340_test_led_automated_correct.py",
            "1340_test_led_automated.py", 
            "led_test.py",
            "automated_test.py"
        ]
        return {"programs": programs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/server/start")
async def start_detection_server():
    """Start the LED detection server"""
    global detection_server_process
    
    if detection_server_process is not None and detection_server_process.poll() is None:
        return {"status": "error", "message": "Detection server is already running"}
    
    try:
        server_path = os.path.join(parent_dir, "server", "led_detection_server.py")
        detection_server_process = subprocess.Popen(
            [sys.executable, server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.join(parent_dir, "server")
        )
        
        # Wait a moment for server to start
        await asyncio.sleep(3)
        update_server_status()
        
        add_console_message("🚀 LED Detection Server started", "success")
        return {"status": "success", "message": "Detection server started successfully"}
    except Exception as e:
        add_console_message(f"❌ Failed to start detection server: {str(e)}", "error")
        return {"status": "error", "message": f"Failed to start detection server: {str(e)}"}

@app.post("/api/server/stop")
async def stop_detection_server():
    """Stop the LED detection server"""
    global detection_server_process
    
    if detection_server_process is None or detection_server_process.poll() is not None:
        return {"status": "error", "message": "Detection server is not running"}
    
    try:
        detection_server_process.terminate()
        detection_server_process.wait(timeout=5)
        detection_server_process = None
        
        update_server_status()
        add_console_message("🛑 LED Detection Server stopped", "info")
        return {"status": "success", "message": "Detection server stopped successfully"}
    except Exception as e:
        add_console_message(f"❌ Failed to stop detection server: {str(e)}", "error")
        return {"status": "error", "message": f"Failed to stop detection server: {str(e)}"}

@app.get("/api/server/status")
async def get_server_status():
    """Get the current server status"""
    update_server_status()
    return server_status

@app.post("/api/test/start")
async def start_test(request: TestStartRequest):
    """Start the LED test"""
    global controller_instance, controller_thread
    
    if controller_thread is not None and controller_thread.is_alive():
        return {"status": "error", "message": "Test is already running"}
    
    if not request.com_port:
        return {"status": "error", "message": "COM port is required"}
    
    try:
        # Check if server is running
        try:
            response = requests.get("http://localhost:8000/status", timeout=2)
            if response.status_code != 200:
                return {"status": "error", "message": "LED Detection Server is not running. Please start it first."}
        except:
            return {"status": "error", "message": "LED Detection Server is not running. Please start it first."}
        
        # Create controller instance
        controller_instance = ModernLEDTestController(
            port=request.com_port,
            server_url=request.server_url,
            test_program=request.test_program,
            username=request.username,
            password=request.password
        )
        
        # Start test in background thread
        def run_test():
            controller_instance.run_automated_test_web()
        
        controller_thread = threading.Thread(target=run_test, daemon=True)
        controller_thread.start()
        
        add_console_message(f"🚀 Starting test on {request.com_port} with program {request.test_program}", "info")
        return {"status": "success", "message": "Test started successfully"}
        
    except Exception as e:
        add_console_message(f"❌ Failed to start test: {str(e)}", "error")
        return {"status": "error", "message": f"Failed to start test: {str(e)}"}

@app.post("/api/test/stop")
async def stop_test():
    """Stop the LED test"""
    global controller_instance, controller_thread
    
    if controller_thread is None or not controller_thread.is_alive():
        return {"status": "error", "message": "No test is running"}
    
    try:
        if controller_instance and controller_instance.serial_conn:
            controller_instance.serial_conn.close()
        
        update_test_status(False, "Test stopped by user", False, "")
        add_console_message("🛑 Test stopped by user", "warning")
        return {"status": "success", "message": "Test stopped successfully"}
        
    except Exception as e:
        add_console_message(f"❌ Failed to stop test: {str(e)}", "error")
        return {"status": "error", "message": f"Failed to stop test: {str(e)}"}

@app.get("/api/test/status")
async def get_test_status():
    """Get the current test status"""
    return test_status

@app.post("/api/test/respond")
async def respond_to_test(request: UserResponseRequest):
    """Send user response to the test"""
    global current_user_response, response_ready
    
    if not test_status["awaiting_input"]:
        return {"status": "error", "message": "Test is not awaiting input"}
    
    current_user_response = request.response
    response_ready.set()
    
    add_console_message(f"📤 User response sent: {request.response}", "success")
    return {"status": "success", "message": f"Response '{request.response}' sent"}

@app.get("/api/console/messages")
async def get_console_messages():
    """Get recent console messages"""
    return {"messages": list(console_messages)}

@app.post("/api/console/clear")
async def clear_console():
    """Clear console messages"""
    console_messages.clear()
    await manager.broadcast({
        "type": "console_clear",
        "data": {}
    })
    add_console_message("🧹 Console cleared", "info")
    return {"status": "success", "message": "Console cleared"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    global main_event_loop
    
    # Ensure event loop is set when first WebSocket connects
    if not main_event_loop:
        main_event_loop = asyncio.get_event_loop()
        print("🔗 Event loop set from WebSocket connection")
    
    await manager.connect(websocket)
    try:
        # Send initial status
        await websocket.send_json({
            "type": "server_status",
            "data": server_status
        })
        await websocket.send_json({
            "type": "test_status", 
            "data": test_status
        })
        await websocket.send_json({
            "type": "console_messages",
            "data": {"messages": list(console_messages)}
        })
        
        # Keep connection alive - no camera feed needed
        while True:
            await asyncio.sleep(1)  # Just keep connection alive
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

# Serve static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)
    webbrowser.open("http://localhost:8080")
    
## Main function to start it

def main():
    """Main entry point"""
    print("=" * 60)
    print("LED Test Controller - Web GUI")
    print("=" * 60)
    print("Starting web server...")
    
    # Debug: Print paths to verify they exist
    current_dir = Path(__file__).parent
    static_dir = current_dir / "static"
    template_file = current_dir / "templates" / "index.html"
    
    print(f"Current directory: {current_dir}")
    print(f"Static directory: {static_dir} (exists: {static_dir.exists()})")
    print(f"Template file: {template_file} (exists: {template_file.exists()})")
    
    if not static_dir.exists():
        print(f"❌ Error: Static directory does not exist: {static_dir}")
        return
    
    if not template_file.exists():
        print(f"❌ Error: Template file does not exist: {template_file}")
        return
    
    # Start browser in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Start the web server - let uvicorn handle everything
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    main()