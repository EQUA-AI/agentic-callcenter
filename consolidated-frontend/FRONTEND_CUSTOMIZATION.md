# 🎨 Chainlit Frontend Customization Guide

This guide explains how the Chainlit interface has been customized for the Multi-Service Call Center application.

## 📁 File Structure

```
consolidated-frontend/
├── app.py                    # FastAPI application with voice integration
├── chainlit_app.py          # Enhanced Chainlit chat interface
├── chainlit.md              # Chainlit configuration (TOML format)
├── requirements.txt         # Python dependencies
└── public/                  # Static assets directory
    ├── custom.css          # Main custom styling
    ├── custom.js           # Interactive JavaScript features
    └── animations.css      # Additional animations and effects
```

## 🎨 Customization Features

### 1. **Visual Styling (custom.css)**

#### **Brand Colors & Theming**
- **Primary Color**: `#2563eb` (Professional blue)
- **Service-Specific Colors**:
  - 🕋 Hajj & Umrah: `#16a34a` (Islamic green)
  - 💒 Wedding Planning: `#be185d` (Wedding pink)
  - 🛠️ Technical Support: `#2563eb` (Tech blue)

#### **Message Styling**
- Gradient user message bubbles with rounded corners
- Service-specific color accents for assistant messages
- Smooth animations for message appearance
- Enhanced typography with Inter font family

#### **Chat Profiles**
- Interactive profile cards with hover effects
- Service-specific visual indicators
- Smooth transition animations between profiles
- Color-coded borders and shadows

### 2. **Interactive Features (custom.js)**

#### **Service Switching**
- Automatic service detection based on keywords
- Dynamic interface color updates
- Personalized greeting messages per service
- Profile preview on hover

#### **Enhanced User Experience**
- Loading animations and transitions
- Service status indicators (online/busy/offline)
- Mobile-responsive design
- Real-time theme switching

#### **Smart Suggestions**
- Auto-suggests appropriate service based on message content
- Context-aware service recommendations
- Seamless profile switching workflow

### 3. **Configuration (chainlit.md)**

#### **Chat Profiles Setup**
```toml
[[chatProfiles.chatProfiles]]
name = "Hajj & Umrah Services"
markdown_description = "🕋 Complete guidance for your spiritual journey..."
icon = "🕋"
default = true
```

#### **UI Customization**
- Custom CSS and JavaScript file references
- Font family configuration
- Feature toggles (audio, file upload, LaTeX)
- Enhanced starter message prompts

## 🚀 Getting Started

### Prerequisites
```bash
pip install chainlit>=2.0.1 fastapi aiohttp
```

### Running the Application

#### Option 1: Pure Chainlit Interface
```bash
cd consolidated-frontend
chainlit run chainlit_app.py --host 0.0.0.0 --port 8080
```

#### Option 2: FastAPI + Chainlit Integration
```bash
cd consolidated-frontend
python app.py
```

### Environment Variables
```bash
# Backend API endpoint
BACKEND_URL=http://localhost:8000

# Optional: Custom branding
CHAINLIT_NAME="Your Company Name"
CHAINLIT_DESCRIPTION="Your Custom Description"
```

## 🎨 Customization Options

### 1. **Changing Colors**

Update the CSS variables in `public/custom.css`:
```css
:root {
  --primary-color: #your-brand-color;
  --hajj-color: #your-hajj-color;
  --wedding-color: #your-wedding-color;
  --telco-color: #your-tech-color;
}
```

### 2. **Adding New Services**

1. **Update `chainlit.md`**:
```toml
[[chatProfiles.chatProfiles]]
name = "New Service"
markdown_description = "Description of new service"
icon = "🆕"
```

2. **Update `chainlit_app.py`**:
```python
SERVICE_CONFIG = {
    "new_service": {
        "name": "New Service",
        "agent_type": "new_agent",
        "emoji": "🆕",
        "color": "#color-code",
        "greeting": "Welcome to our new service!",
        "description": "Service description"
    }
}
```

3. **Add CSS styling**:
```css
.profile-new-service {
  border-left: 4px solid #color-code !important;
}
```

### 3. **Customizing Messages**

Update greetings and responses in `chainlit_app.py`:
```python
# Welcome message
welcome_content = """
Your custom welcome message here...
"""

# Service-specific greetings
SERVICE_CONFIG["service"]["greeting"] = "Your custom greeting"
```

### 4. **Adding Animations**

Add new animations in `public/animations.css`:
```css
@keyframes your-animation {
  from { /* start state */ }
  to { /* end state */ }
}

.your-element {
  animation: your-animation 0.3s ease;
}
```

## 📱 Mobile Responsiveness

The interface automatically adapts to mobile devices:
- Responsive chat profiles layout
- Mobile-optimized service indicators
- Touch-friendly interactive elements
- Adjusted spacing and typography

## 🎯 Service Integration

### Backend Integration
The frontend integrates with the backend through:
- HTTP POST to `/chat` endpoint
- Service-specific agent routing
- Phone number session management
- Multi-agent conversation handling

### Message Flow
1. User selects service profile
2. Session updated with agent type
3. Messages sent to backend with service context
4. Responses styled with service branding

## 🔧 Advanced Customization

### Custom JavaScript Functions
```javascript
// Custom service switching
CallCenterInterface.switchProfile('service_key');

// Update service status
CallCenterInterface.updateServiceStatus();

// Show custom greeting
CallCenterInterface.showGreetingMessage(serviceConfig);
```

### CSS Custom Properties
```css
/* Override default values */
document.documentElement.style.setProperty('--property-name', 'value');
```

### Event Listeners
```javascript
// Listen for profile changes
document.addEventListener('profileSwitched', function(event) {
  // Custom logic here
});
```

## 🔍 Troubleshooting

### Common Issues

1. **CSS Not Loading**: Ensure files are in `/public` directory
2. **JavaScript Errors**: Check browser console for script errors  
3. **Profile Not Switching**: Verify service names match exactly
4. **Backend Connection**: Check `BACKEND_URL` environment variable

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Additional Resources

- [Chainlit Documentation](https://docs.chainlit.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [JavaScript Events](https://developer.mozilla.org/en-US/docs/Web/Events)

## 🤝 Contributing

To contribute to the frontend customization:
1. Fork the repository
2. Create a feature branch
3. Test your changes across different browsers
4. Submit a pull request with detailed description

---

*For support or questions about customization, please refer to the project documentation or create an issue in the repository.*
