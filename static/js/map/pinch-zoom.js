/**
 * Pinch Zoom Handler
 * Handles 2-finger pinch gestures for zoom on mobile devices.
 *
 * This handler works alongside TouchHandler (which handles single-touch)
 * and uses the existing zoom API to avoid conflicts.
 */
export class PinchZoomHandler {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            minZoom: options.minZoom || 0.1,
            maxZoom: options.maxZoom || 3,
            ...options
        };

        // Callbacks for zoom integration
        this.getZoom = options.getZoom || (() => 1);
        this.setZoom = options.setZoom || (() => {});
        this.getMapWrapper = options.getMapWrapper || (() => null);
        this.getSvg = options.getSvg || (() => null);

        // Pinch state
        this.isPinching = false;
        this.pinchStartDistance = 0;
        this.pinchStartZoom = 1;
        this.pinchCenter = { x: 0, y: 0 };

        // Bind methods
        this.handleTouchStart = this.handleTouchStart.bind(this);
        this.handleTouchMove = this.handleTouchMove.bind(this);
        this.handleTouchEnd = this.handleTouchEnd.bind(this);

        this.bindEvents();
    }

    bindEvents() {
        this.container.addEventListener('touchstart', this.handleTouchStart, { passive: false });
        this.container.addEventListener('touchmove', this.handleTouchMove, { passive: false });
        this.container.addEventListener('touchend', this.handleTouchEnd, { passive: false });
        this.container.addEventListener('touchcancel', this.handleTouchEnd, { passive: false });
    }

    /**
     * Calculate distance between two touch points
     */
    getDistance(touch1, touch2) {
        const dx = touch2.clientX - touch1.clientX;
        const dy = touch2.clientY - touch1.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    /**
     * Calculate midpoint between two touch points
     */
    getMidpoint(touch1, touch2) {
        return {
            x: (touch1.clientX + touch2.clientX) / 2,
            y: (touch1.clientY + touch2.clientY) / 2
        };
    }

    handleTouchStart(e) {
        if (e.touches.length === 2) {
            // Prevent native gestures when pinching
            e.preventDefault();

            this.isPinching = true;
            this.pinchStartDistance = this.getDistance(e.touches[0], e.touches[1]);
            this.pinchStartZoom = this.getZoom();
            this.pinchCenter = this.getMidpoint(e.touches[0], e.touches[1]);
        }
    }

    handleTouchMove(e) {
        if (!this.isPinching || e.touches.length !== 2) return;

        e.preventDefault();

        const currentDistance = this.getDistance(e.touches[0], e.touches[1]);
        const currentCenter = this.getMidpoint(e.touches[0], e.touches[1]);

        // Calculate new zoom based on distance ratio
        const zoomRatio = currentDistance / this.pinchStartDistance;
        let newZoom = this.pinchStartZoom * zoomRatio;

        // Clamp to limits
        newZoom = Math.max(this.options.minZoom, Math.min(this.options.maxZoom, newZoom));

        // Apply zoom and adjust scroll to keep pinch center stable
        this.applyZoomToPoint(newZoom, currentCenter);
    }

    handleTouchEnd(e) {
        if (e.touches.length < 2) {
            this.isPinching = false;
        }
    }

    /**
     * Apply zoom centered on a specific point (keeps point under fingers)
     * Adapted from the wheel zoom logic in map.html
     */
    applyZoomToPoint(newZoom, point) {
        const svg = this.getSvg();
        const wrapper = this.getMapWrapper();
        if (!svg || !wrapper) return;

        const currentZoom = this.getZoom();
        if (Math.abs(newZoom - currentZoom) < 0.001) return;

        const svgRect = svg.getBoundingClientRect();
        const wrapperRect = wrapper.getBoundingClientRect();

        // Point position in wrapper viewport
        const pointXInWrapper = point.x - wrapperRect.left;
        const pointYInWrapper = point.y - wrapperRect.top;

        // Convert to canvas coordinates (before zoom change)
        const canvasX = Math.max(0, (point.x - svgRect.left)) / currentZoom;
        const canvasY = Math.max(0, (point.y - svgRect.top)) / currentZoom;

        // Apply zoom through the standard API
        this.setZoom(newZoom);

        // Adjust scroll to keep point under fingers
        requestAnimationFrame(() => {
            const newSvgRect = svg.getBoundingClientRect();
            const padding = 10;

            // Calculate centering offset (for when SVG is smaller than viewport)
            const availableWidth = wrapper.clientWidth - padding * 2;
            const availableHeight = wrapper.clientHeight - padding * 2;
            const newCenterOffsetX = Math.max(0, (availableWidth - newSvgRect.width) / 2);
            const newCenterOffsetY = Math.max(0, (availableHeight - newSvgRect.height) / 2);

            // New point position in zoomed SVG
            const newPointXInSvg = canvasX * newZoom;
            const newPointYInSvg = canvasY * newZoom;

            // Target scroll position
            const targetScrollX = padding + newCenterOffsetX + newPointXInSvg - pointXInWrapper;
            const targetScrollY = padding + newCenterOffsetY + newPointYInSvg - pointYInWrapper;

            wrapper.scrollLeft = Math.max(0, targetScrollX);
            wrapper.scrollTop = Math.max(0, targetScrollY);
        });
    }

    destroy() {
        this.container.removeEventListener('touchstart', this.handleTouchStart);
        this.container.removeEventListener('touchmove', this.handleTouchMove);
        this.container.removeEventListener('touchend', this.handleTouchEnd);
        this.container.removeEventListener('touchcancel', this.handleTouchEnd);
    }
}

// Export for non-module usage
window.PinchZoomHandler = PinchZoomHandler;
