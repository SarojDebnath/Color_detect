import requests
import json
import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

# Server configuration
SERVER_URL = "http://localhost:8000"

def get_server_status():
    """Get server status"""
    try:
        response = requests.get(f"{SERVER_URL}/status")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting status: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None

def get_combined_image():
    """Get the combined camera image"""
    try:
        response = requests.get(f"{SERVER_URL}/combined_image")
        if response.status_code == 200:
            # Save the image
            with open("combined_image_from_server.jpg", "wb") as f:
                f.write(response.content)
            print("Combined image saved as 'combined_image_from_server.jpg'")
            return True
        else:
            print(f"Error getting combined image: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error getting combined image: {e}")
        return False

def get_combined_image_base64():
    """Get the combined camera image as base64"""
    try:
        response = requests.get(f"{SERVER_URL}/combined_image_base64")
        if response.status_code == 200:
            data = response.json()
            # Decode base64 image
            img_data = base64.b64decode(data["image"])
            img = Image.open(BytesIO(img_data))
            img.save("combined_image_base64.jpg")
            print("Base64 image saved as 'combined_image_base64.jpg'")
            return True
        else:
            print(f"Error getting base64 image: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error getting base64 image: {e}")
        return False

def get_all_led_status():
    """Get status of all LEDs"""
    try:
        response = requests.get(f"{SERVER_URL}/led_status")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting LED status: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting LED status: {e}")
        return None

def get_led_colors_only():
    """Get only LED colors (simplified response)"""
    try:
        response = requests.get(f"{SERVER_URL}/led_colors")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting LED colors: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting LED colors: {e}")
        return None

def get_specific_led_status(led_id):
    """Get status of a specific LED"""
    try:
        response = requests.get(f"{SERVER_URL}/led_status/{led_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting LED {led_id} status: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting LED {led_id} status: {e}")
        return None

def clear_all_samples():
    """Clear all LED color samples"""
    try:
        response = requests.post(f"{SERVER_URL}/clear_samples")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error clearing samples: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error clearing samples: {e}")
        return None

def main():
    print("LED Detection Server Client Example")
    print("=" * 40)
    
    # Check server status
    print("1. Checking server status...")
    status = get_server_status()
    if status:
        print(f"   Server Status: {json.dumps(status, indent=2)}")
    else:
        print("   Server is not responding. Make sure it's running.")
        return
    
    # Get combined image
    print("\n2. Getting combined image...")
    if get_combined_image():
        print("   ✓ Combined image retrieved successfully")
    
    # Get combined image as base64
    print("\n3. Getting combined image as base64...")
    if get_combined_image_base64():
        print("   ✓ Base64 image retrieved successfully")
    
    # Get all LED status
    print("\n4. Getting all LED status...")
    led_status = get_all_led_status()
    if led_status:
        print(f"   Total LEDs: {led_status['total_leds']}")
        print("   LED Status (first 5):")
        count = 0
        for led_id, status in led_status['led_status'].items():
            if count >= 5:
                break
            print(f"     {led_id}: {status['color']} (samples: {status['sample_count']})")
            count += 1
    
    # Get simplified LED colors
    print("\n5. Getting LED colors only...")
    led_colors = get_led_colors_only()
    if led_colors:
        print(f"   LEDs with color data: {len(led_colors['led_colors'])}")
        print("   LED Colors (first 5):")
        count = 0
        for led_id, color in led_colors['led_colors'].items():
            if count >= 5:
                break
            print(f"     {led_id}: {color}")
            count += 1
    
    # Get specific LED status
    print("\n6. Getting specific LED status (pon1)...")
    specific_led = get_specific_led_status("pon1")
    if specific_led:
        print(f"   LED pon1 Status: {json.dumps(specific_led, indent=2)}")
    
    print("\n7. Example usage patterns:")
    print("   - Use /combined_image for getting the current camera view")
    print("   - Use /led_colors for quick LED color lookup")
    print("   - Use /led_status for detailed LED information")
    print("   - Use /led_status/{led_id} for specific LED details")
    print("   - Colors are determined by mode of last 10 samples")

if __name__ == "__main__":
    main() 