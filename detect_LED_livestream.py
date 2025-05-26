import depthai as dai
import cv2
import contextlib
import numpy as np


def led_color():
    pass

def detect_LED(frame):
    image = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    # Convert grayscale image to binary using a threshold
    _, binary_image = cv2.threshold(image, 40, 255, cv2.THRESH_BINARY)

    kernel = np.ones((3, 3), np.uint8)  # 3x3 structuring element
    dilated = cv2.dilate(binary_image, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1)
    dilated = cv2.dilate(eroded, kernel, iterations=1)

    circles = cv2.HoughCircles(
        dilated,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=2,
        param1=10,
        param2=9,
        minRadius=6,
        maxRadius=10
    )

    if circles is not None:
        circles = np.uint16(np.around(circles))
        for i in circles[0, :]:
            center = (i[0], i[1])
            radius = i[2]
            cv2.circle(frame, center, 1, (0, 255, 0), 2)  # Green center
            cv2.circle(frame, center, radius, (0, 0, 255), 2)  # Red outline
    return frame


#Rectangle for Camera 1 is between (303, 154) and (1453, 816)
#Rectangle for Camera 2 is between (503, 115) and (1517, 819)
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
    cam_rgb.initialControl.setBrightness(-5) #-10 .. 10
    cam_rgb.initialControl.setManualWhiteBalance(1000)#1000..12000
    xout_rgb = pipeline.create(dai.node.XLinkOut)
    xout_rgb.setStreamName("rgb")
    cam_rgb.video.link(xout_rgb.input)
    return pipeline

def main():
    with contextlib.ExitStack() as stack:
        device_infos = dai.Device.getAllAvailableDevices()[:2]
        if len(device_infos) < 2:
            raise RuntimeError(f"Only {len(device_infos)} camera(s) detected. Two cameras required.")

        q_rgb_map = []
        usb_speed = dai.UsbSpeed.SUPER

        for i, device_info in enumerate(device_infos):
            device = stack.enter_context(dai.Device(create_pipeline(), device_info, usb_speed))
            q_rgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            stream_name = f"Camera {i+1}"
            q_rgb_map.append((q_rgb, stream_name))

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
                        
                        if stream_name == "Camera 1":  # (303, 154) and (1453, 816)
                            frame = frame[150:820, 300:1460]
                        elif stream_name == "Camera 2":  # (503, 115) and (1517, 819)
                            frame = frame[115:820, 500:1517]
                        frame= detect_LED(frame)  # Detect LED in the frame
                        frames[stream_name] = frame
                        cv2.imshow(stream_name, frame)
                        cv2.imwrite(f"{stream_name}.png", frame)  # Save individual frames for inspection

                if len(frames) == 2:  # Ensure both frames are available
                    frame2 = frames["Camera 1"]
                    frame1 = frames["Camera 2"]

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
                    print(f"Frame1 shape: {frame1.shape}, Frame2 shape: {frame2.shape}, Combined shape: {combined_frame.shape}")

                    # Resize combined frame to fit display (adjust target_width based on your screen)
                    target_width = 1280  # Adjust to your screen resolution (e.g., 1920 for 1920x1080)
                    combined_h, combined_w = combined_frame.shape[:2]
                    if combined_w > target_width:
                        scale = target_width / combined_w
                        target_height = int(combined_h * scale)
                        combined_frame = cv2.resize(combined_frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
                        print(f"Resized combined frame to: {combined_frame.shape}")

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