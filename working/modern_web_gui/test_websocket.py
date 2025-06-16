#!/usr/bin/env python3
"""
Simple test to verify WebSocket broadcasting works
"""

import asyncio
import time
import threading
from main import add_console_message, main_event_loop

def test_console_messages():
    """Test function to send console messages from a background thread"""
    time.sleep(2)  # Wait for server to start
    
    for i in range(5):
        add_console_message(f"Test message {i+1} from background thread", "info")
        time.sleep(1)
    
    add_console_message("🎉 Test completed! If you see this in the web console, WebSocket is working!", "success")

if __name__ == "__main__":
    print("Testing WebSocket broadcasting...")
    print("1. Start the web server: python start_gui.py")
    print("2. Open browser to http://localhost:8080")
    print("3. Run this test script: python test_websocket.py")
    print("4. Check if test messages appear in the web console")
    
    # Start test in background thread (simulating the controller thread)
    test_thread = threading.Thread(target=test_console_messages, daemon=True)
    test_thread.start()
    
    # Keep script alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Test stopped") 