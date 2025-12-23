/**
 * Map Navigation Module
 * Handles date navigation, zoom/pan, and keyboard shortcuts
 */

/**
 * Navigation manager for beach map
 */
export class NavigationManager {
    constructor(options = {}) {
        this.zoom = 1;
        this.pan = { x: 0, y: 0 };
        this.options = {
            minZoom: options.minZoom || 0.1,
            maxZoom: options.maxZoom || 3,
            ...options
        };
        this.callbacks = {
            onDateChange: null,
            onZoomChange: null
        };
        this.keydownHandler = null;
    }

    /**
     * Set callback functions
     * @param {string} eventName - Event name
     * @param {Function} callback - Callback function
     */
    on(eventName, callback) {
        if (this.callbacks.hasOwnProperty(eventName)) {
            this.callbacks[eventName] = callback;
        }
        return this;
    }

    /**
     * Update options (e.g., from server config)
     * @param {Object} newOptions - New option values
     */
    updateOptions(newOptions) {
        Object.assign(this.options, newOptions);
    }

    // =========================================================================
    // DATE NAVIGATION
    // =========================================================================

    /**
     * Navigate to a specific date
     * @param {string} dateStr - Date string YYYY-MM-DD
     * @param {Function} loadDataFn - Async function to reload data
     */
    async goToDate(dateStr, loadDataFn) {
        if (this.callbacks.onDateChange) {
            this.callbacks.onDateChange(dateStr);
        }
        if (loadDataFn) {
            await loadDataFn();
        }
    }

    /**
     * Navigate to previous day
     * @param {string} currentDate - Current date string
     * @param {Function} loadDataFn - Async function to reload data
     * @returns {string} New date string
     */
    async goToPreviousDay(currentDate, loadDataFn) {
        const date = new Date(currentDate);
        date.setDate(date.getDate() - 1);
        const newDate = date.toISOString().split('T')[0];
        await this.goToDate(newDate, loadDataFn);
        return newDate;
    }

    /**
     * Navigate to next day
     * @param {string} currentDate - Current date string
     * @param {Function} loadDataFn - Async function to reload data
     * @returns {string} New date string
     */
    async goToNextDay(currentDate, loadDataFn) {
        const date = new Date(currentDate);
        date.setDate(date.getDate() + 1);
        const newDate = date.toISOString().split('T')[0];
        await this.goToDate(newDate, loadDataFn);
        return newDate;
    }

    // =========================================================================
    // ZOOM & PAN
    // =========================================================================

    /**
     * Zoom in by a factor
     * @param {number} factor - Zoom increment
     */
    zoomIn(factor = 0.25) {
        this.setZoom(this.zoom + factor);
    }

    /**
     * Zoom out by a factor
     * @param {number} factor - Zoom decrement
     */
    zoomOut(factor = 0.25) {
        this.setZoom(this.zoom - factor);
    }

    /**
     * Reset zoom to 100%
     */
    zoomReset() {
        this.setZoom(1);
        this.pan = { x: 0, y: 0 };
    }

    /**
     * Set zoom level with bounds checking
     * @param {number} level - New zoom level
     */
    setZoom(level) {
        this.zoom = Math.max(this.options.minZoom, Math.min(this.options.maxZoom, level));
        if (this.callbacks.onZoomChange) {
            this.callbacks.onZoomChange(this.zoom);
        }
    }

    /**
     * Get current zoom level
     * @returns {number}
     */
    getZoom() {
        return this.zoom;
    }

    /**
     * Apply zoom to SVG element
     * @param {SVGSVGElement} svg - SVG element
     * @param {Object} data - Map data with dimensions
     */
    applyZoom(svg, data) {
        if (!svg || !data) return;

        const viewBox = svg.getAttribute('viewBox');
        if (!viewBox) return;

        const [, , width, height] = viewBox.split(' ').map(Number);

        svg.style.width = `${width * this.zoom}px`;
        svg.style.height = `${height * this.zoom}px`;
    }

    // =========================================================================
    // KEYBOARD NAVIGATION
    // =========================================================================

    /**
     * Setup keyboard event listener
     * @param {Object} handlers - Object with handler functions
     */
    setupKeyboard(handlers) {
        this.keydownHandler = (event) => {
            // Escape to clear selection
            if (event.key === 'Escape') {
                if (handlers.onEscape) handlers.onEscape();
                return;
            }

            // Arrow keys for date navigation
            if (event.key === 'ArrowLeft' && event.altKey) {
                event.preventDefault();
                if (handlers.onPrevDay) handlers.onPrevDay();
            } else if (event.key === 'ArrowRight' && event.altKey) {
                event.preventDefault();
                if (handlers.onNextDay) handlers.onNextDay();
            }

            // Zoom with + and -
            if (event.key === '+' || event.key === '=') {
                this.zoomIn();
                if (handlers.onZoom) handlers.onZoom();
            } else if (event.key === '-') {
                this.zoomOut();
                if (handlers.onZoom) handlers.onZoom();
            }
        };

        document.addEventListener('keydown', this.keydownHandler);
    }

    /**
     * Remove keyboard event listener
     */
    removeKeyboard() {
        if (this.keydownHandler) {
            document.removeEventListener('keydown', this.keydownHandler);
            this.keydownHandler = null;
        }
    }
}
