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
            snapToGrid: this.options.snapToGrid
        });
        this.tooltipManager = new TooltipManager(this.container, this.colors);

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
            }
        });

        // Event callbacks
        this.callbacks = {
            onSelect: null,
            onDeselect: null,
            onDateChange: null,
            onFurnitureClick: null,
            onBlockRequest: null,
            onUnblockRequest: null,
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

        // Bind methods
        this.handleFurnitureClick = this.handleFurnitureClick.bind(this);
        this.handleFurnitureContextMenu = this.handleFurnitureContextMenu.bind(this);

        // Initialize
        this.init();
    }

    async init() {
        this.createSVG();
        this.setupEventListeners();
        await this.loadData();
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
    }

    async loadData() {
        try {
            const response = await fetch(`${this.options.apiUrl}?date=${this.currentDate}`);
            if (!response.ok) throw new Error('Error loading map data');

            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Error loading data');

            this.data = result;

            // Override options with server config if available
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

            this.render();
        } catch (error) {
            console.error('Map load error:', error);
            if (this.callbacks.onError) {
                this.callbacks.onError(error);
            }
            this.showError('Error cargando datos del mapa');
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
        await this.loadData();
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
    }

    getZoom() {
        return this.navigation.getZoom();
    }

    applyZoom() {
        this.navigation.applyZoom(this.svg, this.data);
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
    }
}

// Export for use as module and global
export default BeachMap;
