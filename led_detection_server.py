import depthai as dai
import cv2
import contextlib
import numpy as np
import json
import math
import asyncio
import threading
import time
from collections import defaultdict, deque
from statistics import mode
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import io
import base64
from PIL import Image

# Global variables
config_data = {}
led_color_samples = defaultdict(lambda: deque(maxlen=30))  # Store last 30 samples for each LED (~1-2 seconds)
current_frames = {"Camera 1": None, "Camera 2": None}
combined_frame = None
camera_running = False
camera_thread = None

# Best image tracking (last 3 seconds)
best_image_data = {
    "image": None,
    "led_count": 0,
    "timestamp": 0,
    "recent_images": deque(maxlen=90)  # Store ~3 seconds of images at 30fps
}

# Load configuration
def load_config():
    global config_data
    try:
        with open("data.json", 'r') as file:
            config_data = json.load(file)
        print(f"Loaded configuration for {len(config_data)} LEDs")
    except Exception as e:
        print(f"Error loading config: {e}")
        config_data = {}

def getLEDID(center, stream_name):
    global config_data
    min_dist = float('inf')
    ID = None

    for key, value in config_data.items():
        if isinstance(value, list) and len(value) == 2:
            dist = math.sqrt((center[0] - value[0]) ** 2 + (center[1] - value[1]) ** 2)
            if dist < min_dist:
                if dist > 10:
                    continue
                min_dist = dist
                ID = key

    return ID

def detect_led_color(image, x, y, radius):
    # Extract the region of interest (ROI) around the circle
    roi_size = int(radius * 2)
    half_size = roi_size // 2
    # Ensure ROI stays within image bounds
    y_start = max(0, int(y - half_size))
    y_end = min(image.shape[0], int(y + half_size))
    x_start = max(0, int(x - half_size))
    x_end = min(image.shape[1], int(x + half_size))
    roi = image[y_start:y_end, x_start:x_end]

    # Convert ROI to HSV
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # Define color ranges in HSV
    red_lower1 = np.array([0, 120, 70])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([170, 120, 70])
    red_upper2 = np.array([180, 255, 255])
    green_lower = np.array([35, 100, 100])
    green_upper = np.array([85, 255, 255])
    blue_lower = np.array([100, 100, 100])
    blue_upper = np.array([130, 255, 255])
    orange_lower = np.array([11, 150, 150])
    orange_upper = np.array([25, 255, 255])

    # Create color masks
    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)

    # Refined orange mask
    orange_mask_raw = cv2.inRange(hsv, orange_lower, orange_upper)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    orange_mask = cv2.bitwise_and(
        orange_mask_raw,
        orange_mask_raw,
        mask=cv2.inRange(saturation, 150, 255) & cv2.inRange(value, 150, 255)
    )

    # Calculate the percentage of each color
    red_percent = (red_mask > 0).mean() * 100
    green_percent = (green_mask > 0).mean() * 100
    blue_percent = (blue_mask > 0).mean() * 100
    orange_percent = (orange_mask > 0).mean() * 100

    # Determine the dominant color
    colors = {
        'red': red_percent,
        'green': green_percent,
        'blue': blue_percent,
        'orange': orange_percent
    }
    dominant_color = max(colors, key=colors.get)

    # Define BGR colors for drawing
    color_map = {
        'red': (0, 0, 255),
        'green': (0, 255, 0),
        'blue': (255, 0, 0),
        'orange': (0, 165, 255)
    }

    return dominant_color, colors, color_map[dominant_color]

def detect_LED(frame, stream_name):
    global led_color_samples
    original_image = frame.copy()
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detected_leds = 0
    
    if stream_name == "Camera 1":
        height, width = image.shape[:2]
        crop_y_start = height // 2 
        crop_y_end = height     
        crop_x_end = (width * 3) // 5
        cropped_image = image[crop_y_start:crop_y_end, 0:crop_x_end]
        cropped_image = (cropped_image / 1.7).astype(np.uint8)
        image[crop_y_start:crop_y_end, 0:crop_x_end] = cropped_image
    
    _, binary_image = cv2.threshold(image, 30, 255, cv2.THRESH_BINARY)

    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(binary_image, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1)
    dilated = cv2.dilate(eroded, kernel, iterations=1)

    circles = cv2.HoughCircles(
        dilated,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=10,
        param1=10,
        param2=7,
        minRadius=4,
        maxRadius=10
    )

    if circles is not None:
        circles = np.uint16(np.around(circles))
        for i in circles[0, :]:
            center = (i[0], i[1])
            radius = i[2]
            ledid = getLEDID(center, stream_name)
            
            if ledid is not None:
                detected_leds += 1
                dominant_color, color_percentages, draw_color = detect_led_color(original_image, center[0], center[1], radius)
                
                # Add color sample with timestamp to the deque for this LED
                led_color_samples[ledid].append({
                    "color": dominant_color,
                    "timestamp": time.time()
                })
                
                cv2.circle(frame, center, 1, draw_color, 2)
                cv2.circle(frame, center, radius, draw_color, 2)
                cv2.putText(frame, f"{ledid}", (center[0] + radius + 5, center[1]), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, draw_color, 2)
    
    return frame, detected_leds

def create_pipeline():
    
    pipeline = dai.Pipeline()
    cam_rgb = pipeline.create(dai.node.ColorCamera)
    cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_4000X3000)
    cam_rgb.setFps(30)
    cam_rgb.initialControl.setManualFocus(150)
    cam_rgb.initialControl.setManualExposure(8000, 100)
    cam_rgb.initialControl.setBrightness(-6)
    cam_rgb.initialControl.setManualWhiteBalance(1000)
    xout_rgb = pipeline.create(dai.node.XLinkOut)
    xout_rgb.setStreamName("rgb")
    cam_rgb.video.link(xout_rgb.input)
    return pipeline

def update_best_image(image, total_leds):
    """Update the best image if this one has more LEDs detected"""
    global best_image_data
    current_time = time.time()
    
    # Add to recent images
    best_image_data["recent_images"].append({
        "image": image.copy(),
        "led_count": total_leds,
        "timestamp": current_time
    })
    
    # Update best image if this one is better
    if total_leds > best_image_data["led_count"]:
        best_image_data["image"] = image.copy()
        best_image_data["led_count"] = total_leds
        best_image_data["timestamp"] = current_time

def camera_worker():
    global current_frames, combined_frame, camera_running
    
    try:
        with contextlib.ExitStack() as stack:
            device_infos = dai.Device.getAllAvailableDevices()[:2]
            if len(device_infos) < 2:
                print(f"Only {len(device_infos)} camera(s) detected. Two cameras required.")
                return

            q_rgb_map = []
            usb_speed = dai.UsbSpeed.SUPER
            devicesID = []
            
            for i, device_info in enumerate(device_infos):
                device = stack.enter_context(dai.Device(create_pipeline(), device_info, usb_speed))
                q_rgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
                devicesID.append(device_info.getMxId())
                stream_name = "Camera 1" if device_info.getMxId().startswith("144") else "Camera 2"
                if len(devicesID) > 1:
                    stream_name = "Camera 2" if device_info.getMxId().startswith("184") else "Camera 1"

                q_rgb_map.append((q_rgb, stream_name))
                print(f"Connected to {stream_name} with ID: {device_info.getMxId()}")

            camera_running = True
            
            # Create resizable window for combined frame like in LED_missingsockets.py
            cv2.namedWindow("LED Detection Server - Live Feed", cv2.WINDOW_NORMAL)
            cv2.setWindowProperty("LED Detection Server - Live Feed", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.setWindowProperty("LED Detection Server - Live Feed", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            
            while camera_running:
                frames = {}
                frame_led_counts = {}
                
                for q_rgb, stream_name in q_rgb_map:
                    if q_rgb.has():
                        frame = q_rgb.get().getCvFrame()
                        frame = cv2.resize(frame, (1706, 960))
                        frame = np.rot90(frame, 2)
                        frame = np.ascontiguousarray(frame)
                        
                        if stream_name == "Camera 2": 
                            frame = frame[120:820, 500:1502]
                        else: 
                            frame = frame[250:820, 340:1451]
                    
                        frame, led_count = detect_LED(frame, stream_name)
                        frames[stream_name] = frame
                        frame_led_counts[stream_name] = led_count
                        current_frames[stream_name] = frame.copy()

                if len(frames) == 2:
                    frame1 = frames["Camera 1"] if devicesID[0].startswith("184") else frames["Camera 2"]
                    frame2 = frames["Camera 2"] if devicesID[1].startswith("144") else frames["Camera 1"]

                    # Calculate heights and pad if necessary
                    h1, w1 = frame1.shape[:2]
                    h2, w2 = frame2.shape[:2]
                    max_height = max(h1, h2)

                    if h1 < max_height:
                        pad_height = max_height - h1
                        frame1 = np.pad(frame1, ((pad_height, 0), (0, 0), (0, 0)), mode='constant', constant_values=0)
                    elif h2 < max_height:
                        pad_height = max_height - h2
                        frame2 = np.pad(frame2, ((pad_height, 0), (0, 0), (0, 0)), mode='constant', constant_values=0)

                    # Stack frames horizontally
                    combined_frame = np.hstack((frame1, frame2))
                    
                    # Display the combined frame (let window handle resizing)
                    cv2.imshow('LED Detection Server - Live Feed', combined_frame)
                    
                    # Check for ESC key to exit
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:  # ESC key
                        print("\nESC pressed - Stopping server...")
                        camera_running = False
                        break
                    
                    # Update best image based on total LED count
                    total_led_count = sum(frame_led_counts.values())
                    update_best_image(combined_frame, total_led_count)

                time.sleep(0.033)  # ~30 FPS
                
    except Exception as e:
        print(f"Camera worker error: {e}")
        camera_running = False
    finally:
        cv2.destroyAllWindows()
        print("Camera windows closed")

def get_led_mode_color(led_id: str) -> Optional[str]:
    """Get the most frequent color for an LED based on samples from last 3 seconds"""
    if led_id not in led_color_samples or len(led_color_samples[led_id]) == 0:
        return None  # Not detected
    
    current_time = time.time()
    recent_samples = []
    
    # Filter samples to only include those from the last 3 seconds
    for sample in led_color_samples[led_id]:
        if isinstance(sample, dict) and "timestamp" in sample:
            if current_time - sample["timestamp"] <= 3.0:  # Last 3 seconds
                recent_samples.append(sample["color"])
        else:
            # Handle old format samples (just color strings) - treat as expired
            continue
    
    if not recent_samples:
        return None  # No recent samples - LED not detected
    
    # Count occurrences of each color in recent samples
    color_counts = {
        'red': 0,
        'green': 0,
        'blue': 0,
        'orange': 0
    }
    
    for color in recent_samples:
        if color in color_counts:
            color_counts[color] += 1
    
    # Find the color with the highest count
    most_frequent_color = max(color_counts, key=color_counts.get)
    
    # Return the most frequent color only if it has at least 1 occurrence
    if color_counts[most_frequent_color] > 0:
        return most_frequent_color
    else:
        # If no primary colors detected, LED is not detected
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global camera_thread
    load_config()
    
    # Start camera worker in a separate thread
    camera_thread = threading.Thread(target=camera_worker, daemon=True)
    camera_thread.start()
    print("LED Detection Server started")
    
    yield
    
    # Shutdown
    global camera_running
    camera_running = False
    if camera_thread:
        camera_thread.join(timeout=5)
    print("LED Detection Server stopped")

app = FastAPI(title="LED Detection Server", version="1.0.0", lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "LED Detection Server is running", "version": "1.0.0"}

@app.get("/status")
async def get_status():
    return {
        "camera_running": camera_running,
        "cameras_connected": len([f for f in current_frames.values() if f is not None]),
        "total_leds_configured": len(config_data),
        "leds_with_samples": len(led_color_samples)
    }

@app.get("/combined_image")
async def get_combined_image():
    """Get the current combined camera image"""
    global combined_frame
    
    if combined_frame is None:
        raise HTTPException(status_code=404, detail="No combined image available")
    
    # Convert frame to JPEG
    _, buffer = cv2.imencode('.jpg', combined_frame)
    
    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/jpeg",
        headers={"Content-Disposition": "inline; filename=combined_image.jpg"}
    )

@app.get("/best_image")
async def get_best_image():
    """Get the image with maximum LEDs detected in last 3 seconds"""
    global best_image_data
    
    if best_image_data["image"] is None:
        raise HTTPException(status_code=404, detail="No best image available")
    
    # Convert frame to JPEG
    _, buffer = cv2.imencode('.jpg', best_image_data["image"])
    
    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/jpeg",
        headers={"Content-Disposition": "inline; filename=best_image.jpg"}
    )

@app.get("/best_image_info")
async def get_best_image_info():
    """Get information about the best image"""
    global best_image_data
    
    return {
        "led_count": best_image_data["led_count"],
        "timestamp": best_image_data["timestamp"],
        "age_seconds": time.time() - best_image_data["timestamp"] if best_image_data["timestamp"] > 0 else 0
    }

@app.get("/combined_image_base64")
async def get_combined_image_base64():
    """Get the current combined camera image as base64"""
    global combined_frame
    
    if combined_frame is None:
        raise HTTPException(status_code=404, detail="No combined image available")
    
    # Convert frame to JPEG and then to base64
    _, buffer = cv2.imencode('.jpg', combined_frame)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return {"image": img_base64, "format": "jpeg"}

@app.get("/camera/{camera_name}")
async def get_camera_image(camera_name: str):
    """Get image from a specific camera"""
    if camera_name not in current_frames:
        raise HTTPException(status_code=404, detail=f"Camera {camera_name} not found")
    
    frame = current_frames[camera_name]
    if frame is None:
        raise HTTPException(status_code=404, detail=f"No image available from {camera_name}")
    
    # Convert frame to JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    
    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/jpeg",
        headers={"Content-Disposition": f"inline; filename={camera_name.replace(' ', '_')}.jpg"}
    )

@app.get("/led_status")
async def get_all_led_status():
    """Get the current status of all LEDs based on mode of last 30 samples"""
    led_status = {}
    
    for led_id in config_data.keys():
        color = get_led_mode_color(led_id)
        sample_count = len(led_color_samples[led_id]) if led_id in led_color_samples else 0
        
        led_status[led_id] = {
            "color": color,
            "sample_count": sample_count,
            "coordinates": config_data[led_id]
        }
    
    return {
        "led_status": led_status,
        "total_leds": len(config_data),
        "timestamp": time.time()
    }

@app.get("/led_status/{led_id}")
async def get_led_status(led_id: str):
    """Get the current status of a specific LED"""
    if led_id not in config_data:
        raise HTTPException(status_code=404, detail=f"LED {led_id} not found in configuration")
    
    color = get_led_mode_color(led_id)
    sample_count = len(led_color_samples[led_id]) if led_id in led_color_samples else 0
    
    return {
        "led_id": led_id,
        "color": color,
        "sample_count": sample_count,
        "coordinates": config_data[led_id],
        "recent_samples": [s["color"] if isinstance(s, dict) else s for s in led_color_samples[led_id]] if led_id in led_color_samples else [],
        "timestamp": time.time()
    }

@app.get("/led_colors")
async def get_led_colors():
    """Get only the LED IDs and their current colors (mode of 30 samples)"""
    led_colors = {}
    
    for led_id in config_data.keys():
        color = get_led_mode_color(led_id)
        if color:  # Only include LEDs that have color data
            led_colors[led_id] = color
    
    return {
        "led_colors": led_colors,
        "timestamp": time.time()
    }

@app.post("/clear_samples")
async def clear_led_samples():
    """Clear all LED color samples"""
    global led_color_samples
    led_color_samples.clear()
    return {"message": "All LED samples cleared"}

@app.post("/clear_samples/{led_id}")
async def clear_led_samples_for_id(led_id: str):
    """Clear LED color samples for a specific LED"""
    if led_id not in config_data:
        raise HTTPException(status_code=404, detail=f"LED {led_id} not found in configuration")
    
    if led_id in led_color_samples:
        led_color_samples[led_id].clear()
    
    return {"message": f"Samples cleared for LED {led_id}"}

@app.get("/check_red_leds")
async def check_red_leds():
    """Check if all 69 LEDs are red, if not list which are not red"""
    all_leds = list(config_data.keys())
    non_red_leds = []
    red_leds = []
    no_data_leds = []
    
    for led_id in all_leds:
        color = get_led_mode_color(led_id)
        if color is None:
            no_data_leds.append(led_id)
        elif color != 'red':
            non_red_leds.append({"led_id": led_id, "color": color})
        else:
            red_leds.append(led_id)
    
    all_red = len(non_red_leds) == 0 and len(no_data_leds) == 0
    
    return {
        "all_leds_red": all_red,
        "total_leds": len(all_leds),
        "red_leds_count": len(red_leds),
        "non_red_leds": non_red_leds,
        "no_data_leds": no_data_leds,
        "timestamp": time.time()
    }

@app.get("/check_green_leds")
async def check_green_leds():
    """Check if all 69 LEDs are green, if not list which are not green"""
    all_leds = list(config_data.keys())
    non_green_leds = []
    green_leds = []
    no_data_leds = []
    
    for led_id in all_leds:
        color = get_led_mode_color(led_id)
        if color is None:
            no_data_leds.append(led_id)
        elif color != 'green':
            non_green_leds.append({"led_id": led_id, "color": color})
        else:
            green_leds.append(led_id)
    
    all_green = len(non_green_leds) == 0 and len(no_data_leds) == 0
    
    return {
        "all_leds_green": all_green,
        "total_leds": len(all_leds),
        "green_leds_count": len(green_leds),
        "non_green_leds": non_green_leds,
        "no_data_leds": no_data_leds,
        "timestamp": time.time()
    }

@app.get("/check_blue_leds")
async def check_blue_leds():
    """Check if all 18 eth-type LEDs are blue, if not list which are not blue"""
    # Get only eth-type LEDs (eth1-1, eth1-2, eth5, eth6, etc.)
    eth_leds = [led_id for led_id in config_data.keys() if led_id.startswith('eth')]
    
    non_blue_leds = []
    blue_leds = []
    no_data_leds = []
    
    for led_id in eth_leds:
        color = get_led_mode_color(led_id)
        if color is None:
            no_data_leds.append(led_id)
        elif color != 'blue':
            non_blue_leds.append({"led_id": led_id, "color": color})
        else:
            blue_leds.append(led_id)
    
    all_blue = len(non_blue_leds) == 0 and len(no_data_leds) == 0
    
    return {
        "all_eth_leds_blue": all_blue,
        "total_eth_leds": len(eth_leds),
        "blue_leds_count": len(blue_leds),
        "non_blue_leds": non_blue_leds,
        "no_data_leds": no_data_leds,
        "eth_leds_checked": eth_leds,
        "timestamp": time.time()
    }

@app.get("/check_undetected_leds")
async def check_undetected_leds():
    """Check which LEDs from configuration are not being detected at all"""
    all_configured_leds = set(config_data.keys())
    detected_leds = set(led_color_samples.keys())
    
    # LEDs with no samples at all
    never_detected = list(all_configured_leds - detected_leds)
    
    # LEDs with samples but very few (less than 5 samples)
    poorly_detected = []
    well_detected = []
    
    for led_id in detected_leds:
        sample_count = len(led_color_samples[led_id])
        if sample_count < 5:
            poorly_detected.append({"led_id": led_id, "sample_count": sample_count})
        else:
            well_detected.append(led_id)
    
    total_issues = len(never_detected) + len(poorly_detected)
    
    return {
        "all_leds_detected_well": total_issues == 0,
        "total_configured_leds": len(all_configured_leds),
        "well_detected_count": len(well_detected),
        "never_detected": never_detected,
        "never_detected_count": len(never_detected),
        "poorly_detected": poorly_detected,
        "poorly_detected_count": len(poorly_detected),
        "detection_rate": len(well_detected) / len(all_configured_leds) * 100,
        "timestamp": time.time()
    }

@app.get("/debug_colors")
async def debug_colors():
    """Debug endpoint to see current color distribution"""
    color_summary = {"red": 0, "green": 0, "blue": 0, "orange": 0}
    led_details = {}
    
    for led_id in config_data.keys():
        if led_id in led_color_samples and len(led_color_samples[led_id]) > 0:
            samples = list(led_color_samples[led_id])
            # Extract colors from samples (handle both old and new format)
            recent_colors = []
            for sample in samples[-5:]:  # Last 5 samples
                if isinstance(sample, dict):
                    recent_colors.append(sample["color"])
                else:
                    recent_colors.append(sample)
            
            current_color = get_led_mode_color(led_id)
            
            led_details[led_id] = {
                "current_color": current_color,
                "recent_samples": recent_colors,
                "total_samples": len(samples)
            }
            
            if current_color and current_color in color_summary:
                color_summary[current_color] += 1
    
    # ETH LED specific info
    eth_details = {k: v for k, v in led_details.items() if k.startswith('eth')}
    
    return {
        "color_summary": color_summary,
        "total_detected": len(led_details),
        "eth_leds_total": len([k for k in config_data.keys() if k.startswith('eth')]),
        "eth_leds_detected": len(eth_details),
        "eth_blue_count": sum(1 for details in eth_details.values() if details["current_color"] == "blue"),
        "sample_led_details": {k: v for k, v in list(led_details.items())[:10]},
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 