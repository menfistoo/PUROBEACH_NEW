/**
 * ReservationPanel Utility Functions
 *
 * Standalone utility functions extracted from ReservationPanel for reuse
 * across panel modules and other components.
 */

// =============================================================================
// NAME UTILITIES
// =============================================================================

/**
 * Get initials from first and last name
 * @param {string} firstName - First name
 * @param {string} lastName - Last name
 * @returns {string} Initials (uppercase) or '?' if no name provided
 */
export function getInitials(firstName, lastName) {
    const first = (firstName || '')[0] || '';
    const last = (lastName || '')[0] || '';
    return (first + last).toUpperCase() || '?';
}

// =============================================================================
// DATE FORMATTING
// =============================================================================

/**
 * Format date for display with weekday, day, and month
 * @param {string} dateStr - Date string in any parseable format
 * @returns {string} Formatted date (e.g., "lun., 15 ene.") or original string if parsing fails
 */
export function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        // Handle various date formats
        let date;
        if (dateStr.includes('T')) {
            date = new Date(dateStr);
        } else {
            date = new Date(dateStr + 'T00:00:00');
        }

        if (isNaN(date.getTime())) {
            return dateStr; // Return original if parsing fails
        }

        return date.toLocaleDateString('es-ES', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    } catch (e) {
        return dateStr;
    }
}

/**
 * Format date in short format (DD/MM)
 * @param {string} dateStr - Date string in any parseable format
 * @returns {string} Formatted date (e.g., "15/01") or '-' if no date
 */
export function formatDateShort(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        return `${day}/${month}`;
    } catch (e) {
        return dateStr;
    }
}

/**
 * Parse any date string to YYYY-MM-DD format for comparison
 * @param {string} dateStr - Date string in any format
 * @returns {string} Date in YYYY-MM-DD format or original string if parsing fails
 */
export function parseDateToYMD(dateStr) {
    if (!dateStr) return '';
    try {
        // If already in YYYY-MM-DD format
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            return dateStr;
        }
        // If ISO format (YYYY-MM-DDTHH:MM:SS)
        const isoMatch = dateStr.match(/^(\d{4}-\d{2}-\d{2})T/);
        if (isoMatch) {
            return isoMatch[1];
        }
        // Any other format - parse with Date and extract components
        const date = new Date(dateStr);
        if (!isNaN(date.getTime())) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        return dateStr;
    } catch (e) {
        return dateStr;
    }
}

// =============================================================================
// FURNITURE UTILITIES
// =============================================================================

/**
 * Get emoji icon for furniture type based on name
 * @param {string} typeName - Furniture type name (e.g., "hamaca", "balinesa")
 * @returns {string} Emoji icon for the furniture type
 */
export function getFurnitureIcon(typeName) {
    const icons = {
        'hamaca': '🛏️',
        'balinesa': '🛖',
        'sombrilla': '☂️',
        'mesa': '🪑'
    };
    const lowerType = (typeName || '').toLowerCase();
    for (const [key, icon] of Object.entries(icons)) {
        if (lowerType.includes(key)) return icon;
    }
    return '🪑';
}

// =============================================================================
// NOTIFICATIONS
// =============================================================================

/**
 * Show toast notification using global PuroBeach toast system
 * Falls back to console.log if toast system is not available
 * @param {string} message - Message to display
 * @param {string} type - Toast type: 'info', 'success', 'warning', 'error'
 */
export function showToast(message, type = 'info') {
    if (window.PuroBeach?.showToast) {
        window.PuroBeach.showToast(message, type);
    } else {
        console.log(`[${type}] ${message}`);
    }
}
