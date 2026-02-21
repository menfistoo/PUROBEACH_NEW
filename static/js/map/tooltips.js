/**
 * Map Tooltips Module
 * Handles tooltip creation, display, and positioning for furniture items
 */

/**
 * Create and manage tooltips for the beach map
 */
export class TooltipManager {
    constructor(container, colors) {
        this.container = container;
        this.colors = colors;
        this.tooltip = null;
    }

    /**
     * Get label text for customer (room# for interno, name for externo)
     * @param {Object} availability - Availability data with customer info
     * @returns {string} Customer label
     */
    getCustomerLabel(availability) {
        if (!availability) return '';

        if (availability.customer_type === 'interno' && availability.room_number) {
            return availability.room_number;
        } else if (availability.first_name) {
            const name = availability.first_name;
            return name.length > 6 ? name.substring(0, 5) + '.' : name;
        } else if (availability.customer_name) {
            const firstName = availability.customer_name.split(' ')[0];
            return firstName.length > 6 ? firstName.substring(0, 5) + '.' : firstName;
        }
        return '';
    }

    /**
     * Show tooltip with customer information
     * @param {Event} event - Mouse event
     * @param {Object} availability - Availability data
     */
    show(event, availability) {
        if (!this.tooltip) {
            this.create();
        }

        const name = this._escape(availability.customer_name || 'Sin nombre');
        let content = `<strong>${name}</strong>`;

        if (availability.customer_type === 'interno' && availability.room_number) {
            content += `<br><small>Hab. ${this._escape(availability.room_number)}</small>`;
        }

        if (availability.vip_status) {
            content += ` <span class="badge bg-warning text-dark" style="font-size: 9px;">VIP</span>`;
        }

        if (availability.num_people) {
            const n = parseInt(availability.num_people, 10) || 0;
            content += `<br><small>${n} persona${n > 1 ? 's' : ''}</small>`;
        }

        this.tooltip.innerHTML = content;
        this.tooltip.style.display = 'block';
        this.move(event);
    }

    /**
     * Show tooltip with block information
     * @param {Event} event - Mouse event
     * @param {Object} blockInfo - Block information from API
     * @param {string} furnitureNumber - Furniture number/code
     */
    showBlock(event, blockInfo, furnitureNumber) {
        if (!this.tooltip) {
            this.create();
        }

        const blockTypeNames = {
            'maintenance': 'Mantenimiento',
            'vip_hold': 'Reserva VIP',
            'event': 'Evento',
            'other': 'Bloqueado'
        };

        const typeName = blockTypeNames[blockInfo.block_type] || this._escape(blockInfo.name) || 'Bloqueado';
        let content = `<strong>${typeName}</strong>`;
        content += `<br><small>Mobiliario: ${this._escape(furnitureNumber)}</small>`;

        if (blockInfo.reason) {
            content += `<br><small>Motivo: ${this._escape(blockInfo.reason)}</small>`;
        }

        if (blockInfo.end_date) {
            content += `<br><small>Hasta: ${this._escape(blockInfo.end_date)}</small>`;
        }

        // Add visual indicator of block color
        const safeColor = this._sanitizeColor(blockInfo.color) || '#999';
        content = `<span style="display: inline-block; width: 10px; height: 10px; background: ${safeColor}; border-radius: 2px; margin-right: 6px;"></span>${content}`;

        this.tooltip.innerHTML = content;
        this.tooltip.style.display = 'block';
        this.move(event);
    }

    /**
     * Hide the tooltip
     */
    hide() {
        if (this.tooltip) {
            this.tooltip.style.display = 'none';
        }
    }

    /**
     * Move tooltip to follow cursor
     * @param {Event} event - Mouse event
     */
    move(event) {
        if (!this.tooltip) return;

        const offsetX = 10;
        const offsetY = -10;
        const tooltipRect = this.tooltip.getBoundingClientRect();
        const containerRect = this.container.getBoundingClientRect();

        let left = event.clientX - containerRect.left + offsetX;
        let top = event.clientY - containerRect.top + offsetY - tooltipRect.height;

        // Keep tooltip within container bounds
        if (left + tooltipRect.width > containerRect.width) {
            left = event.clientX - containerRect.left - tooltipRect.width - offsetX;
        }
        if (top < 0) {
            top = event.clientY - containerRect.top + 20;
        }

        this.tooltip.style.left = `${left}px`;
        this.tooltip.style.top = `${top}px`;
    }

    /**
     * Create the tooltip DOM element
     */
    create() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'map-tooltip';
        this.tooltip.style.cssText = `
            position: absolute;
            display: none;
            background: ${this.colors.tooltipBg};
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            max-width: 200px;
            z-index: 1000;
            pointer-events: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            line-height: 1.4;
            opacity: 0.95;
        `;
        this.container.style.position = 'relative';
        this.container.appendChild(this.tooltip);
    }

    /**
     * Escape HTML entities to prevent XSS
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     * @private
     */
    _escape(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Sanitize a CSS color value
     * @param {string} color - Color value
     * @returns {string|null} Sanitized color or null
     * @private
     */
    _sanitizeColor(color) {
        if (!color) return null;
        if (/^#[0-9A-Fa-f]{3,8}$/.test(color)) return color;
        if (/^(rgb|hsl)a?\([^)]+\)$/.test(color)) return color;
        if (/^[a-zA-Z]+$/.test(color)) return color;
        return null;
    }

    /**
     * Clean up tooltip element
     */
    destroy() {
        if (this.tooltip && this.tooltip.parentNode) {
            this.tooltip.parentNode.removeChild(this.tooltip);
            this.tooltip = null;
        }
    }
}
