/**
 * Map Editor - Canvas Module
 * Handles SVG canvas creation, grid, rulers, and center guides
 */

/**
 * Mixin that adds canvas management to MapEditor
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with canvas methods
 */
export const CanvasMixin = (Base) => class extends Base {

    // =============================================================================
    // CANVAS CREATION
    // =============================================================================

    /**
     * Create the main SVG canvas
     */
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

        // Selection layer (for marquee rectangle)
        this.selectionLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.selectionLayer.setAttribute('id', 'selection-layer');
        this.svg.appendChild(this.selectionLayer);

        this.container.appendChild(this.svg);
        this.setupCanvasDrop();

        // Click on background deselects all
        this.svg.addEventListener('click', (e) => {
            // Don't deselect if we just finished a marquee selection
            if (this.justFinishedMarquee) {
                this.justFinishedMarquee = false;
                return;
            }
            if (e.target === this.svg || e.target === bg) {
                this.deselectAll();
            }
        });

        this.applyZoom();
    }

    /**
     * Clear the canvas and reset state
     */
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

    /**
     * Resize canvas without reloading furniture
     * @param {number} width - New canvas width
     * @param {number} height - New canvas height
     * @param {string} backgroundColor - Optional background color
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

    // =============================================================================
    // GRID
    // =============================================================================

    /**
     * Create the grid lines
     */
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

    /**
     * Toggle grid visibility
     */
    toggleGrid() {
        this.showGrid = !this.showGrid;
        if (this.gridLayer) {
            this.gridLayer.style.display = this.showGrid ? 'block' : 'none';
        }
    }

    // =============================================================================
    // RULERS
    // =============================================================================

    /**
     * Create the horizontal and vertical rulers
     */
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

    /**
     * Update ruler positions based on scroll
     */
    updateRulers() {
        if (!this.viewport || !this.rulerH || !this.rulerV) return;
        const scrollLeft = this.viewport.scrollLeft;
        const scrollTop = this.viewport.scrollTop;

        const hSvg = this.rulerH.querySelector('svg');
        const vSvg = this.rulerV.querySelector('svg');

        if (hSvg) hSvg.style.transform = `translateX(-${scrollLeft}px)`;
        if (vSvg) vSvg.style.transform = `translateY(-${scrollTop}px)`;
    }

    // =============================================================================
    // CENTER GUIDES
    // =============================================================================

    /**
     * Create center guide lines
     */
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

    /**
     * Toggle center guides visibility
     */
    toggleCenterGuides() {
        this.showCenterGuides = !this.showCenterGuides;
        if (this.centerGuidesLayer) {
            this.centerGuidesLayer.style.display = this.showCenterGuides ? 'block' : 'none';
        }
    }
};
