/**
 * Scooper CMS - JavaScript
 * Handles theme toggling and other client-side functionality
 */

// Light themes (use sun icon)
const LIGHT_THEMES = ['light', 'rose-pine-dawn', 'catpuccin-latte'];

// Theme Management
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    // Simple toggle between light and dark for the button
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    // Update data attribute
    document.documentElement.setAttribute('data-theme', newTheme);
    
    // Update theme icon
    updateThemeIcon(newTheme);
    
    // Save preference to localStorage
    localStorage.setItem('scooper-theme', newTheme);
    
    // Also send to server via AJAX
    fetch('/api/toggle-theme', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `theme=${newTheme}`
    }).catch(() => {
        // If AJAX fails, that's okay - the localStorage will persist
        console.log('Theme saved locally');
    });
}

// Update theme icon based on current theme
function updateThemeIcon(theme) {
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        const isLight = LIGHT_THEMES.includes(theme);
        themeIcon.innerHTML = isLight ? '&#127774;' : '&#127771;';
    }
}

// Initialize theme from localStorage or server preference
function initTheme() {
    // Check localStorage first
    const savedTheme = localStorage.getItem('scooper-theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeIcon(savedTheme);
        return;
    }
    
    // If no localStorage preference, use the server's theme setting
    // This is already set in the HTML by the server
    const currentTheme = document.documentElement.getAttribute('data-theme');
    if (currentTheme) {
        updateThemeIcon(currentTheme);
    }
}

// Set theme explicitly (used when selecting from settings)
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('scooper-theme', theme);
    updateThemeIcon(theme);
    
    // Send to server
    fetch('/api/toggle-theme', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `theme=${theme}`
    }).catch(() => {
        console.log('Theme saved locally');
    });
}

// Mark active navigation item
document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    
    // Highlight active nav item in CMS
    const navItems = document.querySelectorAll('.cms-nav .nav-item');
    const currentPath = window.location.pathname;
    
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        // Simple path matching
        if (currentPath === href || currentPath === href + '/') {
            item.classList.add('active');
        }
    });
    
    // Auto-expand textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        // Trigger once to set initial height
        textarea.dispatchEvent(new Event('input'));
    });
    
    // Also highlight active nav item in bottom mobile navigation
    const bottomNavItems = document.querySelectorAll('.cms-bottom-nav .nav-item');
    bottomNavItems.forEach(function(item) {
        const href = item.getAttribute('href');
        // Simple path matching
        if (currentPath === href || currentPath === href + '/') {
            item.classList.add('active');
        }
    });

    // Setup mobile sidebar overlay
    const overlay = document.querySelector('.cms-sidebar-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeMobileSidebar);
    }
    
    // Close sidebar when window is resized to desktop size
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            closeMobileSidebar();
        }
    });
});

// Confirm before leaving unsaved changes
let hasUnsavedChanges = false;

// Track form changes
const forms = document.querySelectorAll('form');
forms.forEach(form => {
    form.addEventListener('input', function() {
        hasUnsavedChanges = true;
    });
    
    form.addEventListener('submit', function() {
        hasUnsavedChanges = false;
    });
});

// Warn before navigating away
window.addEventListener('beforeunload', function(e) {
    if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return e.returnValue;
    }
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Keyboard shortcuts
 document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + S to save form
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        const activeForm = document.querySelector('form');
        if (activeForm) {
            const submitBtn = activeForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.click();
            }
        }
    }
    
    // Escape key to close mobile sidebar
    if (e.key === 'Escape') {
        closeMobileSidebar();
    }
});


// Mobile Sidebar Toggle
function toggleMobileSidebar() {
    const sidebar = document.querySelector('.cms-sidebar');
    const overlay = document.querySelector('.cms-sidebar-overlay');
    if (sidebar && overlay) {
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('active');
    }
}

function closeMobileSidebar() {
    const sidebar = document.querySelector('.cms-sidebar');
    const overlay = document.querySelector('.cms-sidebar-overlay');
    if (sidebar && overlay) {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('active');
    }
}
