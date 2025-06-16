import serial
import time
import requests
import os
import re
from datetime import datetime
from colorama import Fore, Back, Style, init
import threading

# Initialize colorama for colored output
init(autoreset=True)

class LEDTestController:
    def __init__(self, port="COM13", baudrate=115200, server_url="http://localhost:8000"):
        self.port = port
        self.baudrate = baudrate
        self.server_url = server_url
        self.serial_conn = None
        self.current_serial_number = None
        self.results_folder = "test_results"
        
        # Create results folder if it doesn't exist
        if not os.path.exists(self.results_folder):
            os.makedirs(self.results_folder)
    
    def connect_serial(self):
        """Connect to the serial port"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=30,
                write_timeout=30
            )
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except Exception as e:
            print(f"Failed to connect to serial port: {e}")
            return False
    
    def send_command(self, command, wait_time=2):
        """Send command to serial and wait"""
        if self.serial_conn:
            print(f"Sending: {command}")
            self.serial_conn.write(command.encode('utf-8') + b'\r\n')
            self.serial_conn.flush()
            time.sleep(wait_time)
    
    def read_serial_output(self, timeout=30):
        """Read serial output until timeout"""
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.serial_conn.in_waiting > 0:
                try:
                    data = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')
                    output += data
                    print(data, end='', flush=True)
                    
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
                    break
            time.sleep(0.05)  # Shorter sleep for more responsive reading
        
        return output
    
    def login_to_device(self):
        """Login to the Linux device"""
        print("Initiating login process...")
        
        # Send enter to trigger login prompt
        self.send_command("")
        output = self.read_serial_output(10)
        
        # Send username
        if "login:" in output.lower():
            print("Sending username...")
            self.send_command("hsvroot")
            output = self.read_serial_output(10)
        
        # Send password
        if "password:" in output.lower():
            print("Sending password...")
            self.send_command("BOSCO")
            output = self.read_serial_output(10)
        
        # Wait for shell prompt
        time.sleep(3)
        return True
    
    def setup_and_run_test(self):
        """Setup USB mount and run the LED test script"""
        print("Setting up USB and running LED test...")
        
        # Create USB directory
        self.send_command("mkdir usb", 2)
        
        # Mount USB
        self.send_command("mount /dev/sdb1 ./usb", 3)
        
        # Run the LED test script
        self.send_command("python usb/1340_test_led_automated_correct.py", 5)
        
        return True
    
    def check_led_colors_via_server(self, color):
        """Check LED colors using the server endpoints"""
        try:
            if color.lower() == "red":
                response = requests.get(f"{self.server_url}/check_red_leds", timeout=10)
                result = response.json()
                # Combine non-red LEDs and undetected LEDs
                failed_leds = result.get("non_red_leds", [])
                # Add undetected LEDs as "not detected"
                for led_id in result.get("no_data_leds", []):
                    failed_leds.append({"led_id": led_id, "color": None})
                return result["all_leds_red"], failed_leds
                
            elif color.lower() == "green":
                response = requests.get(f"{self.server_url}/check_green_leds", timeout=10)
                result = response.json()
                # Combine non-green LEDs and undetected LEDs
                failed_leds = result.get("non_green_leds", [])
                # Add undetected LEDs as "not detected"
                for led_id in result.get("no_data_leds", []):
                    failed_leds.append({"led_id": led_id, "color": None})
                return result["all_leds_green"], failed_leds
                
            elif color.lower() == "blue":
                response = requests.get(f"{self.server_url}/check_blue_leds", timeout=10)
                result = response.json()
                # Combine non-blue LEDs and undetected LEDs
                failed_leds = result.get("non_blue_leds", [])
                # Add undetected LEDs as "not detected"
                for led_id in result.get("no_data_leds", []):
                    failed_leds.append({"led_id": led_id, "color": None})
                return result["all_eth_leds_blue"], failed_leds
                
        except Exception as e:
            print(f"Error checking {color} LEDs via server: {e}")
            return False, []
        
        return False, []
    
    def save_current_image_async(self, color, serial_number):
        """Save the optimal image using multi-frame analysis (non-blocking)"""
        def save_image():
            try:
                # First try to get the optimal frame (best quality from recent frames)
                optimal_response = requests.get(f"{self.server_url}/optimal_frame", timeout=10)
                
                if optimal_response.status_code == 200:
                    # Get quality metrics from headers
                    led_count = optimal_response.headers.get('X-LED-Count', 'unknown')
                    quality_score = optimal_response.headers.get('X-Quality-Score', 'unknown')
                    frame_age = optimal_response.headers.get('X-Frame-Age', 'unknown')
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{serial_number}_{color}_{timestamp}_optimal.jpg"
                    filepath = os.path.join(self.results_folder, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(optimal_response.content)
                    
                    print(f"📸 Saved optimal image: {filename}")
                    print(f"   📊 Quality metrics: {led_count} LEDs, score {quality_score}, {frame_age}s old")
                    
                else:
                    # Fallback to current combined image if optimal frame not available
                    print(f"⚠️ Optimal frame not available ({optimal_response.status_code}), using current image")
                    response = requests.get(f"{self.server_url}/combined_image", timeout=10)
                    
                    if response.status_code == 200:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{serial_number}_{color}_{timestamp}.jpg"
                        filepath = os.path.join(self.results_folder, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        print(f"📸 Saved current image: {filename}")
                    else:
                        print(f"❌ Failed to get any image: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error saving image: {e}")
        
        # Start image saving in background thread
        thread = threading.Thread(target=save_image, daemon=True)
        thread.start()
        print(f"📸 Saving optimal {color} image using multi-frame analysis...")
        return thread
    
    def extract_serial_number(self, text):
        """Extract serial number from the output"""
        # Look for patterns like "LBADTN2409AA250"
        pattern = r'(LB[A-Z0-9]+)'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None
    
    def display_current_image(self):
        """Just log that image check happened - display is on server"""
        print("(Image being displayed on server window)")
    
    def run_automated_test(self):
        """Run the complete automated LED test"""
        print("Starting automated LED test...")
        
        if not self.connect_serial():
            return False
        
        try:
            # Login to device
            if not self.login_to_device():
                print("Failed to login")
                return False
            
            # Setup and run test
            if not self.setup_and_run_test():
                print("Failed to start test")
                return False
            
            # Monitor test execution
            test_output = ""
            failed_colors = []
            
            while True:
                output = self.read_serial_output(60)
                test_output += output
                
                # Extract serial number if found
                if not self.current_serial_number:
                    sn = self.extract_serial_number(output)
                    if sn:
                        self.current_serial_number = sn
                        print(f"Detected Serial Number: {sn}")
                
                # Handle LED color questions - wait for complete prompt
                if "[yes/no/skip]:" in output.lower() or "[yes/no/skip/exit]:" in output.lower():
                    
                    if "are all the leds red?" in output.lower():
                        print("\n=== RED LED CHECK ===")
                        time.sleep(2)  # Give time for LED server to stabilize
                        print("Displaying current image...")
                        self.display_current_image()
                        
                        # Check detection status
                        try:
                            debug_response = requests.get(f"{self.server_url}/debug_colors", timeout=15)
                            debug_data = debug_response.json()
                            print(f"{Fore.RED}RED TEST - {debug_data['color_summary']['red']}/{debug_data['total_detected']} LEDs are red{Style.RESET_ALL}")
                            
                            # Check for undetected LEDs
                            undetected_response = requests.get(f"{self.server_url}/check_undetected_leds", timeout=15)
                            undetected_data = undetected_response.json()
                            if undetected_data['never_detected']:
                                print(f"{Fore.MAGENTA}⚠ UNDETECTED LEDs: {undetected_data['never_detected']}{Style.RESET_ALL}")
                            if undetected_data['poorly_detected']:
                                poorly = [f"{led['led_id']}({led['sample_count']})" for led in undetected_data['poorly_detected']]
                                print(f"{Fore.YELLOW}⚠ POORLY DETECTED LEDs: {poorly}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}ERROR: Could not get LED detection status - {str(e)}{Style.RESET_ALL}")
                        
                        all_red, failed_red_data = self.check_led_colors_via_server("red")
                        self.save_current_image_async("red", self.current_serial_number or "unknown")
                        
                        if all_red:
                            print(f"{Fore.GREEN}{Back.BLACK}✓ PASS: All LEDs are RED{Style.RESET_ALL}")
                            self.send_command("yes", wait_time=3)
                        else:
                            total_failed = len(failed_red_data)
                            print(f"{Fore.RED}{Back.BLACK}✗ FAIL: Found {total_failed} non-red LEDs{Style.RESET_ALL}")
                            for led in failed_red_data[:5]:  # Show first 5 failed LEDs
                                if led['color'] is None:
                                    color_display = f"{Fore.YELLOW}❌ not detected{Style.RESET_ALL}"
                                else:
                                    color_display = f"{Fore.MAGENTA}{led['color']}{Style.RESET_ALL}"
                                print(f"  {Fore.YELLOW}• {led['led_id']}: {color_display}{Style.RESET_ALL}")
                            if len(failed_red_data) > 5:
                                print(f"  {Fore.YELLOW}... and {len(failed_red_data)-5} more{Style.RESET_ALL}")
                            failed_colors.append(("red", failed_red_data))
                            self.send_command("no", wait_time=3)
                    
                    elif "are all the leds green?" in output.lower():
                        print("\n=== GREEN LED CHECK ===")
                        print("Waiting for LEDs to change to green...")
                        time.sleep(3)  # Give time for LEDs to change to green
                        print("Displaying current image...")
                        self.display_current_image()
                        
                        # Check detection status
                        try:
                            debug_response = requests.get(f"{self.server_url}/debug_colors", timeout=15)
                            debug_data = debug_response.json()
                            print(f"{Fore.GREEN}GREEN TEST - {debug_data['color_summary']['green']}/{debug_data['total_detected']} LEDs are green{Style.RESET_ALL}")
                            
                            # Check for undetected LEDs
                            undetected_response = requests.get(f"{self.server_url}/check_undetected_leds", timeout=15)
                            undetected_data = undetected_response.json()
                            if undetected_data['never_detected']:
                                print(f"{Fore.MAGENTA}⚠ UNDETECTED LEDs: {undetected_data['never_detected']}{Style.RESET_ALL}")
                            if undetected_data['poorly_detected']:
                                poorly = [f"{led['led_id']}({led['sample_count']})" for led in undetected_data['poorly_detected']]
                                print(f"{Fore.YELLOW}⚠ POORLY DETECTED LEDs: {poorly}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}ERROR: Could not get LED detection status - {str(e)}{Style.RESET_ALL}")
                        
                        all_green, failed_green_data = self.check_led_colors_via_server("green")
                        self.save_current_image_async("green", self.current_serial_number or "unknown")
                        
                        if all_green:
                            print(f"{Fore.GREEN}{Back.BLACK}✓ PASS: All LEDs are GREEN{Style.RESET_ALL}")
                            self.send_command("yes", wait_time=3)
                        else:
                            total_failed = len(failed_green_data)
                            print(f"{Fore.RED}{Back.BLACK}✗ FAIL: Found {total_failed} non-green LEDs{Style.RESET_ALL}")
                            for led in failed_green_data[:5]:  # Show first 5 failed LEDs
                                if led['color'] is None:
                                    color_display = f"{Fore.YELLOW}❌ not detected{Style.RESET_ALL}"
                                else:
                                    color_display = f"{Fore.MAGENTA}{led['color']}{Style.RESET_ALL}"
                                print(f"  {Fore.YELLOW}• {led['led_id']}: {color_display}{Style.RESET_ALL}")
                            if len(failed_green_data) > 5:
                                print(f"  {Fore.YELLOW}... and {len(failed_green_data)-5} more{Style.RESET_ALL}")
                            failed_colors.append(("green", failed_green_data))
                            self.send_command("no", wait_time=3)
                    
                    elif "are all the leds blue?" in output.lower():
                        print("\n=== BLUE LED CHECK ===")
                        print("Waiting for LEDs to change to blue...")
                        time.sleep(5)  # Wait longer for LEDs to actually change to blue
                        
                        # Display current image to see LEDs
                        print("Displaying current image...")
                        self.display_current_image()
                        
                        # Debug: Check what colors are actually being detected (BLUE TEST - ONLY ETH LEDs matter)
                        try:
                            debug_response = requests.get(f"{self.server_url}/debug_colors", timeout=15)
                            debug_data = debug_response.json()
                            print(f"{Fore.CYAN}BLUE TEST - Only checking ETH LEDs (ignoring PON/other LEDs){Style.RESET_ALL}")
                            print(f"{Fore.CYAN}ETH LEDs detected: {debug_data['eth_blue_count']}/{debug_data['eth_leds_total']} are blue{Style.RESET_ALL}")
                            
                            # Check for undetected LEDs
                            undetected_response = requests.get(f"{self.server_url}/check_undetected_leds", timeout=15)
                            undetected_data = undetected_response.json()
                            if undetected_data['never_detected']:
                                print(f"{Fore.MAGENTA}⚠ UNDETECTED LEDs: {undetected_data['never_detected']}{Style.RESET_ALL}")
                            if undetected_data['poorly_detected']:
                                poorly = [f"{led['led_id']}({led['sample_count']})" for led in undetected_data['poorly_detected']]
                                print(f"{Fore.YELLOW}⚠ POORLY DETECTED LEDs: {poorly}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}ERROR: Could not get LED detection status - {str(e)}{Style.RESET_ALL}")
                        
                        all_blue, failed_blue_data = self.check_led_colors_via_server("blue")
                        self.save_current_image_async("blue", self.current_serial_number or "unknown")
                        
                        if all_blue:
                            print(f"{Fore.BLUE}{Back.BLACK}✓ PASS: All ETH LEDs are BLUE{Style.RESET_ALL}")
                            self.send_command("yes", wait_time=3)
                        else:
                            total_failed = len(failed_blue_data)
                            print(f"{Fore.RED}{Back.BLACK}✗ FAIL: Found {total_failed} non-blue ETH LEDs{Style.RESET_ALL}")
                            for led in failed_blue_data[:5]:  # Show first 5 failed LEDs
                                if led['color'] is None:
                                    color_display = f"{Fore.YELLOW}❌ not detected{Style.RESET_ALL}"
                                else:
                                    color_display = f"{Fore.MAGENTA}{led['color']}{Style.RESET_ALL}"
                                print(f"  {Fore.YELLOW}• {led['led_id']}: {color_display}{Style.RESET_ALL}")
                            if len(failed_blue_data) > 5:
                                print(f"  {Fore.YELLOW}... and {len(failed_blue_data)-5} more{Style.RESET_ALL}")
                            failed_colors.append(("blue", failed_blue_data))
                            self.send_command("no", wait_time=3)
                    
                    else:
                        # For non-LED tests, ask user for input and send it
                        print(f"{Fore.CYAN}[MANUAL INPUT REQUIRED]{Style.RESET_ALL}")
                        # Extract the actual question/prompt
                        if "[yes/no/skip/exit]:" in output.lower():
                            prompt_text = output.split('[yes/no/skip/exit]:')[0].split('\n')[-1].strip()
                        else:
                            prompt_text = output.split('[yes/no/skip]:')[0].split('\n')[-1].strip()
                        print(f"{Fore.YELLOW}Prompt: {prompt_text}{Style.RESET_ALL}")
                        
                        # Determine available options from the prompt
                        if "[yes/no/skip/exit]:" in output.lower():
                            options = "yes/no/skip/exit"
                            valid_responses = ['yes', 'no', 'skip', 'exit']
                        else:
                            options = "yes/no/skip"
                            valid_responses = ['yes', 'no', 'skip']
                        
                        # Get user input
                        user_response = input(f"{Fore.CYAN}Enter your response ({options}): {Style.RESET_ALL}").strip().lower()
                        
                        # Validate response
                        if user_response in valid_responses:
                            print(f"Sending response: {user_response}")
                            self.send_command(user_response, wait_time=3)
                        else:
                            print(f"{Fore.RED}Invalid response. Sending 'skip' as default{Style.RESET_ALL}")
                            self.send_command("skip", wait_time=3)
                
                # Handle test retry questions
                elif "would you like to run this test again?" in output.lower() and "[yes/no/skip/exit]:" in output.lower():
                    print("Test asking to retry - Answering NO")
                    self.send_command("no", wait_time=3)
                
                # Check if test is complete
                if "test completed" in output.lower() or "please contact hw4" in output.lower():
                    print("\nTest completed!")
                    break
                
                # Check for timeout or error
                if "connection lost" in output.lower() or len(output) == 0:
                    print("Connection issue or timeout")
                    break
            
            # Cleanup
            print("Cleaning up...")
            self.send_command("umount ./usb", 2)
            self.send_command("rm -r usb", 2)
            
            # Handle failed color checks
            if failed_colors:
                print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.RED}{Back.BLACK}🔍 MANUAL VERIFICATION REQUIRED 🔍{Style.RESET_ALL}")
                print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}⚠️  The following LED color checks failed:{Style.RESET_ALL}")
                
                # Create a set to track unique failed LEDs and avoid duplicates
                unique_failed_leds = {}
                
                for color, failed_leds in failed_colors:
                    color_icon = {"red": "🔴", "green": "🟢", "blue": "🔵"}.get(color, "⚪")
                    print(f"\n{Fore.CYAN}{color_icon} {color.upper()} LEDs that failed:{Style.RESET_ALL}")
                    
                    for led in failed_leds[:10]:  # Show first 10
                        led_id = led['led_id']
                        led_color = led['color']
                        
                        # Avoid duplicates
                        if led_id not in unique_failed_leds:
                            unique_failed_leds[led_id] = led_color
                            
                            if led_color is None:
                                color_display = f"{Fore.YELLOW}❌ not detected{Style.RESET_ALL}"
                            else:
                                color_display = f"{Fore.MAGENTA}{led_color}{Style.RESET_ALL}"
                            
                            print(f"  {Fore.WHITE}• {led_id}: {color_display}{Style.RESET_ALL}")
                    
                    if len(failed_leds) > 10:
                        print(f"  {Fore.YELLOW}... and {len(failed_leds) - 10} more{Style.RESET_ALL}")
                
                print(f"\n{Fore.CYAN}📁 Please check the saved images in '{self.results_folder}' folder{Style.RESET_ALL}")
                print(f"{Fore.CYAN}🏷️  Serial Number: {self.current_serial_number}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}📊 Total unique failed LEDs: {len(unique_failed_leds)}{Style.RESET_ALL}")
                
                verify = input(f"\n{Fore.GREEN}🔍 Do you want to manually verify the images? (y/n): {Style.RESET_ALL}")
                if verify.lower() == 'y':
                    self.open_results_folder()
            
            else:
                # No failed colors - all tests passed!
                print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}{Back.BLACK}🎉 ALL LED TESTS PASSED! 🎉{Style.RESET_ALL}")
                print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}✅ All LED color tests completed successfully{Style.RESET_ALL}")
                print(f"{Fore.CYAN}🏷️  Serial Number: {self.current_serial_number}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}📁 Images saved in '{self.results_folder}' folder{Style.RESET_ALL}")
            
            return True
            
        except Exception as e:
            print(f"Error during automated test: {e}")
            return False
        
        finally:
            if self.serial_conn:
                self.serial_conn.close()
                print("Serial connection closed")
    
    def open_results_folder(self):
        """Open the results folder for manual verification"""
        try:
            os.startfile(self.results_folder)  # Windows
        except:
            try:
                os.system(f"xdg-open {self.results_folder}")  # Linux
            except:
                print(f"Please manually open folder: {self.results_folder}")

def main():
    print("LED Test Automation Controller")
    print("=" * 40)
    
    controller = LEDTestController()
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/status", timeout=5)
        print("✓ LED Detection Server is running")
        print(f"Server status: {response.json()}")
    except:
        print("✗ LED Detection Server is not running!")
        print("Please start the server first: python led_detection_server.py")
        return
    
    # Run the automated test
    success = controller.run_automated_test()
    
    if success:
        print("\n✓ Automated test completed successfully!")
    else:
        print("\n✗ Automated test failed!")

if __name__ == "__main__":
    main()