/**
 * Map Interaction Module
 * Handles drag-drop functionality and edit mode for furniture positioning
 */

import { getCSRFToken, showToast } from './utils.js';

/**
 * Interaction manager for drag-drop and edit mode
 */
export class InteractionManager {
    constructor(options = {}) {
        this.editMode = false;
        this.readOnly = false;  // Read-only state (controlled by ModalStateManager)
        this.isDragging = false;
        this.dragTarget = null;
        this.dragStart = null;
        this.options = {
            snapToGrid: options.snapToGrid || 10,
            ...options
        };
        this.zoom = 1;
        this.container = null;
        this.furnitureLayer = null;

        // Callback for when position is saved (used to trigger refresh)
        this.onPositionSaved = options.onPositionSaved || null;

        // Callback for updating local data cache after position change
        this.onPositionUpdate = options.onPositionUpdate || null;

        // Temporary furniture drag state (always enabled, no edit mode required)
        this.isDraggingTemp = false;
        this.tempDragTarget = null;
        this.tempDragStartMouse = null;
        this.tempDragStartPos = null;
        this.tempDragThreshold = 5; // pixels before drag activates
        this.tempDragThresholdMet = false;

        // Bind methods
        this.handleDrag = this.handleDrag.bind(this);
        this.handleDragEnd = this.handleDragEnd.bind(this);
    }

    /**
     * Update options (e.g., from server config)
     * @param {Object} newOptions - New option values
     */
    updateOptions(newOptions) {
        Object.assign(this.options, newOptions);
    }

    /**
     * Set current zoom level (needed for drag calculations)
     * @param {number} zoom - Current zoom level
     */
    setZoom(zoom) {
        this.zoom = zoom;
    }

    /**
     * Set read-only state (controlled by ModalStateManager)
     * @param {boolean} readOnly - True to disable interactions
     */
    setReadOnly(readOnly) {
        this.readOnly = readOnly;
        console.log(`[InteractionManager] Read-only mode: ${readOnly}`);

        // If entering read-only, cancel any ongoing drags
        if (readOnly && this.isDragging) {
            this.cancelDrag();
        }
        if (readOnly && this.isDraggingTemp) {
            this.cancelTempDrag();
        }
    }

    /**
     * Check if interactions are currently allowed
     * @returns {boolean} True if interactions are allowed
     */
    canInteract() {
        return !this.readOnly;
    }

    /**
     * Enable edit mode for furniture positioning
     * @param {HTMLElement} container - Map container element
     * @param {SVGGElement} furnitureLayer - Furniture layer element
     */
    enableEditMode(container, furnitureLayer) {
        this.editMode = true;
        this.container = container;
        this.furnitureLayer = furnitureLayer;
        container.classList.add('edit-mode');
        this.setupDragDrop();
    }

    /**
     * Disable edit mode
     */
    disableEditMode() {
        this.editMode = false;
        if (this.container) {
            this.container.classList.remove('edit-mode');
        }
        this.removeDragDrop();
    }

    /**
     * Check if edit mode is enabled
     * @returns {boolean}
     */
    isEditMode() {
        return this.editMode;
    }

    /**
     * Setup drag-drop event listeners
     */
    setupDragDrop() {
        if (!this.editMode || !this.furnitureLayer) return;

        this.furnitureLayer.querySelectorAll('.furniture-item').forEach(group => {
            group.style.cursor = 'move';
            group.addEventListener('mousedown', (e) => this.handleDragStart(e));
        });

        document.addEventListener('mousemove', this.handleDrag);
        document.addEventListener('mouseup', this.handleDragEnd);
    }

    /**
     * Remove drag-drop event listeners
     */
    removeDragDrop() {
        document.removeEventListener('mousemove', this.handleDrag);
        document.removeEventListener('mouseup', this.handleDragEnd);
    }

    /**
     * Handle drag start
     * @param {MouseEvent} event
     */
    handleDragStart(event) {
        if (!this.editMode) return;

        const group = event.target.closest('.furniture-item');
        if (!group) return;

        this.isDragging = true;
        this.dragTarget = group;
        this.dragStart = {
            x: event.clientX,
            y: event.clientY
        };

        // Get current position from transform
        const transform = group.getAttribute('transform');
        const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
        if (match) {
            this.dragStart.itemX = parseFloat(match[1]);
            this.dragStart.itemY = parseFloat(match[2]);
        }

        group.classList.add('dragging');
    }

    /**
     * Handle drag movement
     * @param {MouseEvent} event
     */
    handleDrag(event) {
        if (!this.isDragging || !this.dragTarget) return;

        const dx = (event.clientX - this.dragStart.x) / this.zoom;
        const dy = (event.clientY - this.dragStart.y) / this.zoom;

        let newX = this.dragStart.itemX + dx;
        let newY = this.dragStart.itemY + dy;

        // Snap to grid
        if (this.options.snapToGrid) {
            newX = Math.round(newX / this.options.snapToGrid) * this.options.snapToGrid;
            newY = Math.round(newY / this.options.snapToGrid) * this.options.snapToGrid;
        }

        // Preserve rotation
        const rotation = this.dragTarget.getAttribute('transform').match(/rotate\(([^)]+)\)/);
        const rotationStr = rotation ? ` rotate(${rotation[1]})` : '';

        this.dragTarget.setAttribute('transform', `translate(${newX}, ${newY})${rotationStr}`);
    }

    /**
     * Handle drag end
     * @param {MouseEvent} event
     */
    async handleDragEnd(event) {
        if (!this.isDragging || !this.dragTarget) return;

        const group = this.dragTarget;
        const furnitureId = parseInt(group.dataset.furnitureId);

        // Get final position
        const transform = group.getAttribute('transform');
        const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);

        if (match) {
            const x = parseFloat(match[1]);
            const y = parseFloat(match[2]);

            // Save position to server
            await this.savePosition(furnitureId, x, y);
        }

        group.classList.remove('dragging');
        this.isDragging = false;
        this.dragTarget = null;
    }

    /**
     * Save furniture position to server
     * @param {number} furnitureId - Furniture ID
     * @param {number} x - X position
     * @param {number} y - Y position
     * @param {number|null} rotation - Rotation angle (optional)
     * @returns {Promise<Object>} Result from server
     */
    async savePosition(furnitureId, x, y, rotation = null) {
        try {
            const response = await fetch(`/beach/api/map/furniture/${furnitureId}/position`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ x, y, rotation })
            });

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || 'Error desconocido');
            }

            showToast('Posición actualizada', 'success');
            return result;
        } catch (error) {
            console.error('Error saving position:', error);
            showToast('Error al mover mobiliario', 'error');
            throw error; // Re-throw for caller to handle
        }
    }

    // =========================================================================
    // TEMPORARY FURNITURE DRAG (always enabled, no edit mode required)
    // =========================================================================

    /**
     * Check if an element is draggable temporary furniture
     * @param {Element} element - DOM element to check
     * @returns {Object|null} Furniture data if temp and draggable, null otherwise
     */
    isTemporaryFurniture(element) {
        const furnitureGroup = element.closest('.furniture-item');
        if (!furnitureGroup) return null;

        // Must be temporary and not blocked
        if (!furnitureGroup.classList.contains('temporary')) return null;
        if (furnitureGroup.classList.contains('blocked')) return null;

        return {
            element: furnitureGroup,
            id: parseInt(furnitureGroup.dataset.furnitureId)
        };
    }

    /**
     * Parse position and rotation from SVG transform attribute
     * @param {string} transform - Transform attribute value
     * @returns {Object} {x, y, rotation}
     */
    parseTransform(transform) {
        const translateMatch = transform?.match(/translate\(([^,]+),\s*([^)]+)\)/);
        const rotateMatch = transform?.match(/rotate\(([^)]+)\)/);

        return {
            x: translateMatch ? parseFloat(translateMatch[1]) : 0,
            y: translateMatch ? parseFloat(translateMatch[2]) : 0,
            rotation: rotateMatch ? parseFloat(rotateMatch[1]) : 0
        };
    }

    /**
     * Handle temp furniture drag start
     * @param {MouseEvent} event
     * @param {Object} tempFurniture - {element, id}
     */
    handleTempDragStart(event, tempFurniture) {
        event.preventDefault();

        this.isDraggingTemp = true;
        this.tempDragTarget = tempFurniture.element;
        this.tempDragThresholdMet = false;

        // Store initial mouse position
        this.tempDragStartMouse = {
            x: event.clientX,
            y: event.clientY
        };

        // Store initial element position
        const transform = this.tempDragTarget.getAttribute('transform');
        this.tempDragStartPos = this.parseTransform(transform);
    }

    /**
     * Handle temp furniture drag movement
     * @param {MouseEvent} event
     * @returns {boolean} True if drag is active
     */
    handleTempDrag(event) {
        if (!this.isDraggingTemp || !this.tempDragTarget) return false;

        const deltaX = event.clientX - this.tempDragStartMouse.x;
        const deltaY = event.clientY - this.tempDragStartMouse.y;

        // Check drag threshold
        if (!this.tempDragThresholdMet) {
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            if (distance < this.tempDragThreshold) return false;

            this.tempDragThresholdMet = true;
            this.tempDragTarget.classList.add('dragging');
        }

        // Calculate new position (zoom-aware)
        const newX = this.tempDragStartPos.x + (deltaX / this.zoom);
        const newY = this.tempDragStartPos.y + (deltaY / this.zoom);

        // Apply grid snapping
        const snappedX = this.options.snapToGrid
            ? Math.round(newX / this.options.snapToGrid) * this.options.snapToGrid
            : newX;
        const snappedY = this.options.snapToGrid
            ? Math.round(newY / this.options.snapToGrid) * this.options.snapToGrid
            : newY;

        // Update visual position (preserve rotation)
        const rotation = this.tempDragStartPos.rotation;
        const rotationStr = rotation ? ` rotate(${rotation})` : '';
        this.tempDragTarget.setAttribute(
            'transform',
            `translate(${snappedX}, ${snappedY})${rotationStr}`
        );

        return true;
    }

    /**
     * Handle temp furniture drag end
     * @param {MouseEvent} event
     * @returns {Promise<boolean>} True if a drag occurred (click should be suppressed)
     */
    async handleTempDragEnd(event) {
        if (!this.isDraggingTemp) return false;

        const target = this.tempDragTarget;
        const wasDrag = this.tempDragThresholdMet;
        const startPos = this.tempDragStartPos;

        // Remove visual dragging state
        if (target) {
            target.classList.remove('dragging');
        }

        // Reset threshold flag (but keep isDraggingTemp true until save completes)
        this.tempDragThresholdMet = false;

        if (!wasDrag) {
            // Was a click, not a drag - let click handler process it
            this.isDraggingTemp = false;
            this.tempDragTarget = null;
            this.tempDragStartMouse = null;
            this.tempDragStartPos = null;
            return false;
        }

        // Get final position from transform
        const transform = target.getAttribute('transform');
        const finalPos = this.parseTransform(transform);
        const furnitureId = parseInt(target.dataset.furnitureId);

        // Update local data cache IMMEDIATELY (true optimistic update)
        // This ensures any render during save uses the new position
        if (this.onPositionUpdate) {
            this.onPositionUpdate(furnitureId, finalPos.x, finalPos.y);
        }

        // Save to backend (keep isDraggingTemp true to block auto-refresh)
        try {
            await this.savePosition(furnitureId, finalPos.x, finalPos.y, finalPos.rotation || null);
        } catch (error) {
            // Revert cache and DOM to original position on error
            if (startPos) {
                // Revert cache
                if (this.onPositionUpdate) {
                    this.onPositionUpdate(furnitureId, startPos.x, startPos.y);
                }
                // Revert DOM
                const rotationStr = startPos.rotation ? ` rotate(${startPos.rotation})` : '';
                const revertTransform = `translate(${startPos.x}, ${startPos.y})${rotationStr}`;
                const freshTarget = document.querySelector(`[data-furniture-id="${furnitureId}"]`);
                if (freshTarget) {
                    freshTarget.setAttribute('transform', revertTransform);
                }
            }
        }

        // Clean up drag state after save completes
        this.isDraggingTemp = false;
        this.tempDragTarget = null;
        this.tempDragStartMouse = null;
        this.tempDragStartPos = null;

        return true; // Signal that drag was handled, suppress click
    }

    /**
     * Cancel any in-progress temp drag
     */
    cancelTempDrag() {
        if (!this.isDraggingTemp || !this.tempDragTarget) return;

        // Revert to original position
        if (this.tempDragStartPos) {
            const orig = this.tempDragStartPos;
            const rotationStr = orig.rotation ? ` rotate(${orig.rotation})` : '';
            this.tempDragTarget.setAttribute(
                'transform',
                `translate(${orig.x}, ${orig.y})${rotationStr}`
            );
        }

        this.tempDragTarget.classList.remove('dragging');
        this.isDraggingTemp = false;
        this.tempDragTarget = null;
        this.tempDragStartMouse = null;
        this.tempDragStartPos = null;
        this.tempDragThresholdMet = false;
    }

    /**
     * Clean up event listeners
     */
    destroy() {
        this.removeDragDrop();
        this.cancelTempDrag();
    }
}
