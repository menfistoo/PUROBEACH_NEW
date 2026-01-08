/**
 * Map Editor - Selection Module
 * Handles single and multi-selection of furniture items
 */

/**
 * Mixin that adds selection management to MapEditor
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with selection methods
 */
export const SelectionMixin = (Base) => class extends Base {

    /**
     * Select a single item (clears previous selection unless addToSelection is true)
     * @param {Object} item - Furniture item to select
     * @param {boolean} addToSelection - If true, add to existing selection
     */
    selectItem(item, addToSelection = false) {
        if (!addToSelection) {
            this.deselectAll();
        }

        // Attach type info for external access
        item.typeInfo = this.furnitureTypes[item.furniture_type] || {};

        this.selectedItems.add(item.id);
        const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
        if (group) group.classList.add('selected');

        this.updateSelectionUI();
        this.emit('selectionChanged', item);
        this.emit('multiSelectionChanged', this.getSelectedItems());
    }

    /**
     * Toggle selection of an item (for Ctrl+click)
     * @param {Object} item - Furniture item to toggle
     */
    toggleItemSelection(item) {
        if (this.selectedItems.has(item.id)) {
            this.deselectItem(item.id);
        } else {
            this.selectItem(item, true);
        }
    }

    /**
     * Deselect a single item
     * @param {number} itemId - ID of item to deselect
     */
    deselectItem(itemId) {
        this.selectedItems.delete(itemId);
        const group = this.furnitureLayer.querySelector(`[data-id="${itemId}"]`);
        if (group) group.classList.remove('selected');

        this.updateSelectionUI();
        this.emit('multiSelectionChanged', this.getSelectedItems());
    }

    /**
     * Clear all selections
     */
    deselectAll() {
        this.selectedItems.clear();
        this.furnitureLayer?.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
        this.updateSelectionUI();
        this.emit('selectionChanged', null);
        this.emit('multiSelectionChanged', []);
    }

    /**
     * Select multiple items by IDs
     * @param {Array} itemIds - Array of item IDs to select
     * @param {boolean} addToSelection - If true, add to existing selection
     */
    selectMultiple(itemIds, addToSelection = false) {
        if (!addToSelection) {
            this.deselectAll();
        }

        itemIds.forEach(id => {
            this.selectedItems.add(id);
            const group = this.furnitureLayer.querySelector(`[data-id="${id}"]`);
            if (group) group.classList.add('selected');
        });

        this.updateSelectionUI();
        this.emit('multiSelectionChanged', this.getSelectedItems());
    }

    /**
     * Select all items in canvas
     */
    selectAll() {
        this.furniture.forEach(item => {
            this.selectedItems.add(item.id);
            const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
            if (group) group.classList.add('selected');
        });

        this.updateSelectionUI();
        this.emit('multiSelectionChanged', this.getSelectedItems());
    }

    /**
     * Get array of selected item objects
     * @returns {Array} Array of selected furniture items
     */
    getSelectedItems() {
        return this.furniture.filter(item => this.selectedItems.has(item.id));
    }

    /**
     * Get count of selected items
     * @returns {number} Number of selected items
     */
    getSelectionCount() {
        return this.selectedItems.size;
    }

    /**
     * Check if item is selected
     * @param {number} itemId - Item ID to check
     * @returns {boolean} True if selected
     */
    isSelected(itemId) {
        return this.selectedItems.has(itemId);
    }

    /**
     * Update UI based on selection state
     */
    updateSelectionUI() {
        const count = this.selectedItems.size;
        const multiSelectToolbar = document.getElementById('multi-select-toolbar');
        const singlePropsPanel = this.propertiesPanel;

        if (count === 0) {
            // No selection
            if (singlePropsPanel) singlePropsPanel.classList.remove('active');
            if (multiSelectToolbar) multiSelectToolbar.classList.add('d-none');
        } else if (count === 1) {
            // Single selection - show properties panel
            const item = this.getSelectedItems()[0];
            this.showProperties(item);
            if (multiSelectToolbar) multiSelectToolbar.classList.add('d-none');
        } else {
            // Multiple selection - show multi-select toolbar
            if (singlePropsPanel) singlePropsPanel.classList.remove('active');
            if (multiSelectToolbar) {
                multiSelectToolbar.classList.remove('d-none');
                const countEl = multiSelectToolbar.querySelector('.selection-count');
                if (countEl) countEl.textContent = count;
            }
        }
    }

    /**
     * Show properties panel for a single item
     * @param {Object} item - Furniture item
     */
    showProperties(item) {
        if (!this.propertiesPanel) return;

        const type = this.furnitureTypes[item.furniture_type] || {};

        document.getElementById('prop-number').value = item.number || '';
        document.getElementById('prop-x').value = Math.round(item.position_x);
        document.getElementById('prop-y').value = Math.round(item.position_y);
        document.getElementById('prop-rotation').value = item.rotation || 0;
        document.getElementById('prop-capacity').value = item.capacity || 0;

        // Size properties (for decorative items)
        const widthInput = document.getElementById('prop-width');
        const heightInput = document.getElementById('prop-height');
        if (widthInput) widthInput.value = item.width || 60;
        if (heightInput) heightInput.value = item.height || 40;

        // Color property
        const fillColorInput = document.getElementById('prop-fill-color');
        const fillColorText = document.getElementById('prop-fill-color-text');
        if (fillColorInput) {
            const color = item.fill_color || type.fill_color || '#A0522D';
            fillColorInput.value = color;
            if (fillColorText) fillColorText.value = color;
        }

        const capacityGroup = document.getElementById('prop-capacity-group');
        if (capacityGroup) {
            capacityGroup.style.display = type.is_decorative ? 'none' : 'block';
        }

        this.propertiesPanel.classList.add('active');
    }
};
