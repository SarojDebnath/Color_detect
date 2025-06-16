import requests
import time

# Check server status
response = requests.get("http://localhost:8000/status")
print("Server status:", response.json())

# Wait a bit for samples to collect
time.sleep(2)

# Get LED colors lookup table
response = requests.get("http://localhost:8000/led_colors")
led_colors = response.json()["led_colors"]
print(f"Total LEDs with colors: {len(led_colors)}")

# Get combined image
response = requests.get("http://localhost:8000/combined_image")
with open("current_image.jpg", "wb") as f:
    f.write(response.content)
print("Saved current_image.jpg")

# Get best image (with max LEDs detected)
response = requests.get("http://localhost:8000/best_image")
with open("best_image.jpg", "wb") as f:
    f.write(response.content)
print("Saved best_image.jpg")

# Get best image info
response = requests.get("http://localhost:8000/best_image_info")
best_info = response.json()
print(f"Best image: {best_info['led_count']} LEDs detected, {best_info['age_seconds']:.1f} seconds old")

# Check if all LEDs are red
response = requests.get("http://localhost:8000/check_red_leds")
red_check = response.json()
print(f"\nRED LED CHECK:")
print(f"All LEDs red: {red_check['all_leds_red']}")

'''
print(f"Red LEDs: {red_check['red_leds_count']}/{red_check['total_leds']}")
if red_check['non_red_leds']:
    print(f"Non-red LEDs ({len(red_check['non_red_leds'])}):")
    for led in red_check['non_red_leds']:  # Show ALL non-red LEDs
        print(f"  {led['led_id']}: {led['color']}")
'''

# Check if all LEDs are green
response = requests.get("http://localhost:8000/check_green_leds")
green_check = response.json()
print(f"\nGREEN LED CHECK:")
print(f"All LEDs green: {green_check['all_leds_green']}")

'''
print(f"Green LEDs: {green_check['green_leds_count']}/{green_check['total_leds']}")
if green_check['non_green_leds']:
    print(f"Non-green LEDs ({len(green_check['non_green_leds'])}):")
    for led in green_check['non_green_leds']:  # Show ALL non-green LEDs
        print(f"  {led['led_id']}: {led['color']}")
'''
# Check if all eth LEDs are blue
response = requests.get("http://localhost:8000/check_blue_leds")
blue_check = response.json()
print(f"\nBLUE LED CHECK (ETH only):")
print(f"All eth LEDs blue: {blue_check['all_eth_leds_blue']}")
'''
print(f"Blue eth LEDs: {blue_check['blue_leds_count']}/{blue_check['total_eth_leds']}")
if blue_check['non_blue_leds']:
    print(f"Non-blue eth LEDs ({len(blue_check['non_blue_leds'])}):")
    for led in blue_check['non_blue_leds']:  # Show ALL non-blue eth LEDs
        print(f"  {led['led_id']}: {led['color']}")
print(f"Eth LEDs checked: {blue_check['eth_leds_checked']}")
'''
# Check for undetected LEDs
response = requests.get("http://localhost:8000/check_undetected_leds")
undetected_check = response.json()
print(f"\nLED DETECTION CHECK:")
print(f"All LEDs detected well: {undetected_check['all_leds_detected_well']}")
print(f"Detection rate: {undetected_check['detection_rate']:.1f}%")
print(f"Well detected: {undetected_check['well_detected_count']}/{undetected_check['total_configured_leds']}")

if undetected_check['never_detected']:
    print(f"Never detected LEDs ({undetected_check['never_detected_count']}):")
    for led in undetected_check['never_detected']:
        print(f"  {led}")

if undetected_check['poorly_detected']:
    print(f"Poorly detected LEDs ({undetected_check['poorly_detected_count']}):")
    for led in undetected_check['poorly_detected']:
        print(f"  {led['led_id']}: {led['sample_count']} samples")