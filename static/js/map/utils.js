/**
 * Map Utilities Module
 * Color functions, CSS variable loading, and helper utilities
 */

// =============================================================================
// HTML & SECURITY UTILITIES
// =============================================================================

/**
 * Escape HTML entities to prevent XSS when inserting user data into innerHTML
 * @param {string} str - String to escape
 * @returns {string} Escaped string safe for HTML insertion
 */
export function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Sanitize a CSS color value to prevent injection via style attributes
 * @param {string} color - Color value (hex, rgb, named)
 * @returns {string|null} Sanitized color or null if invalid
 */
export function sanitizeColor(color) {
    if (!color) return null;
    if (/^#[0-9A-Fa-f]{3,8}$/.test(color)) return color;
    if (/^(rgb|hsl)a?\([^)]+\)$/.test(color)) return color;
    if (/^[a-zA-Z]+$/.test(color)) return color;
    return null;
}

// =============================================================================
// CSS & COLOR UTILITIES
// =============================================================================

/**
 * Load CSS variables for map configuration
 * @returns {Object} Configuration object with colors and numeric values
 */
export function loadCSSVariables() {
    const style = getComputedStyle(document.documentElement);
    const getVar = (name, fallback) => {
        const value = style.getPropertyValue(name).trim();
        return value || fallback;
    };
    const getNumVar = (name, fallback) => {
        const value = style.getPropertyValue(name).trim();
        return value ? parseFloat(value) : fallback;
    };

    return {
        autoRefreshMs: getNumVar('--map-auto-refresh-ms', 30000),
        minZoom: getNumVar('--map-min-zoom', 0.1),
        maxZoom: getNumVar('--map-max-zoom', 3),
        snapGrid: getNumVar('--map-snap-grid', 10),
        colors: {
            availableFill: getVar('--map-available-fill', '#F5E6D3'),
            availableStroke: getVar('--map-available-stroke', '#D4AF37'),
            selectedFill: getVar('--map-selected-fill', '#D4AF37'),
            selectedStroke: getVar('--map-selected-stroke', '#8B6914'),
            zoneLabel: getVar('--map-zone-label', '#1A3A5C'),
            tooltipBg: getVar('--map-tooltip-bg', '#1A3A5C'),
            poolPrimary: getVar('--map-pool-primary', '#87CEEB'),
            poolSecondary: getVar('--map-pool-secondary', '#5DADE2'),
            primary: getVar('--color-primary', '#D4AF37'),
            secondary: getVar('--color-secondary', '#1A3A5C')
        }
    };
}

/**
 * Darken a hex color by a percentage
 * @param {string} color - Hex color string
 * @param {number} percent - Percentage to darken (0-100)
 * @returns {string} Darkened hex color
 */
export function darkenColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.max(0, (num >> 16) - amt);
    const G = Math.max(0, ((num >> 8) & 0x00FF) - amt);
    const B = Math.max(0, (num & 0x0000FF) - amt);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}

/**
 * Get contrasting text color (black or white) for a background
 * @param {string} hexcolor - Background hex color
 * @param {Object} colors - Colors object with secondary color
 * @returns {string} Contrasting color for text
 */
export function getContrastColor(hexcolor, colors) {
    const r = parseInt(hexcolor.slice(1, 3), 16);
    const g = parseInt(hexcolor.slice(3, 5), 16);
    const b = parseInt(hexcolor.slice(5, 7), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? colors.secondary : '#FFFFFF';
}

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token or empty string
 */
export function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type (info, success, error, warning)
 */
export function showToast(message, type = 'info') {
    if (window.PuroBeach && window.PuroBeach.showToast) {
        window.PuroBeach.showToast(message, type);
    } else {
    }
}

/**
 * Format a date string for display in Spanish
 * @param {string} dateStr - Date string YYYY-MM-DD
 * @returns {string} Formatted date string
 */
export function formatDateDisplay(dateStr) {
    const date = new Date(dateStr + 'T12:00:00');
    const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
    return date.toLocaleDateString('es-ES', options);
}
