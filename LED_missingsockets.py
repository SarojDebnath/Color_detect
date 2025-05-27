import depthai as dai
import cv2
import contextlib
import numpy as np
import json
import math
global stream_name
#Cam2 is capturing from Left.
with open("C:/Users/sarojd/SDX330/Color_detect/data.json", 'r') as file:
            config_data = json.load(file)
current_id=[]
stream_name="Camera 1"

def getLEDID(center):
    global config_data, stream_name, current_id
    min_dist = float('inf')
    ID = None

    for key, value in config_data.items():
        if stream_name == "Camera 1":
            pass
            # Only consider pon1 to pon16 and eth
            #if not (key.startswith("pon") and key[3:].isdigit() and 1 <= int(key[3:]) <= 16 or key == "eth"):
             #   continue

        if isinstance(value, list) and len(value) == 2:
            dist = math.sqrt((center[0] - value[0]) ** 2 + (center[1] - value[1]) ** 2)
            if dist < min_dist:
                min_dist = dist
                ID = key

    #if ID and ID not in current_id:
     #   current_id.append(ID)

    return ID



def detect_led_color(image, x, y, radius):
    # Extract the region of interest (ROI) around the circle
    roi_size = int(radius * 2)  # Use the circle's diameter as ROI size
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

    # Refined orange mask using saturation and value constraints
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

def detect_LED(frame):
    original_image = frame.copy()  # Keep a copy of the original image for color detection
    image = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    # Convert grayscale image to binary using a threshold
    blur_image = cv2.GaussianBlur(image, (5,5), 1)  # Apply Gaussian blur to reduce noise
    _, binary_image = cv2.threshold(blur_image, 35, 255, cv2.THRESH_BINARY)

    kernel = np.ones((3, 3), np.uint8)  # 3x3 structuring element
    dilated = cv2.dilate(binary_image, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1)
    dilated = cv2.dilate(eroded, kernel, iterations=1)

    circles = cv2.HoughCircles(
        dilated,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=5,
        param1=10,
        param2=9,
        minRadius=5,
        maxRadius=10
    )

    if circles is not None:
        circles = np.uint16(np.around(circles))
        for i in circles[0, :]:
            center = (i[0], i[1])
            radius = i[2]
            # Detect color of the LED
            dominant_color, color_percentages, draw_color = detect_led_color(original_image, center[0], center[1], radius)
            cv2.circle(frame, center, 1, draw_color, 2)  # Green center
            cv2.circle(frame, center, radius, draw_color, 2)  # Red outline
            #print(center)
            ledid=getLEDID(center)
            cv2.putText(frame,f"{ledid}",
                        (center[0] + radius+5, center[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, draw_color, 2)
    return frame


#Rectangle for Camera 1 is between (490, 764) and (490, 766)
#Rectangle for Camera 2 is between (1405, 100) and (1405, 100)
# Dictionary to store state for each camera
camera_states = {}

def create_pipeline():
    pipeline = dai.Pipeline()
    cam_rgb = pipeline.create(dai.node.ColorCamera)
    cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_4000X3000)  # 4056x3040
    cam_rgb.setFps(30)
    cam_rgb.initialControl.setManualFocus(150)
    cam_rgb.initialControl.setManualExposure(8000, 100)
    cam_rgb.initialControl.setBrightness(-6) #-10 .. 10
    cam_rgb.initialControl.setManualWhiteBalance(1000)#1000..12000
    xout_rgb = pipeline.create(dai.node.XLinkOut)
    xout_rgb.setStreamName("rgb")
    cam_rgb.video.link(xout_rgb.input)
    return pipeline

def main():
    global framename, stream_name
    with contextlib.ExitStack() as stack:
        device_infos = dai.Device.getAllAvailableDevices()[:2]
        if len(device_infos) < 2:
            raise RuntimeError(f"Only {len(device_infos)} camera(s) detected. Two cameras required.")

        q_rgb_map = []
        usb_speed = dai.UsbSpeed.SUPER
        devicesID=[]
        for i, device_info in enumerate(device_infos):
            device = stack.enter_context(dai.Device(create_pipeline(), device_info, usb_speed))
            q_rgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            devicesID.append(device_info.getMxId())
            stream_name = "Camera 1" if devicesID[0].startswith("144") else "Camera 2"
            if len(devicesID) > 1:
                stream_name = "Camera 2" if devicesID[1].startswith("184") else "Camera 1"

            q_rgb_map.append((q_rgb, stream_name))
            print(f"Connected to {stream_name} with ID: {device_info.getMxId()}")

        # Create resizable window for combined frame
        cv2.namedWindow("Combined Cameras", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Combined Cameras", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty("Combined Cameras", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

        try:
            frame_count = 0
            while True:
                frames = {}
                for q_rgb, stream_name in q_rgb_map:
                    if q_rgb.has():
                        frame = q_rgb.get().getCvFrame()
                        frame = cv2.resize(frame, (1706, 960))
                        frame = np.rot90(frame, 2)
                        frame = np.ascontiguousarray(frame)  # Ensure contiguous
                        
                        #print(devicesID)
                        if stream_name=="Camera 2": 
                            frame = frame[120:820, 500:1502]
                        else: 
                            frame = frame[250:820, 340:1451]
                        frame= detect_LED(frame)  # Detect LED in the frame
                        frames[stream_name] = frame
                        cv2.imshow(stream_name, frame)
                        cv2.imwrite(f"{stream_name}.png", frame)

                if len(frames) == 2:  # Ensure both frames are available

                    frame1 = frames["Camera 1"] if devicesID[0].startswith("184") else frames["Camera 2"]
                    frame2 = frames["Camera 2"] if devicesID[1].startswith("144") else frames["Camera 1"]

                    # Calculate heights
                    h1, w1 = frame1.shape[:2]
                    h2, w2 = frame2.shape[:2]
                    max_height = max(h1, h2)

                    # Pad the shorter frame with black pixels at the top
                    if h1 < max_height:
                        pad_height = max_height - h1
                        frame1 = np.pad(frame1, ((pad_height, 0), (0, 0), (0, 0)), mode='constant', constant_values=0)
                    elif h2 < max_height:
                        pad_height = max_height - h2
                        frame2 = np.pad(frame2, ((pad_height, 0), (0, 0), (0, 0)), mode='constant', constant_values=0)

                    # Stack frames horizontally (Camera 2 on left, Camera 1 on right)
                    combined_frame = np.hstack((frame2, frame1))

                    # Print dimensions for debugging
                    #print(f"Frame1 shape: {frame1.shape}, Frame2 shape: {frame2.shape}, Combined shape: {combined_frame.shape}")

                    # Resize combined frame to fit display (adjust target_width based on your screen)
                    target_width = 1280  # Adjust to your screen resolution (e.g., 1920 for 1920x1080)
                    combined_h, combined_w = combined_frame.shape[:2]
                    if combined_w > target_width:
                        scale = target_width / combined_w
                        target_height = int(combined_h * scale)
                        combined_frame = cv2.resize(combined_frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
                        #print(f"Resized combined frame to: {combined_frame.shape}")

                    # Save the first combined frame to disk for inspection
                    if frame_count == 0:
                        cv2.imwrite("combined_frame.png", combined_frame)
                        print("Saved combined frame to 'combined_frame.png'")
                        frame_count += 1

                    # Display the combined frame
                    cv2.imshow("Combined Cameras", combined_frame)

                if cv2.waitKey(1) == ord('q'):
                    break
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            print("No frames received or exiting...")
            cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        cv2.destroyAllWindows()