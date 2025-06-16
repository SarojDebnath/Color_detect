// Global variables
let websocket = null;
let isTestRunning = false;
let isServerRunning = false;
let awaitingInput = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    loadComPorts();
    setupEventListeners();
    setupKeyboardShortcuts();
    setupComboBox();
});

// Initialize WebSocket connection
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function(event) {
        console.log('WebSocket connected');
        addConsoleMessage('🔌 Connected to server', 'success');
    };
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    websocket.onclose = function(event) {
        console.log('WebSocket disconnected');
        addConsoleMessage('🔌 Disconnected from server', 'warning');
        
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            initializeWebSocket();
        }, 5000);
    };
    
    websocket.onerror = function(error) {
        console.error('WebSocket error:', error);
        addConsoleMessage('❌ WebSocket error', 'error');
    };
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'server_status':
            updateServerStatus(data.data);
            break;
        case 'test_status':
            updateTestStatus(data.data);
            break;
        case 'console_message':
            addConsoleMessage(data.data.message, data.data.type, data.data.timestamp);
            break;
        case 'console_messages':
            loadConsoleMessages(data.data.messages);
            break;
        case 'console_clear':
            clearConsoleDisplay();
            break;
    }
}

// Setup combo box functionality
function setupComboBox() {
    const input = document.getElementById('testProgram');
    const dropdown = document.getElementById('programDropdown');
    const dropdownBtn = document.getElementById('programDropdownBtn');
    
    // Toggle dropdown
    dropdownBtn.addEventListener('click', function(e) {
        e.preventDefault();
        dropdown.classList.toggle('hidden');
    });
    
    // Handle dropdown item selection
    dropdown.addEventListener('click', function(e) {
        if (e.target.tagName === 'DIV') {
            input.value = e.target.textContent;
            dropdown.classList.add('hidden');
        }
    });
    
    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.combo-box')) {
            dropdown.classList.add('hidden');
        }
    });
    
    // Hide dropdown when typing
    input.addEventListener('input', function() {
        dropdown.classList.add('hidden');
    });
}

// Load COM ports
async function loadComPorts() {
    try {
        const response = await fetch('/api/com-ports');
        const data = await response.json();
        
        const comPortSelect = document.getElementById('comPort');
        comPortSelect.innerHTML = '<option value="">Select COM Port</option>';
        
        data.ports.forEach(port => {
            const option = document.createElement('option');
            option.value = port;
            option.textContent = port;
            comPortSelect.appendChild(option);
        });
        
        // Enable start test button if server is running and port is selected
        updateStartTestButton();
        
    } catch (error) {
        console.error('Error loading COM ports:', error);
        addConsoleMessage('❌ Failed to load COM ports', 'error');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Server controls
    document.getElementById('startServer').addEventListener('click', startServer);
    document.getElementById('stopServer').addEventListener('click', stopServer);
    
    // Port controls
    document.getElementById('refreshPorts').addEventListener('click', loadComPorts);
    document.getElementById('comPort').addEventListener('change', updateStartTestButton);
    
    // Test controls
    document.getElementById('startTest').addEventListener('click', startTest);
    document.getElementById('stopTest').addEventListener('click', stopTest);
    
    // Console controls
    document.getElementById('clearConsole').addEventListener('click', clearConsole);
    
    // User input buttons
    document.getElementById('responseYes').addEventListener('click', () => sendResponse('yes'));
    document.getElementById('responseNo').addEventListener('click', () => sendResponse('no'));
    document.getElementById('responseSkip').addEventListener('click', () => sendResponse('skip'));
    document.getElementById('responseExit').addEventListener('click', () => sendResponse('exit'));
    
    // Manual text input
    document.getElementById('sendManualInput').addEventListener('click', sendManualResponse);
    document.getElementById('manualInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendManualResponse();
        }
    });
    
    // Modal controls
    document.getElementById('modalClose').addEventListener('click', closeModal);
}

// Setup keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Only handle shortcuts when awaiting input
        if (!awaitingInput) return;
        
        // Handle button responses
        if (!document.getElementById('userInputPanel').classList.contains('hidden')) {
            switch(e.key.toLowerCase()) {
                case 'y':
                    e.preventDefault();
                    sendResponse('yes');
                    break;
                case 'n':
                    e.preventDefault();
                    sendResponse('no');
                    break;
                case 's':
                    e.preventDefault();
                    sendResponse('skip');
                    break;
                case 'e':
                    if (!document.getElementById('responseExit').classList.contains('hidden')) {
                        e.preventDefault();
                        sendResponse('exit');
                    }
                    break;
            }
        }
    });
}

// Server control functions
async function startServer() {
    try {
        showLoading('Starting detection server...');
        
        const response = await fetch('/api/server/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.status === 'success') {
            addConsoleMessage('🚀 Detection server started successfully', 'success');
            setTimeout(() => {
                // Check for server status after a moment
                checkServerStatus();
            }, 2000);
        } else {
            addConsoleMessage(`❌ Failed to start server: ${result.message}`, 'error');
        }
        
    } catch (error) {
        hideLoading();
        console.error('Error starting server:', error);
        addConsoleMessage('❌ Network error starting server', 'error');
    }
}

async function stopServer() {
    try {
        showLoading('Stopping detection server...');
        
        const response = await fetch('/api/server/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.status === 'success') {
            addConsoleMessage('🛑 Detection server stopped', 'info');
        } else {
            addConsoleMessage(`❌ Failed to stop server: ${result.message}`, 'error');
        }
        
    } catch (error) {
        hideLoading();
        console.error('Error stopping server:', error);
        addConsoleMessage('❌ Network error stopping server', 'error');
    }
}

async function checkServerStatus() {
    try {
        const response = await fetch('/api/server/status');
        const data = await response.json();
        updateServerStatus(data);
    } catch (error) {
        console.error('Error checking server status:', error);
    }
}

// Test control functions
async function startTest() {
    const comPort = document.getElementById('comPort').value;
    const testProgram = document.getElementById('testProgram').value.trim();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    
    if (!comPort) {
        showModal('⚠️', 'Warning', 'Please select a COM port first.');
        return;
    }
    
    if (!testProgram) {
        showModal('⚠️', 'Warning', 'Please enter a test program name.');
        return;
    }
    
    if (!username) {
        showModal('⚠️', 'Warning', 'Please enter a username.');
        return;
    }
    
    if (!password) {
        showModal('⚠️', 'Warning', 'Please enter a password.');
        return;
    }
    
    try {
        showLoading('Starting LED test...');
        
        const response = await fetch('/api/test/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                com_port: comPort,
                test_program: testProgram,
                server_url: 'http://localhost:8000',
                username: username,
                password: password
            })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.status === 'success') {
            addConsoleMessage(`🚀 Test started on ${comPort} with ${testProgram} (user: ${username})`, 'success');
            isTestRunning = true;
            updateTestButtons();
        } else {
            addConsoleMessage(`❌ Failed to start test: ${result.message}`, 'error');
            showModal('❌', 'Error', result.message);
        }
        
    } catch (error) {
        hideLoading();
        console.error('Error starting test:', error);
        addConsoleMessage('❌ Network error starting test', 'error');
        showModal('❌', 'Error', 'Network error starting test');
    }
}

async function stopTest() {
    try {
        showLoading('Stopping test...');
        
        const response = await fetch('/api/test/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.status === 'success') {
            addConsoleMessage('🛑 Test stopped by user', 'warning');
            isTestRunning = false;
            awaitingInput = false;
            hideUserInputPanels();
            updateTestButtons();
        } else {
            addConsoleMessage(`❌ Failed to stop test: ${result.message}`, 'error');
        }
        
    } catch (error) {
        hideLoading();
        console.error('Error stopping test:', error);
        addConsoleMessage('❌ Network error stopping test', 'error');
    }
}

// User input functions
async function sendResponse(response) {
    if (!awaitingInput) return;
    
    try {
        const apiResponse = await fetch('/api/test/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ response: response })
        });
        
        const result = await apiResponse.json();
        
        if (result.status === 'success') {
            addConsoleMessage(`📤 Response sent: ${response.toUpperCase()}`, 'success');
            hideUserInputPanels();
            awaitingInput = false;
        } else {
            addConsoleMessage(`❌ Failed to send response: ${result.message}`, 'error');
        }
        
    } catch (error) {
        console.error('Error sending response:', error);
        addConsoleMessage('❌ Network error sending response', 'error');
    }
}

async function sendManualResponse() {
    const input = document.getElementById('manualInput');
    const response = input.value.trim();
    
    if (!response) {
        addConsoleMessage('⚠️ Please enter a response', 'warning');
        return;
    }
    
    if (!awaitingInput) return;
    
    try {
        const apiResponse = await fetch('/api/test/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ response: response })
        });
        
        const result = await apiResponse.json();
        
        if (result.status === 'success') {
            addConsoleMessage(`📤 Manual response sent: ${response}`, 'success');
            input.value = '';
            hideUserInputPanels();
            awaitingInput = false;
        } else {
            addConsoleMessage(`❌ Failed to send response: ${result.message}`, 'error');
        }
        
    } catch (error) {
        console.error('Error sending manual response:', error);
        addConsoleMessage('❌ Network error sending response', 'error');
    }
}

// Status update functions
function updateServerStatus(status) {
    isServerRunning = status.running;
    
    const statusIndicator = document.getElementById('serverStatus');
    const statusText = document.getElementById('serverStatusText');
    const startBtn = document.getElementById('startServer');
    const stopBtn = document.getElementById('stopServer');
    
    if (status.running) {
        statusIndicator.className = 'status-indicator online';
        statusText.textContent = `Server Status: Running (${status.cameras_connected} camera)`;
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        statusIndicator.className = 'status-indicator offline';
        statusText.textContent = 'Server Status: Not Running';
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
    
    updateStartTestButton();
    updateOverallStatus();
}

function updateTestStatus(status) {
    isTestRunning = status.running;
    awaitingInput = status.awaiting_input;
    
    const statusIndicator = document.getElementById('testStatus');
    const statusText = document.getElementById('testStatusText');
    const currentStep = document.getElementById('testCurrentStep');
    
    if (status.running) {
        statusIndicator.className = 'status-indicator online';
        statusText.textContent = 'Test Status: Running';
        currentStep.textContent = status.current_step;
    } else {
        statusIndicator.className = awaitingInput ? 'status-indicator warning' : 'status-indicator offline';
        statusText.textContent = awaitingInput ? 'Test Status: Awaiting Input' : 'Test Status: Ready';
        currentStep.textContent = status.current_step;
    }
    
    // Handle user input requirements
    if (status.awaiting_input) {
        showUserInputPanel(status.input_prompt, status.input_type || 'buttons');
    } else {
        hideUserInputPanels();
    }
    
    updateTestButtons();
    updateOverallStatus();
}

function updateOverallStatus() {
    const overallIndicator = document.getElementById('overallStatus');
    const overallText = document.getElementById('overallStatusText');
    
    if (isTestRunning) {
        overallIndicator.className = 'status-indicator online';
        overallText.textContent = awaitingInput ? 'Test Running - Input Required' : 'Test Running';
    } else if (isServerRunning) {
        overallIndicator.className = 'status-indicator warning';
        overallText.textContent = 'Server Ready - Awaiting Test';
    } else {
        overallIndicator.className = 'status-indicator offline';
        overallText.textContent = 'System Ready';
    }
}

function updateStartTestButton() {
    const startBtn = document.getElementById('startTest');
    const comPort = document.getElementById('comPort').value;
    
    startBtn.disabled = !isServerRunning || !comPort || isTestRunning;
}

function updateTestButtons() {
    const startBtn = document.getElementById('startTest');
    const stopBtn = document.getElementById('stopTest');
    
    startBtn.disabled = isTestRunning || !isServerRunning || !document.getElementById('comPort').value;
    stopBtn.disabled = !isTestRunning;
}

// User input panel functions
function showUserInputPanel(prompt, inputType = 'buttons') {
    hideUserInputPanels(); // Hide any existing panels first
    
    if (inputType === 'text') {
        // Show text input panel
        const textPanel = document.getElementById('textInputPanel');
        const textPrompt = document.getElementById('textInputPrompt');
        
        textPrompt.textContent = prompt;
        textPanel.classList.remove('hidden');
        textPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Focus on the input field
        setTimeout(() => {
            document.getElementById('manualInput').focus();
        }, 100);
        
    } else {
        // Show button input panel
        const panel = document.getElementById('userInputPanel');
        const promptElement = document.getElementById('inputPrompt');
        const exitBtn = document.getElementById('responseExit');
        
        promptElement.textContent = prompt;
        
        // Show/hide exit button based on prompt
        if (prompt.toLowerCase().includes('exit') || prompt.includes('[yes/no/skip/exit]')) {
            exitBtn.classList.remove('hidden');
        } else {
            exitBtn.classList.add('hidden');
        }
        
        panel.classList.remove('hidden');
        panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function hideUserInputPanels() {
    document.getElementById('userInputPanel').classList.add('hidden');
    document.getElementById('textInputPanel').classList.add('hidden');
}

// Console functions
function addConsoleMessage(message, type = 'info', timestamp = null) {
    const console = document.getElementById('consoleOutput');
    const line = document.createElement('div');
    line.className = `console-line ${type}`;
    
    const time = timestamp || new Date().toLocaleTimeString();
    line.innerHTML = `<span style="color: #888;">[${time}]</span> ${message}`;
    
    console.appendChild(line);
    console.scrollTop = console.scrollHeight;
}

function loadConsoleMessages(messages) {
    const console = document.getElementById('consoleOutput');
    console.innerHTML = '';
    
    messages.forEach(msg => {
        addConsoleMessage(msg.message, msg.type, msg.timestamp);
    });
}

function clearConsoleDisplay() {
    const console = document.getElementById('consoleOutput');
    console.innerHTML = '';
}

async function clearConsole() {
    try {
        const response = await fetch('/api/console/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            clearConsoleDisplay();
        }
        
    } catch (error) {
        console.error('Error clearing console:', error);
        addConsoleMessage('❌ Failed to clear console', 'error');
    }
}

// UI helper functions
function showModal(icon, title, message) {
    document.getElementById('modalIcon').textContent = icon;
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalMessage').textContent = message;
    document.getElementById('modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}

function showLoading(message) {
    // Simple loading implementation - could be enhanced with a proper loading spinner
    addConsoleMessage(`⏳ ${message}`, 'info');
}

function hideLoading() {
    // Loading is hidden automatically when new messages arrive
} 