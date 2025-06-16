# LED Test Controller - Modern Web GUI

A modern, web-based graphical user interface for the LED Test Controller system. This implementation provides all the functionality of the original controller with an attractive, browser-based interface.

## ✨ Features

### 🎯 Core Functionality
- **Complete LED Testing Automation**: All original controller functionality preserved
- **COM Port Management**: Easy selection and management of serial ports
- **Detection Server Control**: Start/stop the LED detection server
- **Live Camera Feed**: Real-time display of LED detection feed
- **Console Output**: Real-time display of test progress and logs
- **User Interaction**: Web-based input for test responses (Yes/No/Skip/Exit)

### 🎨 Modern Interface
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Real-time Updates**: WebSocket-based real-time communication
- **Status Indicators**: Visual status indicators for all system components
- **Modern Styling**: Glass morphism effects and gradient backgrounds
- **Interactive Elements**: Hover effects and smooth transitions
- **Dark Console**: Terminal-style console with color-coded messages

### 🚀 Enhanced User Experience
- **Auto-launch Browser**: Automatically opens in your default browser
- **Keyboard Shortcuts**: Quick response keys (Y/N/S/E) when input is required
- **Visual Feedback**: Loading states and success/error notifications
- **Smooth Animations**: Fade-in effects and pulse animations
- **Modal Dialogs**: Clean notifications for important events

## 📋 Requirements

- **Python 3.8+**
- **Windows 10/11** (tested on Windows 10)
- **Compatible COM Port** for device communication
- **DepthAI Camera** for LED detection (via server)

## 🚀 Quick Start

### Method 1: Double-click to Start (Recommended)
1. Simply double-click `start_gui.bat`
2. The application will automatically:
   - Check Python version
   - Install missing dependencies
   - Start the web server
   - Open your browser to the interface

### Method 2: Manual Start
1. Open Command Prompt or PowerShell
2. Navigate to the `modern_web_gui` folder
3. Run: `python start_gui.py`

### Method 3: Advanced Users
```bash
# Install dependencies manually
pip install -r requirements.txt

# Start the web server directly
python main.py
```

## 🖥️ Web Interface Guide

### Header
- **System Status**: Overall system status indicator
- **Title**: LED Test Controller branding

### Main Content Area

#### 📹 Live Detection Feed (Left Panel)
- **Camera Status**: Shows if detection server is running
- **Live Feed**: Real-time camera feed from detection server
- **Placeholder**: Helpful message when camera is offline

#### 🎛️ Control Panel (Right Panel)

##### Detection Server
- **Status Indicator**: Green (running) / Red (stopped)
- **Start/Stop Buttons**: Control the LED detection server
- **Real-time Status**: Updates automatically

##### COM Port Selection
- **Dropdown**: Lists all available COM ports
- **Refresh Button**: Reload available ports
- **Auto-selection**: Remembers last selected port

##### Test Controls
- **Status Display**: Current test status and step
- **Start Test**: Begin automated LED testing
- **Stop Test**: Emergency stop for running tests
- **Smart Validation**: Only enables when prerequisites are met

##### User Input Panel (Auto-appears)
- **Dynamic Prompt**: Shows current question from test
- **Response Buttons**: Yes/No/Skip/Exit options
- **Keyboard Support**: Y/N/S/E keys for quick response
- **Visual Highlighting**: Pulses to draw attention

#### 📺 Console Output (Bottom Panel)
- **Real-time Logs**: All system messages and test progress
- **Color Coding**: 
  - 🟢 Success messages (green)
  - 🔴 Error messages (red)
  - 🟡 Warning messages (yellow)
  - 🔵 Info messages (blue)
  - 🟠 Input required (orange)
- **Auto-scroll**: Keeps latest messages visible
- **Clear Button**: Clear console history
- **Timestamps**: All messages include time stamps

## 🔧 How It Works

### System Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│  FastAPI Server  │◄──►│  LED Detection  │
│   (Frontend)    │    │   (Backend)      │    │     Server      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Controller     │
                       │   (Serial Comm)  │
                       └──────────────────┘
```

### Workflow
1. **Start Web GUI**: Launch the modern web interface
2. **Start Detection Server**: Begin LED detection camera server
3. **Select COM Port**: Choose the serial port for device communication
4. **Start Test**: Initiate the automated LED testing process
5. **Monitor Progress**: Watch real-time console output and camera feed
6. **Respond to Prompts**: Use web interface to answer test questions
7. **View Results**: See test completion and any failed LED reports

## 🎯 Usage Instructions

### Initial Setup
1. **Start the Application**
   - Double-click `start_gui.bat` or run `python start_gui.py`
   - Browser will open automatically to `http://localhost:8080`

2. **Start Detection Server**
   - Click the green "Start Server" button
   - Wait for status to show "Running"
   - Camera feed should appear

3. **Select COM Port**
   - Choose your device's COM port from dropdown
   - Click "Refresh" if your port doesn't appear
   - "Start Test" button will enable when server is running and port is selected

### Running Tests
1. **Start Test**
   - Click the green "Start Test" button
   - Test will begin automatically

2. **Monitor Progress**
   - Watch console output for real-time progress
   - Camera feed shows current LED detection
   - Status updates show current test step

3. **Respond to Prompts**
   - User input panel appears when response needed
   - Click buttons or use keyboard shortcuts:
     - `Y` = Yes
     - `N` = No  
     - `S` = Skip
     - `E` = Exit (when available)

4. **View Results**
   - Test completion messages in console
   - Success/failure notifications
   - Image files saved to `test_results` folder

### LED Color Testing
The system automatically handles:
- **Red LED Test**: Checks if all LEDs show red
- **Green LED Test**: Checks if all LEDs show green  
- **Blue LED Test**: Checks if all ETH LEDs show blue
- **Manual Tests**: Prompts user for other test confirmations

## 🐛 Troubleshooting

### Common Issues

#### "Failed to start detection server"
- **Cause**: Camera not connected or server files missing
- **Solution**: Check camera connection and ensure `server/led_detection_server.py` exists

#### "No COM ports found"
- **Cause**: Device not connected or drivers not installed
- **Solution**: Check device connection and install proper USB drivers

#### "Connection error" messages
- **Cause**: Network/communication issues
- **Solution**: Restart the application, check firewall settings

#### Browser doesn't open automatically
- **Cause**: Default browser not set or permission issues
- **Solution**: Manually navigate to `http://localhost:8080`

#### "Module not found" errors
- **Cause**: Missing Python dependencies
- **Solution**: Run `pip install -r requirements.txt`

### Performance Tips
- **Close other applications** that might use the camera
- **Use Chrome/Edge browsers** for best performance
- **Check system resources** if interface becomes slow
- **Restart application** if WebSocket connection issues occur

## 🔌 API Endpoints

The web GUI provides a REST API for advanced users:

```
GET  /                          # Main web interface
GET  /api/com-ports            # Get available COM ports  
POST /api/server/start         # Start detection server
POST /api/server/stop          # Stop detection server
GET  /api/server/status        # Get server status
POST /api/test/start           # Start LED test
POST /api/test/stop            # Stop LED test
GET  /api/test/status          # Get test status
POST /api/test/respond         # Send user response
GET  /api/console/messages     # Get console messages
POST /api/console/clear        # Clear console
WS   /ws                       # WebSocket for real-time updates
```

## 📁 File Structure

```
modern_web_gui/
├── main.py                 # Main FastAPI server
├── start_gui.py           # Startup script
├── start_gui.bat          # Windows batch launcher  
├── requirements.txt       # Python dependencies
├── README.md             # This documentation
├── templates/
│   └── index.html        # Main web interface
└── static/
    └── js/
        └── main.js       # Frontend JavaScript
```

## 🎨 Customization

### Styling
- Edit `templates/index.html` CSS variables to change colors
- Modify gradient backgrounds in the `:root` section
- Adjust animations and transitions

### Functionality  
- Extend `main.py` to add new API endpoints
- Modify `static/js/main.js` for frontend behavior
- Add new features to the `ModernLEDTestController` class

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review console output for error messages
3. Ensure all dependencies are properly installed
4. Verify hardware connections (camera, device, COM port)

## 📝 Changelog

### Version 1.0.0
- Initial release
- Complete controller functionality in web interface
- Real-time WebSocket communication
- Modern responsive design
- Auto-launch browser capability
- Comprehensive error handling
- Keyboard shortcuts support

## 🏗️ Technical Details

### Technologies Used
- **Backend**: FastAPI, Python 3.8+
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Tailwind CSS, Custom CSS
- **Icons**: Font Awesome 6
- **Communication**: WebSockets, REST API
- **Hardware**: Serial communication, DepthAI cameras

### Browser Compatibility
- ✅ Chrome 90+
- ✅ Edge 90+
- ✅ Firefox 88+  
- ✅ Safari 14+
- ⚠️ Internet Explorer not supported

---

**🔬 LED Test Controller - Modern Web GUI**  
*Making LED testing beautiful and efficient* ✨ 