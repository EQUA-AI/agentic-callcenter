// Custom JavaScript for Multi-Agent Call Center Interface

// Global configuration
const CALLCENTER_CONFIG = {
    services: {
        hajj: {
            name: "Hajj & Umrah Services",
            color: "#16a34a",
            emoji: "🕋",
            greeting: "Assalamu Alaikum! How can I help you with your Hajj or Umrah journey?",
            agent_id: "hajj_agent"
        },
        wedding: {
            name: "Wedding Planning",
            color: "#be185d", 
            emoji: "💒",
            greeting: "Congratulations! Let's make your special day perfect. How can I assist you?",
            agent_id: "wedding_agent"
        },
        epcon: {
            name: "EPCON AI",
            color: "#2563eb",
            emoji: "🤖",
            greeting: "Welcome to EPCON AI! How can I help with technical diagnostics or spare parts today?",
            agent_id: "telco_agent"
        }
    },
    animations: {
        messageDelay: 300,
        typingSpeed: 50,
        profileSwitchDuration: 500
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Call Center Interface Initialized');
    initializeInterface();
    setupEventListeners();
    setupProfileSwitching();
    addServiceIndicators();
    setupDynamicHeaderTitle();
    setupDropdownPositioning();
    hideProcessingMessages();
});

// Setup dropdown positioning to prevent overlap
function setupDropdownPositioning() {
    // Observer to watch for dropdown menu creation
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    // Check for dropdown menus
                    const dropdowns = node.querySelectorAll('.MuiPopover-root, .MuiMenu-root');
                    dropdowns.forEach(positionDropdown);
                    
                    // Also check if the node itself is a dropdown
                    if (node.classList.contains('MuiPopover-root') || node.classList.contains('MuiMenu-root')) {
                        positionDropdown(node);
                    }
                }
            });
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Position existing dropdowns
    document.querySelectorAll('.MuiPopover-root, .MuiMenu-root').forEach(positionDropdown);
}

function positionDropdown(dropdown) {
    if (!dropdown) return;
    
    // Add positioning class
    dropdown.classList.add('positioned-dropdown');
    
    // Find the paper element (actual dropdown content)
    const paper = dropdown.querySelector('.MuiPopover-paper, .MuiMenu-paper');
    if (paper) {
        // Ensure proper positioning
        paper.style.marginTop = '8px';
        paper.style.marginLeft = '8px';
        paper.style.transformOrigin = 'top left';
        paper.style.zIndex = '9999';
        paper.style.maxHeight = '300px';
        paper.style.overflowY = 'auto';
        
        // Add click handlers to menu items
        const menuItems = paper.querySelectorAll('.MuiMenuItem-root');
        menuItems.forEach(item => {
            item.style.cursor = 'pointer';
            item.style.userSelect = 'none';
            
            // Ensure click events work properly
            item.addEventListener('click', function(e) {
                e.stopPropagation();
                // Close dropdown after selection
                setTimeout(() => {
                    const backdrop = document.querySelector('.MuiModal-backdrop');
                    if (backdrop) backdrop.click();
                }, 100);
            });
        });
    }
}

// Hide processing/thinking messages
function hideProcessingMessages() {
    const hideMessages = () => {
        // Hide various types of processing messages
        const selectors = [
            '[data-testid="thinking-message"]',
            '.thinking-message',
            '.processing-message',
            '[class*="thinking"]',
            '[class*="processing"]',
            '.cot-container',
            '.chain-of-thought',
            '[data-testid="cot"]',
            '[class*="cot"]'
        ];
        
        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                el.style.display = 'none';
            });
        });
        
        // Also hide text content that matches processing patterns
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            if (el.textContent && el.textContent.includes('is processing your request')) {
                const parent = el.closest('.message, .chat-message, [class*="message"]');
                if (parent) {
                    parent.style.display = 'none';
                }
            }
        });
    };
    
    // Run immediately and set up observer
    hideMessages();
    
    const observer = new MutationObserver(hideMessages);
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true
    });
}

// Setup dynamic header title functionality
function setupDynamicHeaderTitle() {
    // Function to update header title based on current service
    function updateHeaderTitle(serviceName) {
        // More comprehensive selector for header title
        const headerSelectors = [
            '.MuiToolbar-root h6',
            '.MuiToolbar-root .MuiTypography-h6', 
            '.MuiToolbar-root .MuiTypography-root',
            'header h1',
            'header .title',
            '.MuiAppBar-root h6',
            '.MuiAppBar-root .MuiTypography-h6',
            '.MuiAppBar-root .MuiTypography-root'
        ];
        
        let headerTitle = null;
        for (const selector of headerSelectors) {
            headerTitle = document.querySelector(selector);
            if (headerTitle) break;
        }
        
        if (headerTitle) {
            if (serviceName === 'EPCON AI') {
                headerTitle.textContent = 'Epcon AI & Spare Parts';
                console.log('🎯 Header updated to: Epcon AI & Spare Parts');
            } else if (serviceName === 'Hajj & Umrah Services') {
                headerTitle.textContent = 'Hajj & Umrah Services';
                console.log('🎯 Header updated to: Hajj & Umrah Services');
            } else if (serviceName === 'Wedding Planning') {
                headerTitle.textContent = 'Wedding Planning Services';
                console.log('🎯 Header updated to: Wedding Planning Services');
            } else if (serviceName) {
                headerTitle.textContent = serviceName;
                console.log('🎯 Header updated to:', serviceName);
            } else {
                headerTitle.textContent = 'Multi-Agent Call Center';
                console.log('🎯 Header updated to default: Multi-Agent Call Center');
            }
        } else {
            console.log('⚠️ Header title element not found');
        }
    }

    // Monitor for profile changes with enhanced detection
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                // Check if dropdown value changed
                const dropdown = document.querySelector('.MuiSelect-select, [role="button"][aria-haspopup="listbox"]');
                if (dropdown) {
                    const selectedText = dropdown.textContent.trim();
                    if (selectedText && selectedText !== 'Multi-Agent Call Center') {
                        updateHeaderTitle(selectedText);
                    }
                }
                
                // Also check for profile selection changes in the chat interface
                const profileCards = document.querySelectorAll('[class*="profile"], .chat-profile, .MuiCard-root');
                profileCards.forEach(card => {
                    if (card.classList.contains('selected') || card.classList.contains('active')) {
                        const profileText = card.textContent;
                        if (profileText.includes('EPCON AI')) {
                            updateHeaderTitle('EPCON AI');
                        } else if (profileText.includes('Hajj')) {
                            updateHeaderTitle('Hajj & Umrah Services');
                        } else if (profileText.includes('Wedding')) {
                            updateHeaderTitle('Wedding Planning');
                        }
                    }
                });
            }
        });
    });

    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class', 'aria-selected']
    });

    // Also listen for click events on dropdown items
    document.addEventListener('click', function(event) {
        const menuItem = event.target.closest('.MuiMenuItem-root');
        if (menuItem) {
            const serviceText = menuItem.textContent.trim();
            setTimeout(() => updateHeaderTitle(serviceText), 100);
        }
        
        // Listen for profile card clicks
        const profileCard = event.target.closest('[class*="profile"], .chat-profile');
        if (profileCard) {
            const profileText = profileCard.textContent;
            setTimeout(() => {
                if (profileText.includes('EPCON AI')) {
                    updateHeaderTitle('EPCON AI');
                } else if (profileText.includes('Hajj')) {
                    updateHeaderTitle('Hajj & Umrah Services');
                } else if (profileText.includes('Wedding')) {
                    updateHeaderTitle('Wedding Planning');
                }
            }, 100);
        }
    });
    
    // Initial header update on page load
    setTimeout(() => {
        const dropdown = document.querySelector('.MuiSelect-select, [role="button"][aria-haspopup="listbox"]');
        if (dropdown) {
            const selectedText = dropdown.textContent.trim();
            if (selectedText && selectedText !== 'Multi-Agent Call Center') {
                updateHeaderTitle(selectedText);
            }
        } else {
            // If no dropdown found, set default
            updateHeaderTitle('');
        }
    }, 1000);
}

// Initialize the interface
function initializeInterface() {
    // Add custom classes to body for styling
    document.body.classList.add('callcenter-interface');
    
    // Set initial theme
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) {
        document.body.classList.add('dark-mode');
    }
    
    // Initialize service status
    updateServiceStatus();
    
    // Add loading animations
    addLoadingAnimations();
}

// Setup event listeners
function setupEventListeners() {
    // Listen for chat profile changes
    document.addEventListener('profileChanged', function(event) {
        const profileType = event.detail.profile;
        handleProfileSwitch(profileType);
    });
    
    // Listen for new messages
    document.addEventListener('messageAdded', function(event) {
        const message = event.detail;
        animateNewMessage(message);
    });
    
    // Theme change listener
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        document.body.classList.toggle('dark-mode', e.matches);
    });
    
    // Window resize handler
    window.addEventListener('resize', debounce(handleResize, 250));
}

// Setup profile switching functionality
function setupProfileSwitching() {
    // Find and enhance profile buttons
    const profileButtons = document.querySelectorAll('[data-profile]');
    
    profileButtons.forEach(button => {
        const profileType = button.getAttribute('data-profile');
        const service = CALLCENTER_CONFIG.services[profileType];
        
        if (service) {
            // Add service emoji and styling
            const emoji = document.createElement('span');
            emoji.className = 'service-emoji';
            emoji.textContent = service.emoji;
            button.prepend(emoji);
            
            // Add click handler
            button.addEventListener('click', () => switchProfile(profileType));
            
            // Add hover effects
            button.addEventListener('mouseenter', () => showProfilePreview(profileType));
            button.addEventListener('mouseleave', hideProfilePreview);
        }
    });
}

// Handle profile switching
function switchProfile(profileType) {
    const service = CALLCENTER_CONFIG.services[profileType];
    if (!service) return;
    
    console.log(`🔄 Switching to ${service.name} profile`);
    
    // Update active profile
    updateActiveProfile(profileType);
    
    // Change interface colors
    updateInterfaceColors(service.color);
    
    // Show greeting message
    showGreetingMessage(service);
    
    // Update page title
    document.title = `${service.name} - Call Center`;
    
    // Trigger custom event
    const event = new CustomEvent('profileSwitched', {
        detail: { profileType, service }
    });
    document.dispatchEvent(event);
}

// Update active profile UI
function updateActiveProfile(profileType) {
    // Remove active class from all profiles
    document.querySelectorAll('.chat-profile').forEach(profile => {
        profile.classList.remove('active');
    });
    
    // Add active class to selected profile
    const activeProfile = document.querySelector(`[data-profile="${profileType}"]`);
    if (activeProfile) {
        activeProfile.classList.add('active');
        
        // Add service-specific class
        activeProfile.classList.add(`profile-${profileType}`);
    }
}

// Update interface colors based on service
function updateInterfaceColors(color) {
    document.documentElement.style.setProperty('--active-service-color', color);
    
    // Update CSS custom properties
    const colorVariations = generateColorVariations(color);
    Object.entries(colorVariations).forEach(([property, value]) => {
        document.documentElement.style.setProperty(property, value);
    });
}

// Generate color variations for theming
function generateColorVariations(baseColor) {
    // Convert hex to RGB
    const rgb = hexToRgb(baseColor);
    if (!rgb) return {};
    
    return {
        '--service-color-light': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`,
        '--service-color-medium': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.2)`,
        '--service-color-strong': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.8)`,
        '--service-shadow': `0 4px 20px rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.2)`
    };
}

// Show greeting message for service
function showGreetingMessage(service) {
    const chatContainer = document.querySelector('.chat-messages') || document.querySelector('#chat-container');
    if (!chatContainer) return;
    
    // Create greeting message element
    const greetingElement = document.createElement('div');
    greetingElement.className = 'message message-system greeting-message';
    greetingElement.innerHTML = `
        <div class="message-content">
            <span class="service-emoji">${service.emoji}</span>
            <span class="greeting-text">${service.greeting}</span>
        </div>
    `;
    
    // Add to chat with animation
    greetingElement.style.opacity = '0';
    greetingElement.style.transform = 'translateY(20px)';
    chatContainer.appendChild(greetingElement);
    
    // Animate in
    requestAnimationFrame(() => {
        greetingElement.style.transition = 'all 0.3s ease';
        greetingElement.style.opacity = '1';
        greetingElement.style.transform = 'translateY(0)';
    });
    
    // Remove after delay
    setTimeout(() => {
        greetingElement.style.opacity = '0';
        setTimeout(() => greetingElement.remove(), 300);
    }, 5000);
}

// Add service indicators
function addServiceIndicators() {
    const indicators = document.createElement('div');
    indicators.className = 'service-indicators';
    indicators.innerHTML = `
        <div class="indicator hajj" title="Hajj & Umrah Services">
            <span class="indicator-dot"></span>
            <span class="indicator-label">🕋</span>
        </div>
        <div class="indicator wedding" title="Wedding Planning">
            <span class="indicator-dot"></span>
            <span class="indicator-label">💒</span>
        </div>
        <div class="indicator telco" title="Technical Support">
            <span class="indicator-dot"></span>
            <span class="indicator-label">🛠️</span>
        </div>
    `;
    
    // Add to header or appropriate location
    const header = document.querySelector('.MuiAppBar-root') || document.querySelector('header');
    if (header) {
        header.appendChild(indicators);
    }
}

// Update service status
function updateServiceStatus() {
    // Mock service status - in real implementation, this would call API
    const statuses = {
        hajj: 'online',
        wedding: 'online', 
        telco: 'busy'
    };
    
    Object.entries(statuses).forEach(([service, status]) => {
        const indicator = document.querySelector(`.indicator.${service} .indicator-dot`);
        if (indicator) {
            indicator.className = `indicator-dot status-${status}`;
        }
    });
}

// Animate new messages
function animateNewMessage(message) {
    const messageElement = message.element || message;
    if (!messageElement) return;
    
    // Add animation class
    messageElement.classList.add('message-entering');
    
    // Determine message type for styling
    const isUser = messageElement.classList.contains('message-user');
    const isSystem = messageElement.classList.contains('message-system');
    
    if (isUser) {
        messageElement.style.transform = 'translateX(100%)';
    } else {
        messageElement.style.transform = 'translateX(-100%)';
    }
    
    messageElement.style.opacity = '0';
    
    // Animate in
    requestAnimationFrame(() => {
        messageElement.style.transition = 'all 0.3s ease';
        messageElement.style.transform = 'translateX(0)';
        messageElement.style.opacity = '1';
    });
    
    // Remove animation class after completion
    setTimeout(() => {
        messageElement.classList.remove('message-entering');
        messageElement.style.transform = '';
        messageElement.style.opacity = '';
        messageElement.style.transition = '';
    }, 300);
}

// Add loading animations
function addLoadingAnimations() {
    // Create loading overlay
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.innerHTML = `
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <div class="loading-text">Initializing Call Center...</div>
        </div>
    `;
    
    document.body.appendChild(loadingOverlay);
    
    // Remove loading overlay after initialization
    setTimeout(() => {
        loadingOverlay.style.opacity = '0';
        setTimeout(() => loadingOverlay.remove(), 500);
    }, 1500);
}

// Show profile preview on hover
function showProfilePreview(profileType) {
    const service = CALLCENTER_CONFIG.services[profileType];
    if (!service) return;
    
    const preview = document.createElement('div');
    preview.className = 'profile-preview';
    preview.innerHTML = `
        <div class="preview-header">
            <span class="preview-emoji">${service.emoji}</span>
            <span class="preview-name">${service.name}</span>
        </div>
        <div class="preview-greeting">${service.greeting}</div>
    `;
    
    document.body.appendChild(preview);
    
    // Position preview
    const button = document.querySelector(`[data-profile="${profileType}"]`);
    if (button) {
        const rect = button.getBoundingClientRect();
        preview.style.left = `${rect.right + 10}px`;
        preview.style.top = `${rect.top}px`;
    }
    
    // Show with animation
    requestAnimationFrame(() => {
        preview.classList.add('show');
    });
}

// Hide profile preview
function hideProfilePreview() {
    const preview = document.querySelector('.profile-preview');
    if (preview) {
        preview.classList.remove('show');
        setTimeout(() => preview.remove(), 200);
    }
}

// Handle window resize
function handleResize() {
    // Adjust layout for mobile
    const isMobile = window.innerWidth < 768;
    document.body.classList.toggle('mobile-layout', isMobile);
    
    // Adjust service indicators
    const indicators = document.querySelector('.service-indicators');
    if (indicators) {
        indicators.classList.toggle('mobile', isMobile);
    }
}

// Utility functions
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export for use in other scripts
window.CallCenterInterface = {
    config: CALLCENTER_CONFIG,
    switchProfile,
    updateServiceStatus,
    showGreetingMessage
};

console.log('✅ Call Center Interface JavaScript loaded successfully');
