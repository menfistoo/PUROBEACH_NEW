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
     * @param {Function} options.onAddTemporary - Callback when add temporary action is selected
     * @param {Function} options.onDeleteTemporary - Callback when delete temporary action is selected
     * @param {Function} options.getData - Function to get current map data
     * @param {Function} options.getZoneAtPosition - Function to get zone at SVG coordinates
     */
    constructor(options) {
        this.container = options.container;
        this.onBlock = options.onBlock || (() => {});
        this.onUnblock = options.onUnblock || (() => {});
        this.onAddTemporary = options.onAddTemporary || (() => {});
        this.onDeleteTemporary = options.onDeleteTemporary || (() => {});
        this.getData = options.getData || (() => null);
        this.getZoneAtPosition = options.getZoneAtPosition || (() => null);

        this.menuElement = null;
        this.emptySpaceMenuElement = null;
        this.currentFurnitureId = null;
        this.currentFurnitureNumber = null;
        this.currentFurnitureIsTemp = false;
        this.currentSelection = []; // Array of IDs for multi-select operations
        this.currentClickPosition = { x: 0, y: 0 };
        this.currentZoneId = null;

        this.init();
    }

    /**
     * Initialize context menu
     */
    init() {
        this.createMenuElement();
        this.createEmptySpaceMenuElement();
        this.setupEventListeners();
        this.setupEmptySpaceEventListeners();
    }

    /**
     * Create the context menu DOM element for furniture
     */
    createMenuElement() {
        // Remove existing if any
        const existing = document.getElementById('furniture-context-menu');
        if (existing) existing.remove();

        this.menuElement = document.createElement('div');
        this.menuElement.id = 'furniture-context-menu';
        this.menuElement.className = 'furniture-context-menu';
        this.menuElement.setAttribute('role', 'menu');
        this.menuElement.setAttribute('aria-label', 'Menu de mobiliario');
        this.menuElement.innerHTML = `
            <div class="context-menu-header" id="ctx-header">
                <span class="ctx-furniture-number"></span>
            </div>
            <div class="context-menu-item ctx-block" id="ctx-block" tabindex="0" role="menuitem">
                <i class="fas fa-ban"></i>
                <span>Bloquear</span>
            </div>
            <div class="context-menu-item ctx-unblock" id="ctx-unblock" tabindex="0" role="menuitem">
                <i class="fas fa-lock-open"></i>
                <span>Desbloquear</span>
            </div>
            <div class="context-menu-divider" role="separator"></div>
            <div class="context-menu-item ctx-view-block" id="ctx-view-block" tabindex="0" role="menuitem">
                <i class="fas fa-info-circle"></i>
                <span>Ver detalles del bloqueo</span>
            </div>
            <div class="context-menu-divider ctx-temp-divider" role="separator"></div>
            <div class="context-menu-item ctx-delete-temp" id="ctx-delete-temp" tabindex="0" role="menuitem">
                <i class="fas fa-trash"></i>
                <span>Eliminar Mobiliario Temporal</span>
            </div>
        `;

        document.body.appendChild(this.menuElement);
    }

    /**
     * Create the context menu DOM element for empty space
     */
    createEmptySpaceMenuElement() {
        // Remove existing if any
        const existing = document.getElementById('empty-space-context-menu');
        if (existing) existing.remove();

        this.emptySpaceMenuElement = document.createElement('div');
        this.emptySpaceMenuElement.id = 'empty-space-context-menu';
        this.emptySpaceMenuElement.className = 'furniture-context-menu';
        this.emptySpaceMenuElement.setAttribute('role', 'menu');
        this.emptySpaceMenuElement.setAttribute('aria-label', 'Menu de espacio vacio');
        this.emptySpaceMenuElement.innerHTML = `
            <div class="context-menu-header" id="ctx-empty-header">
                <span class="ctx-zone-name">Zona</span>
            </div>
            <div class="context-menu-item ctx-add-temp" id="ctx-add-temp" tabindex="0" role="menuitem">
                <i class="fas fa-plus-circle"></i>
                <span>Añadir Mobiliario Temporal</span>
            </div>
        `;

        document.body.appendChild(this.emptySpaceMenuElement);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Block option click/keyboard
        const blockItem = this.menuElement.querySelector('#ctx-block');
        const handleBlock = () => {
            // Check if multi-select or single
            if (this.currentSelection.length > 0) {
                // Multi-select: get furniture data for all selected items
                const beachMap = this.getData()?.beachMap;
                if (beachMap) {
                    const selectedData = beachMap.getSelectedFurnitureData();
                    const ids = selectedData.map(f => f.id);
                    const numbers = selectedData.map(f => f.number);
                    this.hide();
                    this.onBlock(ids, numbers);
                }
            } else {
                // Single selection
                const furnitureId = this.currentFurnitureId;
                const furnitureNumber = this.currentFurnitureNumber;
                this.hide();
                if (furnitureId) {
                    this.onBlock([furnitureId], [furnitureNumber]);
                }
            }
        };
        blockItem?.addEventListener('click', handleBlock);
        blockItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleBlock();
            }
        });

        // Unblock option click/keyboard
        const unblockItem = this.menuElement.querySelector('#ctx-unblock');
        const handleUnblock = () => {
            // Check if multi-select or single
            if (this.currentSelection.length > 0) {
                // Multi-select: get furniture data for all selected items
                const beachMap = this.getData()?.beachMap;
                if (beachMap) {
                    const selectedData = beachMap.getSelectedFurnitureData();
                    const ids = selectedData.map(f => f.id);
                    const numbers = selectedData.map(f => f.number);
                    this.hide();
                    this.onUnblock(ids, numbers);
                }
            } else {
                // Single selection
                const furnitureId = this.currentFurnitureId;
                const furnitureNumber = this.currentFurnitureNumber;
                this.hide();
                if (furnitureId) {
                    this.onUnblock([furnitureId], [furnitureNumber]);
                }
            }
        };
        unblockItem?.addEventListener('click', handleUnblock);
        unblockItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleUnblock();
            }
        });

        // View block details click/keyboard
        const viewBlockItem = this.menuElement.querySelector('#ctx-view-block');
        const handleViewBlock = () => {
            // Save value before hide() clears it
            const furnitureId = this.currentFurnitureId;
            this.hide();
            if (furnitureId) {
                this.showBlockDetails(furnitureId);
            }
        };
        viewBlockItem?.addEventListener('click', handleViewBlock);
        viewBlockItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleViewBlock();
            }
        });

        // Delete temporary furniture click/keyboard
        const deleteTempItem = this.menuElement.querySelector('#ctx-delete-temp');
        const handleDeleteTemp = () => {
            // Check if multi-select or single
            if (this.currentSelection.length > 0) {
                // Multi-select: get furniture data for all selected items
                const beachMap = this.getData()?.beachMap;
                if (beachMap) {
                    const selectedData = beachMap.getSelectedFurnitureData();
                    const ids = selectedData.map(f => f.id);
                    const numbers = selectedData.map(f => f.number);
                    this.hide();
                    this.onDeleteTemporary(ids, numbers);
                }
            } else {
                // Single selection
                const furnitureId = this.currentFurnitureId;
                const furnitureNumber = this.currentFurnitureNumber;
                this.hide();
                if (furnitureId) {
                    this.onDeleteTemporary([furnitureId], [furnitureNumber]);
                }
            }
        };
        deleteTempItem?.addEventListener('click', handleDeleteTemp);
        deleteTempItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleDeleteTemp();
            }
        });

        // Hide on click outside
        document.addEventListener('click', (e) => {
            if (!this.menuElement.contains(e.target) &&
                !this.emptySpaceMenuElement?.contains(e.target)) {
                this.hide();
                this.hideEmptySpaceMenu();
            }
        });

        // Hide on scroll
        document.addEventListener('scroll', () => {
            this.hide();
            this.hideEmptySpaceMenu();
        }, true);

        // Hide on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hide();
                this.hideEmptySpaceMenu();
            }
        });
    }

    /**
     * Setup event listeners for empty space menu
     */
    setupEmptySpaceEventListeners() {
        // Add temporary furniture click/keyboard
        const addTempItem = this.emptySpaceMenuElement?.querySelector('#ctx-add-temp');
        const handleAddTemp = () => {
            const position = { ...this.currentClickPosition };
            const zoneId = this.currentZoneId;
            this.hideEmptySpaceMenu();
            this.onAddTemporary(position.x, position.y, zoneId);
        };
        addTempItem?.addEventListener('click', handleAddTemp);
        addTempItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleAddTemp();
            }
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

        // Hide empty space menu if open
        this.hideEmptySpaceMenu();

        // Check if this furniture is part of a multi-selection
        const beachMap = this.getData()?.beachMap;
        const selectedIds = beachMap ? beachMap.getSelectedFurniture() : [];
        const isMultiSelect = selectedIds.length > 1 && selectedIds.includes(furniture.id);

        if (isMultiSelect) {
            // Store all selected IDs for multi-select operations
            this.currentSelection = selectedIds;
            this.currentFurnitureId = null; // Clear single ID to indicate multi-select
            this.currentFurnitureNumber = null;
        } else {
            // Single selection
            this.currentSelection = [];
            this.currentFurnitureId = furniture.id;
            this.currentFurnitureNumber = furniture.number;
        }

        this.currentFurnitureIsTemp = !!furniture.is_temporary;

        // Update header
        const header = this.menuElement.querySelector('.ctx-furniture-number');
        if (header) {
            if (isMultiSelect) {
                header.textContent = `${selectedIds.length} items seleccionados`;
            } else {
                const tempLabel = furniture.is_temporary ? ' (Temporal)' : '';
                header.textContent = `Mobiliario ${furniture.number}${tempLabel}`;
            }
        }

        // Check if blocked
        const data = this.getData();
        const isBlocked = data?.blocks && data.blocks[furniture.id];
        const isTemporary = !!furniture.is_temporary;

        // Show/hide appropriate options
        const blockItem = this.menuElement.querySelector('.ctx-block');
        const unblockItem = this.menuElement.querySelector('.ctx-unblock');
        const viewBlockItem = this.menuElement.querySelector('.ctx-view-block');
        const tempDivider = this.menuElement.querySelector('.ctx-temp-divider');
        const deleteTempItem = this.menuElement.querySelector('.ctx-delete-temp');

        if (isBlocked) {
            blockItem.style.display = 'none';
            unblockItem.style.display = 'flex';
            viewBlockItem.style.display = 'flex';
        } else {
            blockItem.style.display = 'flex';
            unblockItem.style.display = 'none';
            viewBlockItem.style.display = 'none';
        }

        // Show delete option only for temporary furniture
        if (isTemporary) {
            tempDivider.style.display = 'block';
            deleteTempItem.style.display = 'flex';
        } else {
            tempDivider.style.display = 'none';
            deleteTempItem.style.display = 'none';
        }

        // Position the menu
        this.positionMenu(event.clientX, event.clientY);

        // Show
        this.menuElement.classList.add('visible');
    }

    /**
     * Show the empty space context menu
     * @param {MouseEvent} event - Right-click event
     * @param {number} svgX - SVG X coordinate
     * @param {number} svgY - SVG Y coordinate
     * @param {Object|null} zone - Zone data if click is within a zone
     */
    showEmptySpaceMenu(event, svgX, svgY, zone = null) {
        event.preventDefault();
        event.stopPropagation();

        // Hide furniture menu if open
        this.hide();

        this.currentClickPosition = { x: svgX, y: svgY };
        this.currentZoneId = zone?.id || null;

        // Update header with zone name
        const header = this.emptySpaceMenuElement?.querySelector('.ctx-zone-name');
        if (header) {
            header.textContent = zone ? zone.name : 'Mapa';
        }

        // Position the menu
        this.positionEmptySpaceMenu(event.clientX, event.clientY);

        // Show
        this.emptySpaceMenuElement?.classList.add('visible');
    }

    /**
     * Position the empty space menu at coordinates
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     */
    positionEmptySpaceMenu(x, y) {
        const menu = this.emptySpaceMenuElement;
        if (!menu) return;

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
     * Hide the empty space context menu
     */
    hideEmptySpaceMenu() {
        this.emptySpaceMenuElement?.classList.remove('visible');
        this.currentClickPosition = { x: 0, y: 0 };
        this.currentZoneId = null;
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
        this.currentFurnitureIsTemp = false;
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
     * Check if furniture is temporary
     * @param {number} furnitureId - Furniture ID
     * @returns {boolean}
     */
    isTemporary(furnitureId) {
        const data = this.getData();
        const furniture = data?.furniture?.find(f => f.id === furnitureId);
        return !!furniture?.is_temporary;
    }

    /**
     * Clean up
     */
    destroy() {
        this.menuElement?.remove();
        this.menuElement = null;
        this.emptySpaceMenuElement?.remove();
        this.emptySpaceMenuElement = null;
    }
}

export default ContextMenuManager;
