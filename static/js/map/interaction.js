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
                throw new Error(result.error);
            }

            showToast('Posicion guardada', 'success');
        } catch (error) {
            console.error('Error saving position:', error);
            showToast('Error guardando posicion', 'error');
        }
    }

    /**
     * Clean up event listeners
     */
    destroy() {
        this.removeDragDrop();
    }
}
