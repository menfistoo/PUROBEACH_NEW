/**
 * Beach Map Interactive Controller
 * Main class that coordinates all map modules
 */

import { loadCSSVariables, formatDateDisplay, showToast } from './utils.js';
import { TooltipManager } from './tooltips.js';
import { SelectionManager } from './selection.js';
import { NavigationManager } from './navigation.js';
import { InteractionManager } from './interaction.js';
import { ContextMenuManager } from './context-menu.js';
import {
    createSVG,
    renderZones,
    renderDecorativeItems,
    renderFurniture,
    updateLegend
} from './renderer.js';
import { OfflineManager } from '../offline/index.js';

/**
 * Main BeachMap class
 */
export class BeachMap {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container #${containerId} not found`);
        }

        // Load CSS variables for configurable values
        const cssVars = loadCSSVariables();

        // Configuration (with CSS variable fallbacks)
        this.options = {
            apiUrl: '/beach/api/map/data',
            autoRefreshInterval: cssVars.autoRefreshMs,
            enableDragDrop: false,
            enableZoom: true,
            minZoom: cssVars.minZoom,
            maxZoom: cssVars.maxZoom,
            snapToGrid: cssVars.snapGrid,
            ...options
        };

        // Store colors from CSS variables
        this.colors = cssVars.colors;

        // State
        this.currentDate = this.options.initialDate || new Date().toISOString().split('T')[0];
        this.data = null;
        this.autoRefreshTimer = null;

        // DOM elements
        this.svg = null;
        this.zonesLayer = null;
        this.decorativeLayer = null;
        this.furnitureLayer = null;
        this.selectionLayer = null;

        // Initialize managers
        this.selection = new SelectionManager();
        this.navigation = new NavigationManager({
            minZoom: this.options.minZoom,
            maxZoom: this.options.maxZoom
        });
        this.interaction = new InteractionManager({
            snapToGrid: this.options.snapToGrid,
            // Optimistic update: sync local data cache when position changes
            onPositionUpdate: (furnitureId, x, y) => {
                const furniture = this.data?.furniture?.find(f => f.id === furnitureId);
                if (furniture) {
                    furniture.position_x = x;
                    furniture.position_y = y;
                }
            }
        });
        this.tooltipManager = new TooltipManager(this.container, this.colors);

        // Offline manager
        this.offlineManager = null;
        this.isOfflineMode = false;

        // Context menu manager (initialized after container is ready)
        this.contextMenu = new ContextMenuManager({
            container: this.container,
            getData: () => this.data,
            onBlock: (furnitureId, furnitureNumber) => {
                if (this.callbacks.onBlockRequest) {
                    this.callbacks.onBlockRequest([furnitureId], [furnitureNumber]);
                }
            },
            onUnblock: (furnitureId, furnitureNumber) => {
                if (this.callbacks.onUnblockRequest) {
                    this.callbacks.onUnblockRequest(furnitureId, furnitureNumber);
                }
            },
            onAddTemporary: (x, y, zoneId) => {
                if (this.callbacks.onAddTemporaryRequest) {
                    this.callbacks.onAddTemporaryRequest(x, y, zoneId);
                }
            },
            onDeleteTemporary: (furnitureId, furnitureNumber) => {
                if (this.callbacks.onDeleteTemporaryRequest) {
                    this.callbacks.onDeleteTemporaryRequest(furnitureId, furnitureNumber);
                }
            },
            getZoneAtPosition: (x, y) => this.getZoneAtPosition(x, y)
        });

        // Event callbacks
        this.callbacks = {
            onSelect: null,
            onDeselect: null,
            onDateChange: null,
            onFurnitureClick: null,
            onBlockRequest: null,
            onUnblockRequest: null,
            onAddTemporaryRequest: null,
            onDeleteTemporaryRequest: null,
            onError: null,
            onRender: null
        };

        // Wire up selection callbacks
        this.selection.on('onSelect', (id) => {
            if (this.callbacks.onSelect) this.callbacks.onSelect(id);
        });
        this.selection.on('onDeselect', (id) => {
            if (this.callbacks.onDeselect) this.callbacks.onDeselect(id);
        });

        // Wire up navigation callbacks
        this.navigation.on('onDateChange', (date) => {
            if (this.callbacks.onDateChange) this.callbacks.onDateChange(date);
        });
        this.navigation.on('onZoomChange', () => {
            this.applyZoom();
            this.interaction.setZoom(this.navigation.getZoom());
        });

        // Click suppression for drag-end
        this._suppressNextClick = false;

        // Bind methods
        this.handleFurnitureClick = this.handleFurnitureClick.bind(this);
        this.handleFurnitureContextMenu = this.handleFurnitureContextMenu.bind(this);
        this.handleTempFurnitureMouseDown = this.handleTempFurnitureMouseDown.bind(this);
        this.handleTempFurnitureMouseMove = this.handleTempFurnitureMouseMove.bind(this);
        this.handleTempFurnitureMouseUp = this.handleTempFurnitureMouseUp.bind(this);

        // Initialize
        this.init();
    }

    async init() {
        this.createSVG();
        this.setupEventListeners();
        await this.loadData();
        this.render();

        // Initialize offline functionality
        await this.initOffline();
    }

    /**
     * Initialize offline functionality
     */
    async initOffline() {
        // Get UI elements
        const banner = document.getElementById('offline-banner');
        const syncButton = document.getElementById('sync-button');
        const syncButtonText = document.getElementById('sync-button-text');
        const offlineSyncTime = document.getElementById('offline-sync-time');

        if (!banner || !syncButton) {
            console.warn('Offline UI elements not found');
            return;
        }

        this.offlineManager = new OfflineManager({
            apiUrl: this.options.apiUrl,

            onOffline: () => {
                this.isOfflineMode = true;
                document.body.classList.add('offline-mode');
                banner.classList.add('visible');
                offlineSyncTime.textContent = this.offlineManager.getLastSyncTimeFormatted();

                syncButton.className = 'sync-button offline';
                syncButton.querySelector('i').className = 'fas fa-times';
                syncButtonText.textContent = 'Sin conexion';

                showToast('Modo offline activado', 'warning');
            },

            onOnline: () => {
                this.isOfflineMode = false;
                document.body.classList.remove('offline-mode');
                banner.classList.remove('visible');

                showToast('Conexion restaurada', 'success');
            },

            onSyncStart: () => {
                syncButton.className = 'sync-button syncing';
                syncButton.querySelector('i').className = 'fas fa-sync-alt';
                syncButtonText.textContent = 'Sincronizando...';
            },

            onSyncComplete: (data) => {
                syncButton.className = 'sync-button synced';
                syncButton.querySelector('i').className = 'fas fa-check';
                syncButtonText.textContent = `Sincronizado ${this.offlineManager.getLastSyncTimeFormatted()}`;

                // Update map with fresh data if online
                if (!this.isOfflineMode && data) {
                    this.data = data;
                    this.render();
                }
            },

            onSyncError: (error) => {
                syncButton.className = 'sync-button stale';
                syncButton.querySelector('i').className = 'fas fa-download';
                syncButtonText.textContent = 'Descargar Dia';
            }
        });

        // Manual sync button click
        syncButton.addEventListener('click', async () => {
            if (this.offlineManager.isOnline() && !syncButton.classList.contains('syncing')) {
                await this.offlineManager.sync();
            } else if (!this.offlineManager.isOnline()) {
                showToast('Funcion no disponible en modo offline', 'warning');
            }
        });

        // Initialize with current date
        await this.offlineManager.init(this.currentDate);

        // Update sync button initial state
        if (this.offlineManager.getLastSyncTime()) {
            syncButton.className = 'sync-button synced';
            syncButtonText.textContent = `Sincronizado ${this.offlineManager.getLastSyncTimeFormatted()}`;
        } else {
            syncButton.className = 'sync-button stale';
            syncButton.querySelector('i').className = 'fas fa-download';
            syncButtonText.textContent = 'Descargar Dia';
        }
    }

    createSVG() {
        const result = createSVG(this.container, this.colors);
        this.svg = result.svg;
        this.zonesLayer = result.zonesLayer;
        this.decorativeLayer = result.decorativeLayer;
        this.furnitureLayer = result.furnitureLayer;
        this.selectionLayer = result.selectionLayer;
    }

    setupEventListeners() {
        // Keyboard navigation
        this.navigation.setupKeyboard({
            onEscape: () => this.clearSelection(),
            onPrevDay: () => this.goToPreviousDay(),
            onNextDay: () => this.goToNextDay(),
            onZoom: () => this.applyZoom()
        });

        // SVG click for deselection
        this.svg.addEventListener('click', (e) => {
            if (e.target === this.svg || e.target.closest('#zones-layer')) {
                this.clearSelection();
            }
        });

        // SVG right-click for empty space context menu
        this.svg.addEventListener('contextmenu', (e) => {
            // Only handle if click is on empty space (not furniture)
            const furnitureGroup = e.target.closest('.furniture-item');
            if (!furnitureGroup) {
                // Convert screen coordinates to SVG coordinates
                const svgPoint = this.screenToSVGCoordinates(e.clientX, e.clientY);
                const zone = this.getZoneAtPosition(svgPoint.x, svgPoint.y);
                this.contextMenu.showEmptySpaceMenu(e, svgPoint.x, svgPoint.y, zone);
            }
        });

        // Temporary furniture drag handling (always enabled)
        this.svg.addEventListener('mousedown', this.handleTempFurnitureMouseDown);
        document.addEventListener('mousemove', this.handleTempFurnitureMouseMove);
        document.addEventListener('mouseup', this.handleTempFurnitureMouseUp);
    }

    /**
     * Convert screen coordinates to SVG coordinates
     * @param {number} clientX - Screen X coordinate
     * @param {number} clientY - Screen Y coordinate
     * @returns {Object} SVG coordinates {x, y}
     */
    screenToSVGCoordinates(clientX, clientY) {
        const pt = this.svg.createSVGPoint();
        pt.x = clientX;
        pt.y = clientY;
        const svgPoint = pt.matrixTransform(this.svg.getScreenCTM().inverse());
        return { x: svgPoint.x, y: svgPoint.y };
    }

    /**
     * Get zone at SVG coordinates
     * @param {number} x - SVG X coordinate
     * @param {number} y - SVG Y coordinate
     * @returns {Object|null} Zone data or null
     */
    getZoneAtPosition(x, y) {
        if (!this.data?.zone_bounds) return null;

        for (const zone of (this.data.zones || [])) {
            const bounds = this.data.zone_bounds[zone.id];
            if (bounds &&
                x >= bounds.x && x <= bounds.x + bounds.width &&
                y >= bounds.y && y <= bounds.y + bounds.height) {
                return zone;
            }
        }
        return null;
    }

    async loadData() {
        try {
            const response = await fetch(`${this.options.apiUrl}?date=${this.currentDate}`);
            if (!response.ok) throw new Error('Error loading map data');

            const result = await response.json();

            if (result.success) {
                this.data = result;

                // Apply map config
                if (result.map_config) {
                    this.options.autoRefreshInterval = result.map_config.auto_refresh_ms || this.options.autoRefreshInterval;
                    this.options.minZoom = result.map_config.min_zoom || this.options.minZoom;
                    this.options.maxZoom = result.map_config.max_zoom || this.options.maxZoom;
                    this.options.snapToGrid = result.map_config.snap_grid || this.options.snapToGrid;

                    // Update managers with new config
                    this.navigation.updateOptions({
                        minZoom: this.options.minZoom,
                        maxZoom: this.options.maxZoom
                    });
                    this.interaction.updateOptions({
                        snapToGrid: this.options.snapToGrid
                    });
                }
            }

            return true;
        } catch (error) {
            console.warn('Failed to load from server, trying cache:', error);

            // Try to load from cache when offline
            if (this.offlineManager) {
                const cachedData = await this.offlineManager.loadCachedData();
                if (cachedData) {
                    this.data = cachedData;
                    showToast('Mostrando datos en cache', 'info');
                    return true;
                }
            }

            console.error('No cached data available');
            showToast('Error al cargar datos del mapa', 'error');
            return false;
        }
    }

    render() {
        if (!this.data) return;

        const { width, height } = this.data.map_dimensions;
        this.svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        renderZones(this.zonesLayer, this.data, this.colors);
        renderDecorativeItems(this.decorativeLayer, this.data, this.colors, this.svg);
        renderFurniture(
            this.furnitureLayer,
            this.data,
            this.selection.getSelectedSet(),
            this.colors,
            this.handleFurnitureClick,
            this.tooltipManager,
            this.handleFurnitureContextMenu
        );
        updateLegend(this.data, this.colors);

        // Apply zoom
        this.applyZoom();

        // Notify render complete
        if (this.callbacks.onRender) {
            this.callbacks.onRender(this.data);
        }
    }

    // =========================================================================
    // SELECTION
    // =========================================================================

    handleFurnitureClick(event, item) {
        event.stopPropagation();

        // Suppress click if it was actually end of a drag
        if (this._suppressNextClick) {
            this._suppressNextClick = false;
            return;
        }

        // Check if furniture is blocked - prevent selection for new reservations
        if (this.data?.blocks && this.data.blocks[item.id]) {
            const blockInfo = this.data.blocks[item.id];
            const blockTypeNames = {
                'maintenance': 'mantenimiento',
                'vip_hold': 'reserva VIP',
                'event': 'evento',
                'other': 'bloqueo'
            };
            const typeName = blockTypeNames[blockInfo.block_type] || 'bloqueo';
            showToast(`Este mobiliario está bloqueado por ${typeName}`, 'warning');
            return; // Do not allow selection
        }

        // Always multi-select on tap (mobile-first)
        this.selection.select(item.id, true);
        this.render();
        this.selection.updatePanel(this.data);

        if (this.callbacks.onFurnitureClick) {
            this.callbacks.onFurnitureClick(item, this.getSelectedFurniture());
        }
    }

    handleFurnitureContextMenu(event, item) {
        this.contextMenu.show(event, item);
    }

    selectFurniture(id, addToSelection = false) {
        this.selection.select(id, addToSelection);
        this.render();
        this.selection.updatePanel(this.data);
    }

    deselectFurniture(id) {
        this.selection.deselect(id);
        this.render();
        this.selection.updatePanel(this.data);
    }

    clearSelection() {
        this.selection.clear();
        this.render();
        this.selection.updatePanel(this.data);
    }

    getSelectedFurniture() {
        return this.selection.getSelected();
    }

    isSelected(id) {
        return this.selection.isSelected(id);
    }

    getSelectedFurnitureData() {
        return this.selection.getSelectedData(this.data);
    }

    updateSelectionPanel() {
        this.selection.updatePanel(this.data);
    }

    // =========================================================================
    // DATE NAVIGATION
    // =========================================================================

    async goToDate(dateStr) {
        this.currentDate = dateStr;

        // Update offline manager date
        if (this.offlineManager) {
            await this.offlineManager.setDate(dateStr);
        }

        await this.loadData();
        this.render();

        if (this.callbacks.onDateChange) {
            this.callbacks.onDateChange(dateStr);
        }
    }

    async goToPreviousDay() {
        const date = new Date(this.currentDate);
        date.setDate(date.getDate() - 1);
        await this.goToDate(date.toISOString().split('T')[0]);
    }

    async goToNextDay() {
        const date = new Date(this.currentDate);
        date.setDate(date.getDate() + 1);
        await this.goToDate(date.toISOString().split('T')[0]);
    }

    formatDateDisplay(dateStr) {
        return formatDateDisplay(dateStr);
    }

    // =========================================================================
    // ZOOM & PAN
    // =========================================================================

    zoomIn(factor = 0.25) {
        this.navigation.zoomIn(factor);
    }

    zoomOut(factor = 0.25) {
        this.navigation.zoomOut(factor);
    }

    zoomReset() {
        this.navigation.zoomReset();
        this.applyZoom();
    }

    setZoom(level) {
        this.navigation.setZoom(level);
        // Keep interaction manager zoom in sync
        this.interaction.setZoom(this.navigation.getZoom());
    }

    getZoom() {
        return this.navigation.getZoom();
    }

    applyZoom() {
        this.navigation.applyZoom(this.svg, this.data);
        // Keep interaction manager zoom in sync
        this.interaction.setZoom(this.navigation.getZoom());
    }

    // =========================================================================
    // AUTO-REFRESH
    // =========================================================================

    startAutoRefresh(intervalMs = null) {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
        }

        const interval = intervalMs || this.options.autoRefreshInterval;
        this.autoRefreshTimer = setInterval(() => {
            this.refreshAvailability();
        }, interval);
    }

    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
            this.autoRefreshTimer = null;
        }
    }

    async refreshAvailability() {
        // Skip refresh if temp furniture drag is in progress
        if (this.interaction.isDraggingTemp) {
            return;
        }

        try {
            await this.loadData();
        } catch (error) {
            console.error('Auto-refresh error:', error);
        }
    }

    // =========================================================================
    // EDIT MODE
    // =========================================================================

    enableEditMode() {
        this.interaction.enableEditMode(this.container, this.furnitureLayer);
    }

    disableEditMode() {
        this.interaction.disableEditMode();
    }

    // =========================================================================
    // TEMPORARY FURNITURE DRAG (always enabled)
    // =========================================================================

    /**
     * Handle mousedown on SVG - check for temp furniture drag
     * @param {MouseEvent} event
     */
    handleTempFurnitureMouseDown(event) {
        // Only left mouse button
        if (event.button !== 0) return;

        // Check if clicking on temp furniture
        const tempFurniture = this.interaction.isTemporaryFurniture(event.target);
        if (!tempFurniture) return;

        // Stop auto-refresh during drag to prevent race conditions
        this.stopAutoRefresh();

        // Start drag tracking
        this.interaction.handleTempDragStart(event, tempFurniture);
    }

    /**
     * Handle mousemove for temp furniture drag
     * @param {MouseEvent} event
     */
    handleTempFurnitureMouseMove(event) {
        this.interaction.handleTempDrag(event);
    }

    /**
     * Handle mouseup for temp furniture drag
     * @param {MouseEvent} event
     */
    async handleTempFurnitureMouseUp(event) {
        const wasDrag = await this.interaction.handleTempDragEnd(event);

        // Restart auto-refresh after drag (with delay to let DB commit)
        setTimeout(() => this.startAutoRefresh(), 500);

        // If was a drag, suppress the click event
        if (wasDrag) {
            this._suppressNextClick = true;
        }
    }

    // =========================================================================
    // SEARCH HIGHLIGHT & PAN
    // =========================================================================

    /**
     * Highlight furniture and pan/scroll to center it in view
     * @param {number} furnitureId - ID of furniture to highlight
     */
    highlightAndPanToFurniture(furnitureId) {
        // Find the furniture element
        const furnitureEl = this.furnitureLayer.querySelector(`[data-furniture-id="${furnitureId}"]`);
        if (!furnitureEl) {
            console.warn(`Furniture #${furnitureId} not found on map`);
            return;
        }

        // Clear previous highlights
        this._clearSearchHighlights();

        // Add highlight class (pulsing animation)
        furnitureEl.classList.add('search-highlight');

        // Get furniture position from data
        const furniture = this.data?.furniture?.find(f => f.id === furnitureId);
        if (furniture) {
            this._panToPosition(furniture.position_x, furniture.position_y);
        }

        // Auto-remove highlight after 3 seconds
        setTimeout(() => {
            furnitureEl.classList.remove('search-highlight');
        }, 3000);
    }

    /**
     * Clear all search highlights
     */
    _clearSearchHighlights() {
        this.furnitureLayer.querySelectorAll('.search-highlight').forEach(el => {
            el.classList.remove('search-highlight');
        });
    }

    /**
     * Pan/scroll the map to center on a position
     * @param {number} x - X coordinate in SVG units
     * @param {number} y - Y coordinate in SVG units
     */
    _panToPosition(x, y) {
        const wrapper = this.container.closest('.map-canvas-wrapper');
        if (!wrapper) return;

        const wrapperRect = wrapper.getBoundingClientRect();
        const zoom = this.navigation.getZoom();

        // Calculate scroll position to center the target
        const targetX = (x * zoom) - (wrapperRect.width / 2);
        const targetY = (y * zoom) - (wrapperRect.height / 2);

        wrapper.scrollTo({
            left: Math.max(0, targetX),
            top: Math.max(0, targetY),
            behavior: 'smooth'
        });
    }

    // =========================================================================
    // UTILITIES
    // =========================================================================

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger m-3';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
        this.container.appendChild(errorDiv);
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    on(eventName, callback) {
        if (this.callbacks.hasOwnProperty(eventName)) {
            this.callbacks[eventName] = callback;
        }
        return this;
    }

    getCurrentDate() {
        return this.currentDate;
    }

    getData() {
        return this.data;
    }

    destroy() {
        this.stopAutoRefresh();
        this.navigation.removeKeyboard();
        this.interaction.destroy();
        this.tooltipManager.destroy();
        this.contextMenu.destroy();

        // Remove temp furniture drag listeners
        this.svg?.removeEventListener('mousedown', this.handleTempFurnitureMouseDown);
        document.removeEventListener('mousemove', this.handleTempFurnitureMouseMove);
        document.removeEventListener('mouseup', this.handleTempFurnitureMouseUp);
    }
}

// Export for use as module and global
export default BeachMap;
