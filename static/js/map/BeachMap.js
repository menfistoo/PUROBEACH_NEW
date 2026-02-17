/**
 * Beach Map Interactive Controller
 * Main class that coordinates all map modules
 */

import { loadCSSVariables, formatDateDisplay, showToast, escapeHtml } from './utils.js';
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

        // Highlighted furniture (reservation panel)
        this.highlightedFurniture = new Set();

        // Hovered reservation furniture (hover on map)
        this.hoveredReservationFurniture = new Set();

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

        // Initialize Modal State Manager
        if (window.modalStateManager) {
            window.modalStateManager.initialize({
                interactionManager: this.interaction,
                selectionManager: this.selection
            });
            console.log('[BeachMap] Modal State Manager initialized');
        }

        // Offline manager
        this.offlineManager = null;
        this.isOfflineMode = false;

        // Context menu manager (initialized after container is ready)
        this.contextMenu = new ContextMenuManager({
            container: this.container,
            getData: () => ({ ...this.data, beachMap: this }),
            onBlock: (furnitureIds, furnitureNumbers) => {
                if (this.callbacks.onBlockRequest) {
                    // Context menu now passes arrays directly
                    this.callbacks.onBlockRequest(furnitureIds, furnitureNumbers);
                }
            },
            onUnblock: (furnitureIds, furnitureNumbers) => {
                if (this.callbacks.onUnblockRequest) {
                    // Context menu now passes arrays directly
                    this.callbacks.onUnblockRequest(furnitureIds, furnitureNumbers);
                }
            },
            onAddTemporary: (x, y, zoneId) => {
                if (this.callbacks.onAddTemporaryRequest) {
                    this.callbacks.onAddTemporaryRequest(x, y, zoneId);
                }
            },
            onDeleteTemporary: (furnitureIds, furnitureNumbers) => {
                if (this.callbacks.onDeleteTemporaryRequest) {
                    // Context menu now passes arrays directly
                    this.callbacks.onDeleteTemporaryRequest(furnitureIds, furnitureNumbers);
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
        // Touch handlers for mobile temp furniture drag
        this.handleTempFurnitureTouchStart = this.handleTempFurnitureTouchStart.bind(this);
        this.handleTempFurnitureTouchMove = this.handleTempFurnitureTouchMove.bind(this);
        this.handleTempFurnitureTouchEnd = this.handleTempFurnitureTouchEnd.bind(this);

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

        // Touch handlers for mobile temp furniture drag
        this.svg.addEventListener('touchstart', this.handleTempFurnitureTouchStart, { passive: false });
        document.addEventListener('touchmove', this.handleTempFurnitureTouchMove, { passive: false });
        document.addEventListener('touchend', this.handleTempFurnitureTouchEnd, { passive: false });
        document.addEventListener('touchcancel', this.handleTempFurnitureTouchEnd, { passive: false });
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

        // Preserve scroll position before re-rendering
        const wrapper = this.container.closest('.map-canvas-wrapper');
        const scrollLeft = wrapper?.scrollLeft || 0;
        const scrollTop = wrapper?.scrollTop || 0;

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
            this.handleFurnitureContextMenu,
            this.highlightedFurniture,
            this.hoveredReservationFurniture
        );
        updateLegend(this.data, this.colors);

        // Apply zoom
        this.applyZoom();

        // Restore scroll position after browser processes DOM changes
        if (wrapper) {
            requestAnimationFrame(() => {
                wrapper.scrollLeft = scrollLeft;
                wrapper.scrollTop = scrollTop;
            });
        }

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
        this.updateFurnitureSelectionVisuals();
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
        this.updateFurnitureSelectionVisuals();
        this.selection.updatePanel(this.data);
    }

    deselectFurniture(id) {
        this.selection.deselect(id);
        this.updateFurnitureSelectionVisuals();
        this.selection.updatePanel(this.data);
    }

    clearSelection() {
        this.selection.clear();
        this.updateFurnitureSelectionVisuals();
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

    /**
     * Update furniture selection visuals without full re-render
     * This preserves scroll position by only updating CSS classes/styles
     */
    updateFurnitureSelectionVisuals() {
        const selectedSet = this.selection.getSelectedSet();
        const furnitureGroups = this.furnitureLayer.querySelectorAll('g[data-furniture-id]');

        furnitureGroups.forEach(group => {
            const id = parseInt(group.getAttribute('data-furniture-id'));
            const rect = group.querySelector('rect');
            if (!rect) return;

            const isSelected = selectedSet.has(id);

            // Get furniture data to determine base colors
            const item = this.data?.furniture?.find(f => f.id === id);
            if (!item) return;

            // Determine availability status
            const availStatus = this.data?.availability?.[id];
            const blockInfo = this.data?.blocks?.[id];

            if (isSelected) {
                // Apply selection styling
                rect.setAttribute('fill', this.colors.selectedFill);
                rect.setAttribute('stroke', this.colors.selectedStroke);
                group.setAttribute('filter', 'url(#selected-glow)');
            } else {
                // Remove selection styling, restore base colors
                group.removeAttribute('filter');

                if (blockInfo) {
                    // Blocked furniture - use color from block data or default gray
                    const blockFill = blockInfo.color || '#9CA3AF';
                    rect.setAttribute('fill', blockFill);
                    rect.setAttribute('stroke', this.darkenColor(blockFill, 30));
                } else if (availStatus && !availStatus.available) {
                    // Occupied furniture - use state colors from data
                    const state = availStatus.state;
                    const stateColor = state && this.data?.state_colors?.[state];
                    if (stateColor) {
                        rect.setAttribute('fill', stateColor);
                        rect.setAttribute('stroke', this.darkenColor(stateColor, 30));
                    } else {
                        // Fallback if no state color defined
                        const typeConfig = this.data?.furniture_types?.[item.furniture_type] || {};
                        rect.setAttribute('fill', typeConfig.fill_color || '#A0522D');
                        rect.setAttribute('stroke', typeConfig.stroke_color || '#654321');
                    }
                } else {
                    // Available furniture - check if temporary
                    if (item.is_temporary) {
                        rect.setAttribute('fill', '#E0F2FE');
                        rect.setAttribute('stroke', '#0EA5E9');
                    } else {
                        rect.setAttribute('fill', this.colors.availableFill);
                        rect.setAttribute('stroke', this.colors.availableStroke);
                    }
                }
            }
        });
    }

    /**
     * Darken a hex color by a percentage
     * @param {string} color - Hex color string
     * @param {number} percent - Percentage to darken (0-100)
     * @returns {string} Darkened hex color
     */
    darkenColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.max(0, (num >> 16) - amt);
        const G = Math.max(0, ((num >> 8) & 0x00FF) - amt);
        const B = Math.max(0, (num & 0x0000FF) - amt);
        return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
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
            this.render();
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
    // TOUCH HANDLERS FOR MOBILE TEMP FURNITURE DRAG
    // =========================================================================

    /**
     * Handle touchstart for temp furniture drag on mobile
     * @param {TouchEvent} event
     */
    handleTempFurnitureTouchStart(event) {
        // Only handle single touch
        if (event.touches.length !== 1) return;

        // Check if touching temp furniture
        const tempFurniture = this.interaction.isTemporaryFurniture(event.target);
        if (!tempFurniture) return;

        // Store touch info for drag detection
        this._tempTouchStartTime = Date.now();
        this._tempTouchStartX = event.touches[0].clientX;
        this._tempTouchStartY = event.touches[0].clientY;
        this._tempTouchTarget = tempFurniture;
        this._tempTouchDragStarted = false;

        // Stop auto-refresh during potential drag
        this.stopAutoRefresh();
    }

    /**
     * Handle touchmove for temp furniture drag on mobile
     * @param {TouchEvent} event
     */
    handleTempFurnitureTouchMove(event) {
        if (!this._tempTouchTarget || event.touches.length !== 1) return;

        const touch = event.touches[0];
        const deltaX = Math.abs(touch.clientX - this._tempTouchStartX);
        const deltaY = Math.abs(touch.clientY - this._tempTouchStartY);
        const moveThreshold = 10;

        // Start drag if moved enough (before long-press triggers)
        if (!this._tempTouchDragStarted && (deltaX > moveThreshold || deltaY > moveThreshold)) {
            // Only start drag if within first 400ms (before long-press at 500ms)
            const elapsed = Date.now() - this._tempTouchStartTime;
            if (elapsed < 400) {
                this._tempTouchDragStarted = true;

                // Create synthetic mousedown event to start drag
                const syntheticEvent = {
                    button: 0,
                    clientX: this._tempTouchStartX,
                    clientY: this._tempTouchStartY,
                    target: this._tempTouchTarget.element,
                    preventDefault: () => {}
                };
                this.interaction.handleTempDragStart(syntheticEvent, this._tempTouchTarget);

                // Haptic feedback
                if (navigator.vibrate) {
                    navigator.vibrate(30);
                }
            }
        }

        // If drag started, continue dragging
        if (this._tempTouchDragStarted) {
            event.preventDefault(); // Prevent scroll while dragging

            const syntheticEvent = {
                clientX: touch.clientX,
                clientY: touch.clientY
            };
            this.interaction.handleTempDrag(syntheticEvent);
        }
    }

    /**
     * Handle touchend/touchcancel for temp furniture drag on mobile
     * @param {TouchEvent} event
     */
    async handleTempFurnitureTouchEnd(event) {
        if (!this._tempTouchTarget) return;

        if (this._tempTouchDragStarted) {
            // End the drag
            const touch = event.changedTouches?.[0];
            const syntheticEvent = {
                clientX: touch?.clientX || this._tempTouchStartX,
                clientY: touch?.clientY || this._tempTouchStartY
            };

            const wasDrag = await this.interaction.handleTempDragEnd(syntheticEvent);

            if (wasDrag) {
                this._suppressNextClick = true;
            }
        }

        // Restart auto-refresh after drag
        setTimeout(() => this.startAutoRefresh(), 500);

        // Reset touch state
        this._tempTouchTarget = null;
        this._tempTouchDragStarted = false;
        this._tempTouchStartTime = 0;
        this._tempTouchStartX = 0;
        this._tempTouchStartY = 0;
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
    // MOVE MODE PREFERENCE HIGHLIGHTS
    // =========================================================================

    /**
     * Highlight furniture items that match customer preferences (for move mode)
     * Supports tiered highlighting: full match vs partial match
     * @param {Array} fullMatchIds - Furniture IDs with 100% preference match
     * @param {Array} partialMatchIds - Furniture IDs with partial match (>0% but <100%)
     */
    applyPreferenceHighlights(fullMatchIds = [], partialMatchIds = []) {
        // Clear previous preference highlights
        this.clearPreferenceHighlights();

        // Add full match highlight (strong green glow)
        fullMatchIds.forEach(id => {
            const furnitureEl = this.furnitureLayer.querySelector(`[data-furniture-id="${id}"]`);
            if (furnitureEl) {
                furnitureEl.classList.add('preference-match-full');
            }
        });

        // Add partial match highlight (lighter highlight)
        partialMatchIds.forEach(id => {
            const furnitureEl = this.furnitureLayer.querySelector(`[data-furniture-id="${id}"]`);
            if (furnitureEl) {
                furnitureEl.classList.add('preference-match-partial');
            }
        });
    }

    /**
     * Clear all preference match highlights
     */
    clearPreferenceHighlights() {
        this.furnitureLayer.querySelectorAll('.preference-match-full').forEach(el => {
            el.classList.remove('preference-match-full');
        });
        this.furnitureLayer.querySelectorAll('.preference-match-partial').forEach(el => {
            el.classList.remove('preference-match-partial');
        });
    }

    /**
     * Set furniture IDs to highlight for a reservation (survives re-renders)
     * @param {number[]} ids - Furniture IDs to highlight
     */
    setHighlightedFurniture(ids) {
        this.highlightedFurniture = new Set(ids);
        this.render();
    }

    /**
     * Clear reservation furniture highlights
     */
    clearHighlightedFurniture() {
        if (this.highlightedFurniture.size === 0) return;
        this.highlightedFurniture = new Set();
        this.render();
    }

    // =========================================================================
    // UTILITIES
    // =========================================================================

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger m-3';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${escapeHtml(message)}`;
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

        // Remove touch listeners
        this.svg?.removeEventListener('touchstart', this.handleTempFurnitureTouchStart);
        document.removeEventListener('touchmove', this.handleTempFurnitureTouchMove);
        document.removeEventListener('touchend', this.handleTempFurnitureTouchEnd);
        document.removeEventListener('touchcancel', this.handleTempFurnitureTouchEnd);
    }
}

// Export for use as module and global
export default BeachMap;
