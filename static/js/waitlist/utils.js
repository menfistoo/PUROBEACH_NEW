/**
 * Waitlist Utilities Module
 *
 * Pure utility functions for the WaitlistManager.
 * No dependencies on class state - all functions are standalone.
 */

// =============================================================================
// DATE UTILITIES
// =============================================================================

/**
 * Get today's date as YYYY-MM-DD string
 * @returns {string} Today's date in ISO format
 */
export function getTodayDate() {
    const today = new Date();
    return today.toISOString().split('T')[0];
}

/**
 * Format date for display (weekday, day, month in es-ES)
 * @param {string} dateStr - Date string in YYYY-MM-DD format
 * @returns {string} Formatted date (e.g., "lun, 15 ene")
 */
export function formatDateDisplay(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr + 'T12:00:00');
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
 * Format date as DD/MM
 * @param {string} dateStr - Date string in YYYY-MM-DD format
 * @returns {string} Formatted date (e.g., "15/01")
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
 * Format relative time (hace X min, hace Xh, etc.)
 * @param {string} dateStr - ISO date string
 * @returns {string} Relative time in Spanish
 */
export function formatTimeAgo(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Ahora';
        if (diffMins < 60) return `hace ${diffMins} min`;
        if (diffHours < 24) return `hace ${diffHours}h`;
        if (diffDays === 1) return 'Ayer';
        return `hace ${diffDays} dias`;
    } catch (e) {
        return '';
    }
}

// =============================================================================
// LABEL UTILITIES
// =============================================================================

/**
 * Get Spanish label for waitlist status
 * @param {string} status - Status code (waiting, contacted, etc.)
 * @returns {string} Spanish label
 */
export function getStatusLabel(status) {
    const labels = {
        'waiting': 'En espera',
        'contacted': 'Contactado',
        'converted': 'Convertido',
        'declined': 'Rechazado',
        'no_answer': 'Sin respuesta',
        'expired': 'Expirado'
    };
    return labels[status] || status;
}

/**
 * Get Spanish label for time preference
 * @param {string} pref - Time preference code
 * @returns {string} Spanish label
 */
export function getTimePreferenceLabel(pref) {
    const labels = {
        'morning': 'Mañana',
        'manana': 'Mañana',
        'afternoon': 'Tarde',
        'tarde': 'Tarde',
        'mediodia': 'Mediodía',
        'all_day': 'Todo el día',
        'todo_el_dia': 'Todo el día'
    };
    return labels[pref] || pref;
}

// =============================================================================
// SECURITY UTILITIES
// =============================================================================

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} str - String to escape
 * @returns {string} HTML-escaped string
 */
export function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// =============================================================================
// UI UTILITIES
// =============================================================================

/**
 * Show toast notification via PuroBeach global
 * @param {string} message - Message to display
 * @param {string} type - Toast type (success, error, info, warning)
 */
export function showToast(message, type = 'info') {
    if (window.PuroBeach?.showToast) {
        window.PuroBeach.showToast(message, type);
    } else {
        // Toast system not available
    }
}
