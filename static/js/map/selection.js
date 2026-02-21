/**
 * Map Selection Module
 * Handles furniture selection state and panel updates
 */

/**
 * Selection manager for beach map furniture
 */
export class SelectionManager {
    constructor() {
        this.selectedFurniture = new Set();
        this.readOnly = false;  // Read-only state (controlled by ModalStateManager)
        this.callbacks = {
            onSelect: null,
            onDeselect: null
        };
    }

    /**
     * Set callback functions
     * @param {string} eventName - Event name (onSelect, onDeselect)
     * @param {Function} callback - Callback function
     */
    on(eventName, callback) {
        if (this.callbacks.hasOwnProperty(eventName)) {
            this.callbacks[eventName] = callback;
        }
        return this;
    }

    /**
     * Set read-only state (controlled by ModalStateManager)
     * @param {boolean} readOnly - True to disable selections
     */
    setReadOnly(readOnly) {
        this.readOnly = readOnly;
    }

    /**
     * Check if selections are currently allowed
     * @returns {boolean} True if selections are allowed
     */
    canSelect() {
        return !this.readOnly;
    }

    /**
     * Select or toggle furniture selection
     * @param {number} id - Furniture ID
     * @param {boolean} addToSelection - Whether to add to existing selection
     * @returns {boolean} Whether selection changed
     */
    select(id, addToSelection = false) {
        // Block selections in read-only mode
        if (this.readOnly) {
            return false;
        }

        if (!addToSelection) {
            this.selectedFurniture.clear();
        }

        if (this.selectedFurniture.has(id)) {
            this.selectedFurniture.delete(id);
            if (this.callbacks.onDeselect) {
                this.callbacks.onDeselect(id);
            }
            return true;
        } else {
            this.selectedFurniture.add(id);
            if (this.callbacks.onSelect) {
                this.callbacks.onSelect(id);
            }
            return true;
        }
    }

    /**
     * Deselect a specific furniture item
     * @param {number} id - Furniture ID
     */
    deselect(id) {
        this.selectedFurniture.delete(id);
    }

    /**
     * Clear all selections
     */
    clear() {
        this.selectedFurniture.clear();
    }

    /**
     * Get selected furniture IDs as array
     * @returns {number[]} Array of selected IDs
     */
    getSelected() {
        return Array.from(this.selectedFurniture);
    }

    /**
     * Get the Set of selected furniture
     * @returns {Set} Selected furniture Set
     */
    getSelectedSet() {
        return this.selectedFurniture;
    }

    /**
     * Check if furniture is selected
     * @param {number} id - Furniture ID
     * @returns {boolean}
     */
    isSelected(id) {
        return this.selectedFurniture.has(id);
    }

    /**
     * Get count of selected items
     * @returns {number}
     */
    count() {
        return this.selectedFurniture.size;
    }

    /**
     * Get selected furniture data from map data
     * @param {Object} data - Map data with furniture array
     * @returns {Object[]} Array of selected furniture objects
     */
    getSelectedData(data) {
        if (!data || !data.furniture) return [];
        return data.furniture.filter(f => this.selectedFurniture.has(f.id));
    }

    /**
     * Update the selection panel UI
     * @param {Object} data - Map data with furniture array
     */
    updatePanel(data) {
        const panel = document.getElementById('selection-panel');
        if (!panel) return;

        const selected = this.getSelectedData(data);
        if (selected.length === 0) {
            panel.style.display = 'none';
            return;
        }

        panel.style.display = 'block';
        const countEl = panel.querySelector('.selection-count');
        const listEl = panel.querySelector('.selection-list');
        const capacityEl = panel.querySelector('.selection-capacity');

        if (countEl) countEl.textContent = selected.length;
        if (listEl) listEl.textContent = selected.map(f => f.number).join(', ');
        if (capacityEl) {
            const totalCapacity = selected.reduce((sum, f) => sum + (f.capacity || 2), 0);
            capacityEl.textContent = totalCapacity;
        }
    }
}
