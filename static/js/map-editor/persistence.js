/**
 * Map Editor - Persistence Module
 * Handles API operations for furniture CRUD
 */

/**
 * Mixin that adds persistence capabilities to MapEditor
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with persistence methods
 */
export const PersistenceMixin = (Base) => class extends Base {

    /**
     * Create new furniture item via API
     * @param {Object} typeData - Furniture type data from palette
     * @param {number} x - X position
     * @param {number} y - Y position
     */
    async createFurniture(typeData, x, y) {
        try {
            // Get next number for this type
            const numResponse = await fetch(
                `${this.options.apiBaseUrl}/furniture/next-number/${this.currentZoneId}/${typeData.type}`
            );
            const numResult = await numResponse.json();
            const nextNumber = numResult.success
                ? numResult.next_number
                : typeData.type.toUpperCase() + '1';

            const response = await fetch(`${this.options.apiBaseUrl}/furniture`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({
                    zone_id: this.currentZoneId,
                    furniture_type: typeData.type,
                    number: nextNumber,
                    capacity: typeData.decorative ? 0 : typeData.capacity,
                    position_x: x,
                    position_y: y,
                    rotation: 0,
                    width: typeData.width,
                    height: typeData.height
                })
            });

            const result = await response.json();
            if (!result.success) throw new Error(result.error);

            const newItem = {
                id: result.furniture_id,
                number: nextNumber,
                furniture_type: typeData.type,
                position_x: x,
                position_y: y,
                rotation: 0,
                width: typeData.width,
                height: typeData.height,
                capacity: typeData.decorative ? 0 : typeData.capacity,
                type_fill_color: typeData.fill,
                type_stroke_color: typeData.stroke,
                is_decorative: typeData.decorative ? 1 : 0
            };

            this.furniture.push(newItem);

            const group = this.createFurnitureElement(newItem);
            this.furnitureLayer.appendChild(group);

            this.selectItem(newItem);
            this.emit('furnitureChanged', this.furniture.length);

            if (window.PuroBeach) {
                window.PuroBeach.showToast(`${nextNumber} creado`, 'success');
            }

        } catch (error) {
            console.error('Error creating furniture:', error);
            if (window.PuroBeach) {
                window.PuroBeach.showToast('Error al crear elemento', 'error');
            }
        }
    }

    /**
     * Save single furniture position to API
     * @param {Object} item - Furniture item
     */
    async saveFurniturePosition(item) {
        try {
            await fetch(`${this.options.apiBaseUrl}/furniture/${item.id}/position`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({
                    x: item.position_x,
                    y: item.position_y,
                    rotation: item.rotation
                })
            });
        } catch (error) {
            console.error('Error saving position:', error);
        }
    }

    /**
     * Save single furniture property to API
     * @param {number} id - Furniture ID
     * @param {string} property - Property name
     * @param {*} value - Property value
     */
    async saveFurnitureProperty(id, property, value) {
        try {
            await fetch(`${this.options.apiBaseUrl}/furniture/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({ [property]: value })
            });
        } catch (error) {
            console.error('Error saving property:', error);
        }
    }

    /**
     * Save positions for multiple items in batch
     * @param {Array} updates - Array of {id, x, y, rotation} objects
     */
    async saveBatchPositions(updates) {
        if (updates.length === 0) return;

        try {
            await fetch(`${this.options.apiBaseUrl}/furniture/batch-position`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({ updates })
            });
        } catch (error) {
            console.error('Error saving batch positions:', error);
        }
    }

    /**
     * Delete multiple furniture items in batch via API
     * @param {Array} ids - Array of furniture IDs to delete
     * @returns {Object} API response
     */
    async deleteBatchFurniture(ids) {
        if (ids.length === 0) return;

        const response = await fetch(`${this.options.apiBaseUrl}/furniture/batch-delete`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
            },
            body: JSON.stringify({ ids })
        });

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || 'Error al eliminar');
        }
        return result;
    }

    /**
     * Delete selected items (legacy method, now uses batch)
     */
    async deleteSelected() {
        await this.deleteSelectedItems();
    }
};
