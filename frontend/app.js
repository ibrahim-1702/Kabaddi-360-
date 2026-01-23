// ===========================================================================
// Kabaddi Ghost Trainer - Main JavaScript
// ===========================================================================

// Utility Functions
// ===========================================================================

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// API Helper Functions
// ===========================================================================

async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, options);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Loading/Error State Management
// ===========================================================================

function showLoading(message = 'Loading...') {
    const overlay = document.querySelector('.loading-overlay');
    if (!overlay) {
        const div = document.createElement('div');
        div.className = 'loading-overlay';
        div.innerHTML = `
            <div class="spinner"></div>
            <p style="color: var(--text-secondary); margin-top: 1rem;">${message}</p>
        `;
        document.body.appendChild(div);
    }
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

function showError(message) {
    alert('Error: ' + message);
}

// Session Storage Helpers
// ===========================================================================

function saveToSession(key, value) {
    sessionStorage.setItem(key, JSON.stringify(value));
}

function getFromSession(key) {
    const item = sessionStorage.getItem(key);
    return item ? JSON.parse(item) : null;
}

// Page-specific Initialization
// ===========================================================================

// Detect current page and initialize
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    
    // Add active class to current nav link
    updateActiveNav(path);
    
    // Initialize animations
    initAnimations();
});

function updateActiveNav(currentPath) {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (currentPath.includes(href) || (currentPath.endsWith('/') && href === 'index.html')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

function initAnimations() {
    // Intersection Observer for fade-in animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.card, .grid > div').forEach(el => {
        observer.observe(el);
    });
}

// Video Player Enhancements
// ===========================================================================

function initVideoPlayers() {
    const videos = document.querySelectorAll('.video-player');
    
    videos.forEach(video => {
        // Prevent videos from playing automatically
        video.setAttribute('playsinline', '');
        video.setAttribute('preload', 'metadata');
        
        // Add loading indicator
        video.addEventListener('loadstart', function() {
            this.parentElement.classList.add('loading');
        });
        
        video.addEventListener('loadeddata', function() {
            this.parentElement.classList.remove('loading');
        });
    });
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatFileSize,
        formatDuration,
        apiRequest,
        showLoading,
        hideLoading,
        showError,
        saveToSession,
        getFromSession
    };
}
