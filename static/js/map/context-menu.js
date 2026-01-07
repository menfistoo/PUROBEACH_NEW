/**
 * Context Menu Module
 * Handles right-click context menu for furniture items
 */

import { showToast } from './utils.js';

/**
 * Block type definitions (should match backend)
 */
const BLOCK_TYPES = {
    'maintenance': { name: 'Mantenimiento', color: '#9CA3AF', icon: '🔧' },
    'vip_hold': { name: 'Reserva VIP', color: '#D4AF37', icon: '⭐' },
    'event': { name: 'Evento', color: '#3B82F6', icon: '📅' },
    'other': { name: 'Otro', color: '#6B7280', icon: '🚫' }
};

/**
 * Context menu manager for beach map
 */
export class ContextMenuManager {
    /**
     * @param {Object} options - Configuration options
     * @param {HTMLElement} options.container - Map container element
     * @param {Function} options.onBlock - Callback when block action is selected
     * @param {Function} options.onUnblock - Callback when unblock action is selected
     * @param {Function} options.getData - Function to get current map data
     */
    constructor(options) {
        this.container = options.container;
        this.onBlock = options.onBlock || (() => {});
        this.onUnblock = options.onUnblock || (() => {});
        this.getData = options.getData || (() => null);

        this.menuElement = null;
        this.currentFurnitureId = null;
        this.currentFurnitureNumber = null;

        this.init();
    }

    /**
     * Initialize context menu
     */
    init() {
        this.createMenuElement();
        this.setupEventListeners();
    }

    /**
     * Create the context menu DOM element
     */
    createMenuElement() {
        // Remove existing if any
        const existing = document.getElementById('furniture-context-menu');
        if (existing) existing.remove();

        this.menuElement = document.createElement('div');
        this.menuElement.id = 'furniture-context-menu';
        this.menuElement.className = 'furniture-context-menu';
        this.menuElement.innerHTML = `
            <div class="context-menu-header" id="ctx-header">
                <span class="ctx-furniture-number"></span>
            </div>
            <div class="context-menu-item ctx-block" id="ctx-block">
                <i class="fas fa-ban"></i>
                <span>Bloquear</span>
            </div>
            <div class="context-menu-item ctx-unblock" id="ctx-unblock">
                <i class="fas fa-check-circle"></i>
                <span>Desbloquear</span>
            </div>
            <div class="context-menu-divider"></div>
            <div class="context-menu-item ctx-view-block" id="ctx-view-block">
                <i class="fas fa-info-circle"></i>
                <span>Ver detalles del bloqueo</span>
            </div>
        `;

        document.body.appendChild(this.menuElement);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Block option click
        const blockItem = this.menuElement.querySelector('#ctx-block');
        blockItem?.addEventListener('click', () => {
            // Save values before hide() clears them
            const furnitureId = this.currentFurnitureId;
            const furnitureNumber = this.currentFurnitureNumber;
            this.hide();
            if (furnitureId) {
                this.onBlock(furnitureId, furnitureNumber);
            }
        });

        // Unblock option click
        const unblockItem = this.menuElement.querySelector('#ctx-unblock');
        unblockItem?.addEventListener('click', () => {
            // Save values before hide() clears them
            const furnitureId = this.currentFurnitureId;
            const furnitureNumber = this.currentFurnitureNumber;
            this.hide();
            if (furnitureId) {
                this.onUnblock(furnitureId, furnitureNumber);
            }
        });

        // View block details
        const viewBlockItem = this.menuElement.querySelector('#ctx-view-block');
        viewBlockItem?.addEventListener('click', () => {
            // Save value before hide() clears it
            const furnitureId = this.currentFurnitureId;
            this.hide();
            if (furnitureId) {
                this.showBlockDetails(furnitureId);
            }
        });

        // Hide on click outside
        document.addEventListener('click', (e) => {
            if (!this.menuElement.contains(e.target)) {
                this.hide();
            }
        });

        // Hide on scroll
        document.addEventListener('scroll', () => this.hide(), true);

        // Hide on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.hide();
        });
    }

    /**
     * Show the context menu at the specified position
     * @param {MouseEvent} event - Right-click event
     * @param {Object} furniture - Furniture item data
     */
    show(event, furniture) {
        event.preventDefault();
        event.stopPropagation();

        this.currentFurnitureId = furniture.id;
        this.currentFurnitureNumber = furniture.number;

        // Update header
        const header = this.menuElement.querySelector('.ctx-furniture-number');
        if (header) {
            header.textContent = `Mobiliario ${furniture.number}`;
        }

        // Check if blocked
        const data = this.getData();
        const isBlocked = data?.blocks && data.blocks[furniture.id];

        // Show/hide appropriate options
        const blockItem = this.menuElement.querySelector('.ctx-block');
        const unblockItem = this.menuElement.querySelector('.ctx-unblock');
        const viewBlockItem = this.menuElement.querySelector('.ctx-view-block');

        if (isBlocked) {
            blockItem.style.display = 'none';
            unblockItem.style.display = 'flex';
            viewBlockItem.style.display = 'flex';
        } else {
            blockItem.style.display = 'flex';
            unblockItem.style.display = 'none';
            viewBlockItem.style.display = 'none';
        }

        // Position the menu
        this.positionMenu(event.clientX, event.clientY);

        // Show
        this.menuElement.classList.add('visible');
    }

    /**
     * Position the menu at coordinates, adjusting for viewport edges
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     */
    positionMenu(x, y) {
        const menu = this.menuElement;
        const menuRect = menu.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // Adjust X if menu would overflow right
        if (x + menuRect.width > viewportWidth) {
            x = viewportWidth - menuRect.width - 10;
        }

        // Adjust Y if menu would overflow bottom
        if (y + menuRect.height > viewportHeight) {
            y = viewportHeight - menuRect.height - 10;
        }

        menu.style.left = `${Math.max(10, x)}px`;
        menu.style.top = `${Math.max(10, y)}px`;
    }

    /**
     * Hide the context menu
     */
    hide() {
        this.menuElement?.classList.remove('visible');
        this.currentFurnitureId = null;
        this.currentFurnitureNumber = null;
    }

    /**
     * Show block details in a toast
     * @param {number} furnitureId - Furniture ID (optional, uses currentFurnitureId if not provided)
     */
    showBlockDetails(furnitureId = null) {
        const data = this.getData();
        const id = furnitureId || this.currentFurnitureId;
        const blockInfo = data?.blocks?.[id];

        if (!blockInfo) {
            showToast('No hay información de bloqueo', 'info');
            return;
        }

        const blockType = BLOCK_TYPES[blockInfo.block_type] || BLOCK_TYPES.other;
        let message = `${blockType.icon} ${blockType.name}`;

        if (blockInfo.reason) {
            message += ` - ${blockInfo.reason}`;
        }

        if (blockInfo.end_date) {
            message += ` (Hasta: ${blockInfo.end_date})`;
        }

        showToast(message, 'info');
    }

    /**
     * Check if furniture is blocked
     * @param {number} furnitureId - Furniture ID
     * @returns {boolean}
     */
    isBlocked(furnitureId) {
        const data = this.getData();
        return !!(data?.blocks && data.blocks[furnitureId]);
    }

    /**
     * Get block info for furniture
     * @param {number} furnitureId - Furniture ID
     * @returns {Object|null}
     */
    getBlockInfo(furnitureId) {
        const data = this.getData();
        return data?.blocks?.[furnitureId] || null;
    }

    /**
     * Clean up
     */
    destroy() {
        this.menuElement?.remove();
        this.menuElement = null;
    }
}

export default ContextMenuManager;
