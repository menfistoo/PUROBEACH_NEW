/**
 * Map Editor - Operations Module
 * Handles multi-selection operations: move, delete, align, distribute, rotate
 */

/**
 * Mixin that adds multi-selection operations to MapEditor
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with operation methods
 */
export const OperationsMixin = (Base) => class extends Base {

    /**
     * Move all selected items by delta
     * @param {number} deltaX - X offset
     * @param {number} deltaY - Y offset
     */
    async moveSelectedItems(deltaX, deltaY) {
        const selectedItems = this.getSelectedItems();
        if (selectedItems.length === 0) return;

        const updates = [];

        selectedItems.forEach(item => {
            let newX = item.position_x + deltaX;
            let newY = item.position_y + deltaY;

            // Snap to grid
            newX = Math.round(newX / this.options.snapToGrid) * this.options.snapToGrid;
            newY = Math.round(newY / this.options.snapToGrid) * this.options.snapToGrid;

            // Bounds check
            newX = Math.max(0, Math.min(newX, this.canvasConfig.width - item.width));
            newY = Math.max(0, Math.min(newY, this.canvasConfig.height - item.height));

            item.position_x = newX;
            item.position_y = newY;

            const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
            if (group) {
                group.setAttribute('transform',
                    `translate(${newX}, ${newY}) rotate(${item.rotation || 0}, ${item.width / 2}, ${item.height / 2})`
                );
            }

            updates.push({ id: item.id, x: newX, y: newY, rotation: item.rotation });
        });

        // Batch save positions
        await this.saveBatchPositions(updates);
    }

    /**
     * Delete all selected items
     */
    async deleteSelectedItems() {
        const selectedItems = this.getSelectedItems();
        if (selectedItems.length === 0) return;

        const count = selectedItems.length;
        const confirmMsg = count === 1
            ? '¿Eliminar el elemento seleccionado?'
            : `¿Eliminar ${count} elementos seleccionados?`;

        const confirmed = await (window.PuroBeach
            ? window.PuroBeach.confirmAction({
                title: 'Confirmar eliminación',
                message: confirmMsg,
                confirmText: 'Eliminar',
                confirmClass: 'btn-danger',
                iconClass: 'fa-trash-alt'
            })
            : Promise.resolve(confirm(confirmMsg)));

        if (!confirmed) return;

        try {
            const ids = selectedItems.map(item => item.id);
            await this.deleteBatchFurniture(ids);

            // Remove from DOM and local state
            ids.forEach(id => {
                const group = this.furnitureLayer.querySelector(`[data-id="${id}"]`);
                if (group) group.remove();
            });

            this.furniture = this.furniture.filter(f => !ids.includes(f.id));
            this.deselectAll();
            this.emit('furnitureChanged', this.furniture.length);

            if (window.PuroBeach) {
                window.PuroBeach.showToast(`${count} elemento(s) eliminado(s)`, 'success');
            }
        } catch (error) {
            console.error('Error deleting items:', error);
            if (window.PuroBeach) {
                window.PuroBeach.showToast(error.message || 'Error al eliminar', 'error');
            }
        }
    }

    /**
     * Align selected items
     * @param {string} alignment - Alignment type (left, right, top, bottom, center-h, center-v, distribute-h, distribute-v)
     */
    async alignSelectedItems(alignment) {
        const selectedItems = this.getSelectedItems();
        if (selectedItems.length < 2) return;

        const updates = [];
        let reference;

        // Calculate reference point based on alignment type
        switch (alignment) {
            case 'left':
                reference = Math.min(...selectedItems.map(i => i.position_x));
                selectedItems.forEach(item => {
                    item.position_x = reference;
                    updates.push({ id: item.id, x: item.position_x, y: item.position_y, rotation: item.rotation });
                });
                break;

            case 'right':
                reference = Math.max(...selectedItems.map(i => i.position_x + i.width));
                selectedItems.forEach(item => {
                    item.position_x = reference - item.width;
                    updates.push({ id: item.id, x: item.position_x, y: item.position_y, rotation: item.rotation });
                });
                break;

            case 'top':
                reference = Math.min(...selectedItems.map(i => i.position_y));
                selectedItems.forEach(item => {
                    item.position_y = reference;
                    updates.push({ id: item.id, x: item.position_x, y: item.position_y, rotation: item.rotation });
                });
                break;

            case 'bottom':
                reference = Math.max(...selectedItems.map(i => i.position_y + i.height));
                selectedItems.forEach(item => {
                    item.position_y = reference - item.height;
                    updates.push({ id: item.id, x: item.position_x, y: item.position_y, rotation: item.rotation });
                });
                break;

            case 'center-h':
                reference = selectedItems.reduce((sum, i) => sum + i.position_x + i.width / 2, 0) / selectedItems.length;
                selectedItems.forEach(item => {
                    item.position_x = Math.round((reference - item.width / 2) / this.options.snapToGrid) * this.options.snapToGrid;
                    updates.push({ id: item.id, x: item.position_x, y: item.position_y, rotation: item.rotation });
                });
                break;

            case 'center-v':
                reference = selectedItems.reduce((sum, i) => sum + i.position_y + i.height / 2, 0) / selectedItems.length;
                selectedItems.forEach(item => {
                    item.position_y = Math.round((reference - item.height / 2) / this.options.snapToGrid) * this.options.snapToGrid;
                    updates.push({ id: item.id, x: item.position_x, y: item.position_y, rotation: item.rotation });
                });
                break;

            case 'distribute-h':
                this.distributeItems(selectedItems, 'horizontal', updates);
                break;

            case 'distribute-v':
                this.distributeItems(selectedItems, 'vertical', updates);
                break;
        }

        // Update DOM
        updates.forEach(update => {
            const item = this.furniture.find(f => f.id === update.id);
            if (item) {
                const group = this.furnitureLayer.querySelector(`[data-id="${update.id}"]`);
                if (group) {
                    group.setAttribute('transform',
                        `translate(${item.position_x}, ${item.position_y}) rotate(${item.rotation || 0}, ${item.width / 2}, ${item.height / 2})`
                    );
                }
            }
        });

        // Batch save
        await this.saveBatchPositions(updates);

        if (window.PuroBeach) {
            window.PuroBeach.showToast('Elementos alineados', 'success');
        }
    }

    /**
     * Distribute items evenly across canvas
     * @param {Array} items - Items to distribute
     * @param {string} direction - 'horizontal' or 'vertical'
     * @param {Array} updates - Updates array to populate
     */
    distributeItems(items, direction, updates) {
        if (items.length < 2) return;

        const margin = 50; // Interior margin from canvas edges
        const canvasSize = direction === 'horizontal'
            ? this.canvasConfig.width
            : this.canvasConfig.height;

        // Available space = canvas size minus margins on both sides
        const availableSpace = canvasSize - (margin * 2);

        // Calculate total size of all items
        const totalItemSize = items.reduce((sum, item) =>
            sum + (direction === 'horizontal' ? item.width : item.height), 0
        );

        // Calculate uniform spacing between items
        // For N items, we have N-1 gaps between them
        const totalGapSpace = availableSpace - totalItemSize;
        const uniformSpacing = items.length > 1 ? totalGapSpace / (items.length - 1) : 0;

        // Sort items by current position to maintain relative order
        const sorted = [...items].sort((a, b) =>
            direction === 'horizontal'
                ? a.position_x - b.position_x
                : a.position_y - b.position_y
        );

        // Calculate average position for the perpendicular axis (to align items)
        const avgPerpendicularPos = direction === 'horizontal'
            ? items.reduce((sum, item) => sum + item.position_y, 0) / items.length
            : items.reduce((sum, item) => sum + item.position_x, 0) / items.length;

        // Round perpendicular position to integer only
        const alignedPerpendicularPos = Math.round(avgPerpendicularPos);

        // Position items with precise spacing
        let currentPos = margin;

        sorted.forEach((item, index) => {
            const precisePos = Math.round(currentPos);

            if (direction === 'horizontal') {
                item.position_x = precisePos;
                item.position_y = alignedPerpendicularPos;
            } else {
                item.position_y = precisePos;
                item.position_x = alignedPerpendicularPos;
            }

            updates.push({ id: item.id, x: item.position_x, y: item.position_y, rotation: item.rotation });

            // Move to next position with exact spacing
            currentPos += (direction === 'horizontal' ? item.width : item.height) + uniformSpacing;
        });
    }

    /**
     * Apply rotation to all selected items
     * @param {number} rotation - Rotation angle in degrees
     */
    async rotateSelectedItems(rotation) {
        const selectedItems = this.getSelectedItems();
        if (selectedItems.length === 0) return;

        const updates = [];

        selectedItems.forEach(item => {
            item.rotation = rotation;

            const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
            if (group) {
                group.setAttribute('transform',
                    `translate(${item.position_x}, ${item.position_y}) rotate(${rotation}, ${item.width / 2}, ${item.height / 2})`
                );
            }

            updates.push({ id: item.id, x: item.position_x, y: item.position_y, rotation: rotation });
        });

        await this.saveBatchPositions(updates);
    }

    /**
     * Update property for currently selected item(s)
     * @param {string} property - Property name
     * @param {*} value - Property value
     */
    async updateSelectedProperty(property, value) {
        const selectedItems = this.getSelectedItems();
        if (selectedItems.length === 0) return;

        // For single selection, update the item directly
        const item = selectedItems[0];

        // Handle position updates
        if (property === 'position_x' || property === 'position_y') {
            const snapped = Math.round(value / this.options.snapToGrid) * this.options.snapToGrid;
            item[property] = snapped;

            const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
            if (group) {
                group.setAttribute('transform',
                    `translate(${item.position_x}, ${item.position_y}) rotate(${item.rotation || 0}, ${item.width / 2}, ${item.height / 2})`
                );
            }

            await this.saveFurniturePosition(item);
            return;
        }

        item[property] = value;

        if (property === 'rotation') {
            const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
            if (group) {
                group.setAttribute('transform',
                    `translate(${item.position_x}, ${item.position_y}) rotate(${value}, ${item.width / 2}, ${item.height / 2})`
                );
            }
            await this.saveFurniturePosition(item);
        } else if (property === 'width' || property === 'height' || property === 'fill_color') {
            // Re-render the shape when size or color changes
            const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
            if (group) {
                const type = this.furnitureTypes[item.furniture_type] || {};
                const oldShape = group.querySelector('rect, ellipse');
                if (oldShape) {
                    const newShape = this.createShape(item, type);
                    oldShape.replaceWith(newShape);
                }
                // Update number position if size changed
                if (property === 'width' || property === 'height') {
                    const text = group.querySelector('.furniture-number');
                    if (text) {
                        text.setAttribute('x', item.width / 2);
                        text.setAttribute('y', item.height / 2);
                    }
                    // Update transform for center rotation point
                    group.setAttribute('transform',
                        `translate(${item.position_x}, ${item.position_y}) rotate(${item.rotation || 0}, ${item.width / 2}, ${item.height / 2})`
                    );
                }
            }
            await this.saveFurnitureProperty(item.id, property, value);
        } else {
            await this.saveFurnitureProperty(item.id, property, value);
        }
    }
};
