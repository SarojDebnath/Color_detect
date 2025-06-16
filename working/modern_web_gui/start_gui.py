#!/usr/bin/env python3
"""
Startup script for LED Test Controller - Modern Web GUI
This script handles dependency installation and launches the web interface.
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        input("Press Enter to exit...")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
## INstalling the dependencie
def install_dependencies():
    """Install required dependencies"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        input("Press Enter to exit...")
        sys.exit(1)
    
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("Try running: pip install -r requirements.txt")
        input("Press Enter to exit...")
        sys.exit(1)

def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        'fastapi', 'uvicorn', 'requests', 'serial', 'pydantic'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Missing modules: {', '.join(missing_modules)}")
        print("Installing missing dependencies...")
        install_dependencies()
    else:
        print("✅ All dependencies are available")

def start_web_gui():
    """Start the web GUI"""
    main_file = Path(__file__).parent / "main.py"
    
    if not main_file.exists():
        print("❌ main.py not found!")
        input("Press Enter to exit...")
        sys.exit(1)
    
    print("🚀 Starting LED Test Controller - Modern Web GUI...")
    print("=" * 60)
    print("🌐 Web Interface will open automatically in your browser")
    print("📝 Console output will appear below")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        # Import and run main
        sys.path.insert(0, str(Path(__file__).parent))
        from main import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

def main():
    """Main startup function"""
    print("🔬 LED Test Controller - Modern Web GUI")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Check and install dependencies
    check_dependencies()
    
    # Start the web GUI
    start_web_gui()

if __name__ == "__main__":
    main() 