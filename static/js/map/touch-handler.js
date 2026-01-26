/**
 * Touch Handler Module
 * Handles touch gestures for the beach map including long-press detection.
 *
 * Events:
 * - longpress: Fired when user long-presses (500ms) on an element
 * - tap: Fired for regular taps (< 300ms, < 10px movement)
 */
class TouchHandler {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            longPressDelay: options.longPressDelay || 500,
            tapMaxDuration: options.tapMaxDuration || 300,
            moveThreshold: options.moveThreshold || 10,
            vibrate: options.vibrate !== false,  // Default true
            ...options
        };

        // State
        this.touchStartTime = 0;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.longPressTimer = null;
        this.currentTarget = null;
        this.isTouchActive = false;

        // Callbacks
        this.callbacks = {
            onLongPress: null,
            onTap: null
        };

        // Bind methods
        this.handleTouchStart = this.handleTouchStart.bind(this);
        this.handleTouchMove = this.handleTouchMove.bind(this);
        this.handleTouchEnd = this.handleTouchEnd.bind(this);
        this.handleTouchCancel = this.handleTouchCancel.bind(this);
        this.handleContextMenu = this.handleContextMenu.bind(this);

        // Attach listeners
        this.attachListeners();
    }

    attachListeners() {
        this.container.addEventListener('touchstart', this.handleTouchStart, { passive: false });
        this.container.addEventListener('touchmove', this.handleTouchMove, { passive: false });
        this.container.addEventListener('touchend', this.handleTouchEnd, { passive: false });
        this.container.addEventListener('touchcancel', this.handleTouchCancel, { passive: false });
        // Prevent native context menu on touch devices during long-press
        this.container.addEventListener('contextmenu', this.handleContextMenu);
    }

    /**
     * Prevent native context menu when touch is active (long-press handling)
     */
    handleContextMenu(event) {
        // If we're in the middle of a touch interaction, prevent native menu
        if (this.isTouchActive || this.longPressTimer) {
            event.preventDefault();
            event.stopPropagation();
        }
    }

    handleTouchStart(event) {
        // Only handle single touch
        if (event.touches.length !== 1) {
            this.cancelLongPress();
            return;
        }

        const touch = event.touches[0];
        this.touchStartTime = Date.now();
        this.touchStartX = touch.clientX;
        this.touchStartY = touch.clientY;
        this.isTouchActive = true;

        // Find the furniture element (traverse up to find data-furniture-id)
        this.currentTarget = this.findFurnitureElement(touch.target);

        if (this.currentTarget) {
            // Start long-press timer
            this.longPressTimer = setTimeout(() => {
                if (this.isTouchActive && this.currentTarget) {
                    this.triggerLongPress(event, this.currentTarget);
                }
            }, this.options.longPressDelay);

            // Visual feedback: scale up slightly
            this.currentTarget.style.transition = 'transform 0.15s ease';
            this.currentTarget.style.transformOrigin = 'center center';
        }
    }

    handleTouchMove(event) {
        if (!this.isTouchActive) return;

        const touch = event.touches[0];
        const deltaX = Math.abs(touch.clientX - this.touchStartX);
        const deltaY = Math.abs(touch.clientY - this.touchStartY);

        // Cancel long-press if moved too much
        if (deltaX > this.options.moveThreshold || deltaY > this.options.moveThreshold) {
            this.cancelLongPress();
        }
    }

    handleTouchEnd(event) {
        if (!this.isTouchActive) return;

        const touchDuration = Date.now() - this.touchStartTime;

        // Cancel long-press timer
        this.cancelLongPress();

        // Check if it was a tap (short touch without much movement)
        if (touchDuration < this.options.tapMaxDuration && this.currentTarget) {
            this.triggerTap(event, this.currentTarget);
        }

        this.resetState();
    }

    handleTouchCancel() {
        this.cancelLongPress();
        this.resetState();
    }

    triggerLongPress(event, target) {
        // Vibration feedback
        if (this.options.vibrate && navigator.vibrate) {
            navigator.vibrate(50);
        }

        // Prevent context menu
        event.preventDefault();

        // Get furniture data
        const furnitureId = parseInt(target.getAttribute('data-furniture-id'));

        if (this.callbacks.onLongPress) {
            this.callbacks.onLongPress({
                furnitureId: furnitureId,
                target: target,
                clientX: this.touchStartX,
                clientY: this.touchStartY,
                originalEvent: event
            });
        }

        // Reset after long-press fires
        this.isTouchActive = false;
    }

    triggerTap(event, target) {
        const furnitureId = parseInt(target.getAttribute('data-furniture-id'));

        if (this.callbacks.onTap) {
            this.callbacks.onTap({
                furnitureId: furnitureId,
                target: target,
                clientX: this.touchStartX,
                clientY: this.touchStartY,
                originalEvent: event
            });
        }
    }

    cancelLongPress() {
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }

        // Remove visual feedback
        if (this.currentTarget) {
            this.currentTarget.style.transition = '';
        }
    }

    resetState() {
        this.isTouchActive = false;
        this.currentTarget = null;
        this.touchStartTime = 0;
        this.touchStartX = 0;
        this.touchStartY = 0;
    }

    findFurnitureElement(element) {
        // Walk up the DOM tree to find furniture group
        let current = element;
        while (current && current !== this.container) {
            if (current.hasAttribute && current.hasAttribute('data-furniture-id')) {
                return current;
            }
            current = current.parentElement;
        }
        return null;
    }

    // Public API
    onLongPress(callback) {
        this.callbacks.onLongPress = callback;
        return this;
    }

    onTap(callback) {
        this.callbacks.onTap = callback;
        return this;
    }

    destroy() {
        this.cancelLongPress();
        this.container.removeEventListener('touchstart', this.handleTouchStart);
        this.container.removeEventListener('touchmove', this.handleTouchMove);
        this.container.removeEventListener('touchend', this.handleTouchEnd);
        this.container.removeEventListener('touchcancel', this.handleTouchCancel);
        this.container.removeEventListener('contextmenu', this.handleContextMenu);
    }
}

// Export for use
window.TouchHandler = TouchHandler;
