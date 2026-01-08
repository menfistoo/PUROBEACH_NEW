/**
 * Map Editor - Viewport Module
 * Handles zoom, pan, rulers, and view persistence
 */

/**
 * Mixin that adds viewport management to MapEditor
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with viewport methods
 */
export const ViewportMixin = (Base) => class extends Base {

    // =============================================================================
    // WHEEL ZOOM
    // =============================================================================

    setupWheelZoom() {
        if (!this.viewport) return;

        this.viewport.addEventListener('wheel', (e) => {
            // Use Shift+Wheel for zoom to avoid browser zoom conflict
            if (e.shiftKey) {
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
                this.zoom = Math.max(
                    this.options.minZoom,
                    Math.min(this.zoom + delta, this.options.maxZoom)
                );

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
        this._setupPanning();
    }

    /**
     * Setup panning with space key or middle mouse button
     * @private
     */
    _setupPanning() {
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
    // VIEWPORT TRACKING
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
    // ZOOM CONTROLS
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
            const scrollLeft = Math.max(0, (canvasWidth - viewportWidth) / 2 + 20);
            const scrollTop = Math.max(0, (canvasHeight - viewportHeight) / 2 + 20);

            this.viewport.scrollLeft = scrollLeft;
            this.viewport.scrollTop = scrollTop;
        });
    }
};
