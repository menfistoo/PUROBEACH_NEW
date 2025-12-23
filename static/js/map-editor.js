/**
 * Beach Map Editor Controller
 * Architectural-style visual editor for designing beach map layout
 */

class MapEditor {
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
        this.selectedItem = null;
        this.zoom = 1;
        this.showGrid = false;
        this.showCenterGuides = true;  // Show center guides by default
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.spaceDown = false;  // For pan mode

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
            canvasLoaded: null,
            zoomChanged: null,
            cursorMove: null,
            itemMoved: null
        };

        // Initialize
        this.setupPaletteDragDrop();
        this.setupKeyboardShortcuts();
        this.setupViewportTracking();
        this.setupWheelZoom();
        this.loadSavedView();
    }

    // =============================================================================
    // WHEEL ZOOM
    // =============================================================================

    setupWheelZoom() {
        if (!this.viewport) return;

        this.viewport.addEventListener('wheel', (e) => {
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();

                // Get mouse position relative to viewport
                const rect = this.viewport.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;

                // Get canvas position under mouse before zoom
                const canvasX = (this.viewport.scrollLeft + mouseX) / this.zoom;
                const canvasY = (this.viewport.scrollTop + mouseY) / this.zoom;

                // Apply zoom
                const delta = e.deltaY > 0 ? -0.1 : 0.1;
                const oldZoom = this.zoom;
                this.zoom = Math.max(this.options.minZoom, Math.min(this.zoom + delta, this.options.maxZoom));

                // Only update if zoom actually changed
                if (this.zoom !== oldZoom) {
                    this.applyZoom();

                    // Adjust scroll to keep the same canvas position under mouse
                    this.viewport.scrollLeft = canvasX * this.zoom - mouseX;
                    this.viewport.scrollTop = canvasY * this.zoom - mouseY;

                    this.emit('zoomChanged', this.zoom);
                }
            }
        }, { passive: false });

        // Pan with space + drag or middle mouse button
        let isPanning = false;
        let panStart = { x: 0, y: 0 };
        let scrollStart = { x: 0, y: 0 };

        // Track space key state
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !this.spaceDown && document.activeElement.tagName !== 'INPUT') {
                e.preventDefault(); // Prevent page scroll
                this.spaceDown = true;
                this.viewport.style.cursor = 'grab';
            }
        });

        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space') {
                this.spaceDown = false;
                if (!isPanning) {
                    this.viewport.style.cursor = '';
                }
            }
        });

        this.viewport.addEventListener('mousedown', (e) => {
            // Middle mouse button or space + left click
            if (e.button === 1 || (e.button === 0 && this.spaceDown)) {
                e.preventDefault();
                isPanning = true;
                panStart = { x: e.clientX, y: e.clientY };
                scrollStart = { x: this.viewport.scrollLeft, y: this.viewport.scrollTop };
                this.viewport.style.cursor = 'grabbing';
            }
        });

        document.addEventListener('mousemove', (e) => {
            if (!isPanning) return;
            const dx = e.clientX - panStart.x;
            const dy = e.clientY - panStart.y;
            this.viewport.scrollLeft = scrollStart.x - dx;
            this.viewport.scrollTop = scrollStart.y - dy;
        });

        document.addEventListener('mouseup', (e) => {
            if (isPanning) {
                isPanning = false;
                this.viewport.style.cursor = this.spaceDown ? 'grab' : '';
            }
        });

        // Prevent default middle click behavior
        this.viewport.addEventListener('auxclick', (e) => {
            if (e.button === 1) e.preventDefault();
        });
    }

    // =============================================================================
    // SAVED VIEW
    // =============================================================================

    loadSavedView() {
        try {
            const saved = localStorage.getItem('mapEditor_defaultView');
            if (saved) {
                const view = JSON.parse(saved);
                if (view.zoom) this.zoom = view.zoom;
                // Store in memory as fallback
                this._savedView = view;
            }
        } catch (e) {
            console.warn('Could not load saved view (localStorage blocked?):', e);
        }
    }

    saveCurrentView() {
        const view = {
            zoom: this.zoom,
            showGrid: this.showGrid,
            showCenterGuides: this.showCenterGuides,
            snapSize: this.options.snapToGrid
        };

        // Always save in memory
        this._savedView = view;

        try {
            localStorage.setItem('mapEditor_defaultView', JSON.stringify(view));
            return true;
        } catch (e) {
            console.warn('Could not save to localStorage (blocked?), saved in memory only');
            return true;  // Still return true since we saved in memory
        }
    }

    getSavedView() {
        // First try memory, then localStorage
        if (this._savedView) {
            return this._savedView;
        }
        try {
            const saved = localStorage.getItem('mapEditor_defaultView');
            return saved ? JSON.parse(saved) : null;
        } catch (e) {
            return null;
        }
    }

    // =============================================================================
    // EVENT SYSTEM
    // =============================================================================

    on(event, callback) {
        if (event in this.callbacks) {
            this.callbacks[event] = callback;
        }
    }

    emit(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event](data);
        }
    }

    // =============================================================================
    // VIEWPORT & CURSOR TRACKING
    // =============================================================================

    setupViewportTracking() {
        if (!this.viewport) return;

        this.viewport.addEventListener('mousemove', (e) => {
            if (!this.svg) return;
            try {
                const pt = this.getSVGPoint(e);
                // Only emit if point is within canvas bounds
                if (pt.x >= 0 && pt.x <= this.canvasConfig.width &&
                    pt.y >= 0 && pt.y <= this.canvasConfig.height) {
                    this.emit('cursorMove', {
                        x: Math.round(pt.x),
                        y: Math.round(pt.y)
                    });
                } else {
                    this.emit('cursorMove', null);
                }
            } catch (e) {
                // SVG point transform failed
                this.emit('cursorMove', null);
            }
        });

        this.viewport.addEventListener('mouseleave', () => {
            this.emit('cursorMove', null);
        });

        // Sync rulers with scroll
        this.viewport.addEventListener('scroll', () => {
            this.updateRulers();
        });
    }

    // =============================================================================
    // CANVAS MANAGEMENT
    // =============================================================================

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

    /**
     * Resize canvas without reloading furniture
     */
    resizeCanvas(width, height, backgroundColor = null) {
        this.canvasConfig.width = width;
        this.canvasConfig.height = height;
        if (backgroundColor) this.canvasConfig.backgroundColor = backgroundColor;

        this.createCanvas();
        this.renderFurniture();
        this.createRulers();
        this.createCenterGuides();

        this.emit('canvasLoaded', this.canvasConfig);
    }

    createCanvas() {
        this.container.querySelectorAll('svg').forEach(el => el.remove());

        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('class', 'canvas-svg');
        this.svg.setAttribute('width', this.canvasConfig.width);
        this.svg.setAttribute('height', this.canvasConfig.height);
        this.svg.setAttribute('viewBox', `0 0 ${this.canvasConfig.width} ${this.canvasConfig.height}`);

        // Background
        const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bg.setAttribute('width', '100%');
        bg.setAttribute('height', '100%');
        bg.setAttribute('fill', this.canvasConfig.backgroundColor);
        this.svg.appendChild(bg);

        // Grid layer
        this.gridLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.gridLayer.setAttribute('id', 'grid-layer');
        this.gridLayer.style.display = this.showGrid ? 'block' : 'none';
        this.createGrid();
        this.svg.appendChild(this.gridLayer);

        // Center guides layer
        this.centerGuidesLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.centerGuidesLayer.setAttribute('id', 'center-guides-layer');
        this.centerGuidesLayer.style.display = this.showCenterGuides ? 'block' : 'none';
        this.createCenterGuides();
        this.svg.appendChild(this.centerGuidesLayer);

        // Furniture layer
        this.furnitureLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.furnitureLayer.setAttribute('id', 'furniture-layer');
        this.svg.appendChild(this.furnitureLayer);

        this.container.appendChild(this.svg);
        this.setupCanvasDrop();

        this.svg.addEventListener('click', (e) => {
            if (e.target === this.svg || e.target === bg) {
                this.deselectAll();
            }
        });

        this.applyZoom();
    }

    createGrid() {
        const { width, height } = this.canvasConfig;
        const snap = this.options.snapToGrid;
        const majorStep = snap * 4;

        this.gridLayer.innerHTML = '';

        // Minor grid lines
        for (let x = snap; x < width; x += snap) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x);
            line.setAttribute('y1', 0);
            line.setAttribute('x2', x);
            line.setAttribute('y2', height);
            line.setAttribute('class', x % majorStep === 0 ? 'grid-line-major' : 'grid-line');
            this.gridLayer.appendChild(line);
        }

        for (let y = snap; y < height; y += snap) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', 0);
            line.setAttribute('y1', y);
            line.setAttribute('x2', width);
            line.setAttribute('y2', y);
            line.setAttribute('class', y % majorStep === 0 ? 'grid-line-major' : 'grid-line');
            this.gridLayer.appendChild(line);
        }

        // Grid labels at major intervals
        for (let x = majorStep; x < width; x += majorStep) {
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x + 3);
            text.setAttribute('y', 12);
            text.setAttribute('class', 'grid-text');
            text.textContent = x;
            this.gridLayer.appendChild(text);
        }

        for (let y = majorStep; y < height; y += majorStep) {
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', 3);
            text.setAttribute('y', y - 3);
            text.setAttribute('class', 'grid-text');
            text.textContent = y;
            this.gridLayer.appendChild(text);
        }
    }

    createRulers() {
        if (!this.options.showRulers || !this.rulerH || !this.rulerV) return;

        const { width, height } = this.canvasConfig;
        const snap = this.options.snapToGrid;
        const majorStep = snap * 4;

        // Horizontal ruler
        this.rulerH.innerHTML = '';
        const hSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        hSvg.setAttribute('class', 'ruler-svg');
        hSvg.setAttribute('width', width * this.zoom);
        hSvg.setAttribute('height', 30);

        for (let x = 0; x <= width; x += snap) {
            const isMajor = x % majorStep === 0;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x * this.zoom);
            line.setAttribute('y1', isMajor ? 10 : 20);
            line.setAttribute('x2', x * this.zoom);
            line.setAttribute('y2', 30);
            line.setAttribute('class', isMajor ? 'ruler-line-major' : 'ruler-line');
            hSvg.appendChild(line);

            if (isMajor && x > 0) {
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', x * this.zoom);
                text.setAttribute('y', 9);
                text.setAttribute('class', 'ruler-text');
                text.setAttribute('text-anchor', 'middle');
                text.textContent = x;
                hSvg.appendChild(text);
            }
        }
        this.rulerH.appendChild(hSvg);

        // Vertical ruler
        this.rulerV.innerHTML = '';
        const vSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        vSvg.setAttribute('class', 'ruler-svg');
        vSvg.setAttribute('width', 30);
        vSvg.setAttribute('height', height * this.zoom);

        for (let y = 0; y <= height; y += snap) {
            const isMajor = y % majorStep === 0;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', isMajor ? 10 : 20);
            line.setAttribute('y1', y * this.zoom);
            line.setAttribute('x2', 30);
            line.setAttribute('y2', y * this.zoom);
            line.setAttribute('class', isMajor ? 'ruler-line-major' : 'ruler-line');
            vSvg.appendChild(line);

            if (isMajor && y > 0) {
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', 8);
                text.setAttribute('y', y * this.zoom + 3);
                text.setAttribute('class', 'ruler-text');
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('transform', `rotate(-90, 8, ${y * this.zoom})`);
                text.textContent = y;
                vSvg.appendChild(text);
            }
        }
        this.rulerV.appendChild(vSvg);
    }

    updateRulers() {
        if (!this.viewport || !this.rulerH || !this.rulerV) return;
        const scrollLeft = this.viewport.scrollLeft;
        const scrollTop = this.viewport.scrollTop;

        const hSvg = this.rulerH.querySelector('svg');
        const vSvg = this.rulerV.querySelector('svg');

        if (hSvg) hSvg.style.transform = `translateX(-${scrollLeft}px)`;
        if (vSvg) vSvg.style.transform = `translateY(-${scrollTop}px)`;
    }

    clearCanvas() {
        this.currentZoneId = null;
        this.furniture = [];
        this.selectedItem = null;
        if (this.svg) {
            this.svg.remove();
            this.svg = null;
        }
        if (this.rulerH) this.rulerH.innerHTML = '';
        if (this.rulerV) this.rulerV.innerHTML = '';
        this.emit('furnitureChanged', 0);
        this.emit('selectionChanged', null);
    }

    // =============================================================================
    // FURNITURE RENDERING
    // =============================================================================

    renderFurniture() {
        if (!this.furnitureLayer) return;
        this.furnitureLayer.innerHTML = '';
        this.furniture.forEach(item => {
            const group = this.createFurnitureElement(item);
            this.furnitureLayer.appendChild(group);
        });
    }

    createFurnitureElement(item) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'furniture-item');
        group.setAttribute('data-id', item.id);
        group.setAttribute('transform', `translate(${item.position_x}, ${item.position_y}) rotate(${item.rotation || 0}, ${item.width / 2}, ${item.height / 2})`);

        const type = this.furnitureTypes[item.furniture_type] || {};
        const shape = this.createShape(item, type);
        group.appendChild(shape);

        if (item.number) {
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('class', 'furniture-number');
            text.setAttribute('x', item.width / 2);
            text.setAttribute('y', item.height / 2);
            text.textContent = item.number;
            group.appendChild(text);
        }

        this.setupFurnitureEvents(group, item);
        return group;
    }

    createShape(item, type) {
        const shape = type.map_shape || 'rounded_rect';
        // Custom fill_color takes priority, then type defaults
        const fillColor = item.fill_color || item.type_fill_color || type.fill_color || '#A0522D';
        const strokeColor = item.type_stroke_color || type.stroke_color || '#654321';
        const strokeWidth = type.type_stroke_width || 2;
        const borderRadius = type.type_border_radius || 5;

        let element;

        switch (shape) {
            case 'circle':
            case 'ellipse':
                element = document.createElementNS('http://www.w3.org/2000/svg', 'ellipse');
                element.setAttribute('cx', item.width / 2);
                element.setAttribute('cy', item.height / 2);
                element.setAttribute('rx', item.width / 2);
                element.setAttribute('ry', item.height / 2);
                break;
            default:
                element = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                element.setAttribute('width', item.width);
                element.setAttribute('height', item.height);
                element.setAttribute('rx', borderRadius);
                element.setAttribute('ry', borderRadius);
                break;
        }

        element.setAttribute('fill', fillColor);
        element.setAttribute('stroke', strokeColor);
        element.setAttribute('stroke-width', strokeWidth);

        return element;
    }

    setupFurnitureEvents(group, item) {
        let startX, startY, startPosX, startPosY;

        group.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;

            this.selectItem(item);
            this.isDragging = true;
            group.classList.add('dragging');

            const pt = this.getSVGPoint(e);
            startX = pt.x;
            startY = pt.y;
            startPosX = item.position_x;
            startPosY = item.position_y;

            e.preventDefault();
        });

        const handleMouseMove = (e) => {
            if (!this.isDragging || !this.selectedItem || this.selectedItem.id !== item.id) return;

            const pt = this.getSVGPoint(e);
            let newX = startPosX + (pt.x - startX);
            let newY = startPosY + (pt.y - startY);

            // Snap to grid
            newX = Math.round(newX / this.options.snapToGrid) * this.options.snapToGrid;
            newY = Math.round(newY / this.options.snapToGrid) * this.options.snapToGrid;

            // Bounds check
            newX = Math.max(0, Math.min(newX, this.canvasConfig.width - item.width));
            newY = Math.max(0, Math.min(newY, this.canvasConfig.height - item.height));

            group.setAttribute('transform', `translate(${newX}, ${newY}) rotate(${item.rotation || 0}, ${item.width / 2}, ${item.height / 2})`);

            item.position_x = newX;
            item.position_y = newY;

            this.emit('itemMoved', { x: newX, y: newY });
        };

        const handleMouseUp = async () => {
            if (!this.isDragging) return;

            this.isDragging = false;
            group.classList.remove('dragging');

            if (item.position_x !== startPosX || item.position_y !== startPosY) {
                await this.saveFurniturePosition(item);
            }

            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        group.addEventListener('mousedown', () => {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        });
    }

    getSVGPoint(e) {
        const pt = this.svg.createSVGPoint();
        pt.x = e.clientX;
        pt.y = e.clientY;
        const ctm = this.svg.getScreenCTM();
        if (!ctm) return { x: -1, y: -1 };  // Return invalid point if CTM not available
        return pt.matrixTransform(ctm.inverse());
    }

    // =============================================================================
    // SELECTION
    // =============================================================================

    selectItem(item) {
        this.deselectAll();
        this.selectedItem = item;
        // Attach type info for external access
        this.selectedItem.typeInfo = this.furnitureTypes[item.furniture_type] || {};

        const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
        if (group) group.classList.add('selected');

        this.showProperties(item);
        this.emit('selectionChanged', item);
    }

    deselectAll() {
        this.selectedItem = null;
        this.furnitureLayer?.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
        if (this.propertiesPanel) this.propertiesPanel.classList.remove('active');
        this.emit('selectionChanged', null);
    }

    showProperties(item) {
        if (!this.propertiesPanel) return;

        const type = this.furnitureTypes[item.furniture_type] || {};

        document.getElementById('prop-number').value = item.number || '';
        document.getElementById('prop-x').value = Math.round(item.position_x);
        document.getElementById('prop-y').value = Math.round(item.position_y);
        document.getElementById('prop-rotation').value = item.rotation || 0;
        document.getElementById('prop-capacity').value = item.capacity || 0;

        const capacityGroup = document.getElementById('prop-capacity-group');
        if (capacityGroup) {
            capacityGroup.style.display = type.is_decorative ? 'none' : 'block';
        }

        this.propertiesPanel.classList.add('active');
    }

    async updateSelectedProperty(property, value) {
        if (!this.selectedItem) return;

        // Handle position updates
        if (property === 'position_x' || property === 'position_y') {
            const snapped = Math.round(value / this.options.snapToGrid) * this.options.snapToGrid;
            this.selectedItem[property] = snapped;

            const group = this.furnitureLayer.querySelector(`[data-id="${this.selectedItem.id}"]`);
            if (group) {
                group.setAttribute('transform',
                    `translate(${this.selectedItem.position_x}, ${this.selectedItem.position_y}) rotate(${this.selectedItem.rotation || 0}, ${this.selectedItem.width / 2}, ${this.selectedItem.height / 2})`
                );
            }

            await this.saveFurniturePosition(this.selectedItem);
            return;
        }

        this.selectedItem[property] = value;

        if (property === 'rotation') {
            const group = this.furnitureLayer.querySelector(`[data-id="${this.selectedItem.id}"]`);
            if (group) {
                group.setAttribute('transform',
                    `translate(${this.selectedItem.position_x}, ${this.selectedItem.position_y}) rotate(${value}, ${this.selectedItem.width / 2}, ${this.selectedItem.height / 2})`
                );
            }
            await this.saveFurniturePosition(this.selectedItem);
        } else if (property === 'width' || property === 'height' || property === 'fill_color') {
            // Re-render the shape when size or color changes
            const group = this.furnitureLayer.querySelector(`[data-id="${this.selectedItem.id}"]`);
            if (group) {
                const type = this.furnitureTypes[this.selectedItem.furniture_type] || {};
                const oldShape = group.querySelector('rect, ellipse');
                if (oldShape) {
                    const newShape = this.createShape(this.selectedItem, type);
                    oldShape.replaceWith(newShape);
                }
                // Update number position if size changed
                if (property === 'width' || property === 'height') {
                    const text = group.querySelector('.furniture-number');
                    if (text) {
                        text.setAttribute('x', this.selectedItem.width / 2);
                        text.setAttribute('y', this.selectedItem.height / 2);
                    }
                    // Update transform for center rotation point
                    group.setAttribute('transform',
                        `translate(${this.selectedItem.position_x}, ${this.selectedItem.position_y}) rotate(${this.selectedItem.rotation || 0}, ${this.selectedItem.width / 2}, ${this.selectedItem.height / 2})`
                    );
                }
            }
            await this.saveFurnitureProperty(this.selectedItem.id, property, value);
        } else {
            await this.saveFurnitureProperty(this.selectedItem.id, property, value);
        }
    }

    // =============================================================================
    // PALETTE DRAG & DROP
    // =============================================================================

    setupPaletteDragDrop() {
        if (!this.palette) return;

        const items = this.palette.querySelectorAll('.palette-item');

        items.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                item.classList.add('dragging');
                e.dataTransfer.setData('application/json', JSON.stringify({
                    type: item.dataset.type,
                    name: item.dataset.name,
                    width: parseFloat(item.dataset.width) || 60,
                    height: parseFloat(item.dataset.height) || 40,
                    capacity: parseInt(item.dataset.capacity) || 2,
                    shape: item.dataset.shape || 'rounded_rect',
                    fill: item.dataset.fill || '#A0522D',
                    stroke: item.dataset.stroke || '#654321',
                    decorative: item.dataset.decorative === '1'
                }));
            });

            item.addEventListener('dragend', () => item.classList.remove('dragging'));
        });
    }

    setupCanvasDrop() {
        if (!this.svg) return;

        this.svg.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });

        this.svg.addEventListener('drop', async (e) => {
            e.preventDefault();

            const data = JSON.parse(e.dataTransfer.getData('application/json'));
            if (!data || !data.type) return;

            const pt = this.getSVGPoint(e);

            // Check if drop point is within canvas bounds
            if (pt.x < 0 || pt.y < 0 || pt.x > this.canvasConfig.width || pt.y > this.canvasConfig.height) {
                if (window.PuroBeach) window.PuroBeach.showToast('Soltar dentro del canvas', 'warning');
                return;
            }

            let x = Math.round((pt.x - data.width / 2) / this.options.snapToGrid) * this.options.snapToGrid;
            let y = Math.round((pt.y - data.height / 2) / this.options.snapToGrid) * this.options.snapToGrid;

            // Constrain to canvas bounds
            x = Math.max(0, Math.min(x, this.canvasConfig.width - data.width));
            y = Math.max(0, Math.min(y, this.canvasConfig.height - data.height));

            await this.createFurniture(data, x, y);
        });
    }

    // =============================================================================
    // CRUD OPERATIONS
    // =============================================================================

    async createFurniture(typeData, x, y) {
        try {
            const numResponse = await fetch(`${this.options.apiBaseUrl}/furniture/next-number/${this.currentZoneId}/${typeData.type}`);
            const numResult = await numResponse.json();
            const nextNumber = numResult.success ? numResult.next_number : typeData.type.toUpperCase() + '1';

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

            if (window.PuroBeach) window.PuroBeach.showToast(`${nextNumber} creado`, 'success');

        } catch (error) {
            console.error('Error creating furniture:', error);
            if (window.PuroBeach) window.PuroBeach.showToast('Error al crear elemento', 'error');
        }
    }

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

    async deleteSelected() {
        if (!this.selectedItem) return;

        try {
            const response = await fetch(`${this.options.apiBaseUrl}/furniture/${this.selectedItem.id}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                }
            });

            const result = await response.json();
            if (!result.success) throw new Error(result.error);

            const group = this.furnitureLayer.querySelector(`[data-id="${this.selectedItem.id}"]`);
            if (group) group.remove();

            this.furniture = this.furniture.filter(f => f.id !== this.selectedItem.id);
            this.deselectAll();
            this.emit('furnitureChanged', this.furniture.length);

            if (window.PuroBeach) window.PuroBeach.showToast('Elemento eliminado', 'success');

        } catch (error) {
            console.error('Error deleting furniture:', error);
            if (window.PuroBeach) window.PuroBeach.showToast(error.message || 'Error al eliminar', 'error');
        }
    }

    // =============================================================================
    // ZOOM & GRID
    // =============================================================================

    setSnapSize(size) {
        this.options.snapToGrid = size;
        if (this.gridLayer && this.showGrid) {
            this.createGrid();
        }
        this.createRulers();
    }

    zoomIn() {
        this.zoom = Math.min(this.zoom + 0.25, this.options.maxZoom);
        this.applyZoom();
        this.emit('zoomChanged', this.zoom);
    }

    zoomOut() {
        this.zoom = Math.max(this.zoom - 0.25, this.options.minZoom);
        this.applyZoom();
        this.emit('zoomChanged', this.zoom);
    }

    zoomReset() {
        // Reset to saved view zoom or default to 1
        const savedView = this.getSavedView();
        this.zoom = savedView?.zoom || 1;
        this.applyZoom();
        this.centerViewport();
        this.emit('zoomChanged', this.zoom);
    }

    applyZoom() {
        if (!this.svg) return;
        this.svg.style.width = `${this.canvasConfig.width * this.zoom}px`;
        this.svg.style.height = `${this.canvasConfig.height * this.zoom}px`;
        this.createRulers();
    }

    centerViewport() {
        if (!this.viewport || !this.svg) return;

        // Wait for DOM to update
        requestAnimationFrame(() => {
            const canvasWidth = this.canvasConfig.width * this.zoom;
            const canvasHeight = this.canvasConfig.height * this.zoom;
            const viewportWidth = this.viewport.clientWidth;
            const viewportHeight = this.viewport.clientHeight;

            // Calculate scroll to center the canvas
            const scrollLeft = Math.max(0, (canvasWidth - viewportWidth) / 2 + 20); // +20 for padding
            const scrollTop = Math.max(0, (canvasHeight - viewportHeight) / 2 + 20);

            this.viewport.scrollLeft = scrollLeft;
            this.viewport.scrollTop = scrollTop;
        });
    }

    toggleGrid() {
        this.showGrid = !this.showGrid;
        if (this.gridLayer) {
            this.gridLayer.style.display = this.showGrid ? 'block' : 'none';
        }
    }

    createCenterGuides() {
        if (!this.centerGuidesLayer) return;

        const { width, height } = this.canvasConfig;
        const centerX = width / 2;
        const centerY = height / 2;

        this.centerGuidesLayer.innerHTML = '';

        // Vertical center line
        const vLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        vLine.setAttribute('x1', centerX);
        vLine.setAttribute('y1', 0);
        vLine.setAttribute('x2', centerX);
        vLine.setAttribute('y2', height);
        vLine.setAttribute('class', 'center-guide');
        this.centerGuidesLayer.appendChild(vLine);

        // Horizontal center line
        const hLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        hLine.setAttribute('x1', 0);
        hLine.setAttribute('y1', centerY);
        hLine.setAttribute('x2', width);
        hLine.setAttribute('y2', centerY);
        hLine.setAttribute('class', 'center-guide');
        this.centerGuidesLayer.appendChild(hLine);

        // Center point circle
        const centerPoint = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        centerPoint.setAttribute('cx', centerX);
        centerPoint.setAttribute('cy', centerY);
        centerPoint.setAttribute('r', 6);
        centerPoint.setAttribute('class', 'center-point');
        this.centerGuidesLayer.appendChild(centerPoint);

        // Center coordinates label
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('x', centerX + 10);
        label.setAttribute('y', centerY - 10);
        label.setAttribute('class', 'center-label');
        label.textContent = `(${centerX}, ${centerY})`;
        this.centerGuidesLayer.appendChild(label);
    }

    toggleCenterGuides() {
        this.showCenterGuides = !this.showCenterGuides;
        if (this.centerGuidesLayer) {
            this.centerGuidesLayer.style.display = this.showCenterGuides ? 'block' : 'none';
        }
    }

    // =============================================================================
    // KEYBOARD SHORTCUTS
    // =============================================================================

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (!this.container.contains(document.activeElement) && document.activeElement.tagName !== 'BODY') return;

            switch (e.key) {
                case 'Escape':
                    this.deselectAll();
                    break;
                case 'Delete':
                case 'Backspace':
                    if (this.selectedItem && document.activeElement.tagName !== 'INPUT') {
                        e.preventDefault();
                        if (confirm('¿Eliminar el elemento seleccionado?')) {
                            this.deleteSelected();
                        }
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
                    if (!e.ctrlKey && !e.metaKey && document.activeElement.tagName !== 'INPUT') {
                        e.preventDefault();
                        this.toggleGrid();
                        document.getElementById('btn-toggle-grid')?.classList.toggle('active');
                    }
                    break;
                case 'c':
                case 'C':
                    if (!e.ctrlKey && !e.metaKey && document.activeElement.tagName !== 'INPUT') {
                        e.preventDefault();
                        this.toggleCenterGuides();
                        document.getElementById('btn-toggle-center')?.classList.toggle('active');
                    }
                    break;
            }
        });
    }
}

window.MapEditor = MapEditor;
