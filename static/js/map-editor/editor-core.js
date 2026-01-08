/**
 * Map Editor - Core Module
 * Main coordinator class with constructor, event system, zone loading, and keyboard shortcuts
 */

/**
 * Base class for MapEditor with core functionality
 */
export class MapEditorBase {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container #${containerId} not found`);
        }

        // Configuration
        this.options = {
            paletteId: 'palette',
            propertiesPanelId: 'properties-panel',
            apiBaseUrl: '/beach/config/map-editor',
            snapToGrid: 25,
            minZoom: 0.25,
            maxZoom: 3,
            showRulers: true,
            rulerSize: 30,
            ...options
        };

        // State
        this.currentZoneId = null;
        this.canvasConfig = { width: 2000, height: 1000, backgroundColor: '#FAFAFA' };
        this.furniture = [];
        this.furnitureTypes = {};
        this.selectedItems = new Set();  // Multi-selection support
        this.zoom = 1;
        this.showGrid = false;
        this.showCenterGuides = true;  // Show center guides by default
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.spaceDown = false;  // For pan mode

        // Marquee selection state
        this.isMarqueeSelecting = false;
        this.marqueeStart = { x: 0, y: 0 };
        this.marqueeRect = null;
        this.selectionLayer = null;

        // DOM elements
        this.svg = null;
        this.furnitureLayer = null;
        this.gridLayer = null;
        this.centerGuidesLayer = null;
        this.palette = document.getElementById(this.options.paletteId);
        this.propertiesPanel = document.getElementById(this.options.propertiesPanelId);
        this.viewport = document.getElementById('canvas-viewport');
        this.rulerH = document.getElementById('ruler-horizontal');
        this.rulerV = document.getElementById('ruler-vertical');

        // Event callbacks
        this.callbacks = {
            furnitureChanged: null,
            selectionChanged: null,
            multiSelectionChanged: null,
            canvasLoaded: null,
            zoomChanged: null,
            cursorMove: null,
            itemMoved: null
        };

        // Initialize (these methods come from mixins)
        this.setupPaletteDragDrop();
        this.setupKeyboardShortcuts();
        this.setupViewportTracking();
        this.setupWheelZoom();
        this.setupMarqueeSelection();
        this.loadSavedView();
    }

    // =============================================================================
    // EVENT SYSTEM
    // =============================================================================

    /**
     * Register event callback
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (event in this.callbacks) {
            this.callbacks[event] = callback;
        }
    }

    /**
     * Emit event to registered callback
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    emit(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event](data);
        }
    }

    // =============================================================================
    // ZONE LOADING
    // =============================================================================

    /**
     * Load a zone's furniture layout
     * @param {number} zoneId - Zone ID to load
     * @param {Object} config - Optional config overrides (width, height, backgroundColor)
     */
    async loadZone(zoneId, config = {}) {
        this.currentZoneId = zoneId;

        // If config has dimensions, use them (priority over API)
        const hasConfigDimensions = config.width && config.height;

        const loading = document.getElementById('canvas-loading');
        if (loading) loading.classList.remove('d-none');

        try {
            const response = await fetch(`${this.options.apiBaseUrl}/zone/${zoneId}`);
            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error loading zone');
            }

            this.furniture = result.zone.furniture || [];
            this.furnitureTypes = result.furniture_types || {};

            // Use passed config dimensions if provided, otherwise use API values
            if (hasConfigDimensions) {
                this.canvasConfig.width = config.width;
                this.canvasConfig.height = config.height;
                this.canvasConfig.backgroundColor = config.backgroundColor || result.zone.background_color || '#FAFAFA';
            } else {
                this.canvasConfig.width = result.zone.canvas_width || 2000;
                this.canvasConfig.height = result.zone.canvas_height || 1000;
                this.canvasConfig.backgroundColor = result.zone.background_color || '#FAFAFA';
            }

            this.createCanvas();
            this.renderFurniture();
            this.createRulers();
            this.centerViewport();

            this.emit('canvasLoaded', this.canvasConfig);
            this.emit('furnitureChanged', this.furniture.length);
            this.emit('zoomChanged', this.zoom);

        } catch (error) {
            console.error('Error loading zone:', error);
            if (window.PuroBeach) window.PuroBeach.showToast('Error cargando zona', 'error');
        } finally {
            if (loading) loading.classList.add('d-none');
        }
    }

    // =============================================================================
    // KEYBOARD SHORTCUTS
    // =============================================================================

    /**
     * Setup keyboard shortcuts for the editor
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (!this.container.contains(document.activeElement) && document.activeElement.tagName !== 'BODY') return;

            const hasSelection = this.selectedItems.size > 0;
            const isInputFocused = document.activeElement.tagName === 'INPUT' ||
                                   document.activeElement.tagName === 'TEXTAREA';

            switch (e.key) {
                case 'Escape':
                    this.deselectAll();
                    break;

                case 'Delete':
                case 'Backspace':
                    if (hasSelection && !isInputFocused) {
                        e.preventDefault();
                        this.deleteSelectedItems();
                    }
                    break;

                case 'a':
                case 'A':
                    // Ctrl+A to select all
                    if ((e.ctrlKey || e.metaKey) && !isInputFocused) {
                        e.preventDefault();
                        this.selectAll();
                    }
                    break;

                case 'ArrowUp':
                    if (hasSelection && !isInputFocused) {
                        e.preventDefault();
                        const stepY = e.shiftKey ? this.options.snapToGrid * 4 : this.options.snapToGrid;
                        this.moveSelectedItems(0, -stepY);
                    }
                    break;

                case 'ArrowDown':
                    if (hasSelection && !isInputFocused) {
                        e.preventDefault();
                        const stepY = e.shiftKey ? this.options.snapToGrid * 4 : this.options.snapToGrid;
                        this.moveSelectedItems(0, stepY);
                    }
                    break;

                case 'ArrowLeft':
                    if (hasSelection && !isInputFocused) {
                        e.preventDefault();
                        const stepX = e.shiftKey ? this.options.snapToGrid * 4 : this.options.snapToGrid;
                        this.moveSelectedItems(-stepX, 0);
                    }
                    break;

                case 'ArrowRight':
                    if (hasSelection && !isInputFocused) {
                        e.preventDefault();
                        const stepX = e.shiftKey ? this.options.snapToGrid * 4 : this.options.snapToGrid;
                        this.moveSelectedItems(stepX, 0);
                    }
                    break;

                case '+':
                case '=':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.zoomIn();
                    }
                    break;

                case '-':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.zoomOut();
                    }
                    break;

                case '0':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.zoomReset();
                    }
                    break;

                case 'g':
                case 'G':
                    if (!e.ctrlKey && !e.metaKey && !isInputFocused) {
                        e.preventDefault();
                        this.toggleGrid();
                        document.getElementById('btn-toggle-grid')?.classList.toggle('active');
                    }
                    break;

                case 'c':
                case 'C':
                    if (!e.ctrlKey && !e.metaKey && !isInputFocused) {
                        e.preventDefault();
                        this.toggleCenterGuides();
                        document.getElementById('btn-toggle-center')?.classList.toggle('active');
                    }
                    break;
            }
        });
    }
}
