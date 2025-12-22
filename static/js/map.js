/**
 * Beach Map Interactive Controller
 * Phase 7: Interactive SVG-based beach map with real-time availability
 */

class BeachMap {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container #${containerId} not found`);
        }

        // Configuration
        this.options = {
            apiUrl: '/beach/api/map/data',
            autoRefreshInterval: 30000,  // 30 seconds
            enableDragDrop: false,
            enableZoom: true,
            minZoom: 0.5,
            maxZoom: 3,
            snapToGrid: 10,
            ...options
        };

        // State
        this.currentDate = this.options.initialDate || new Date().toISOString().split('T')[0];
        this.data = null;
        this.selectedFurniture = new Set();
        this.zoom = 1;
        this.pan = { x: 0, y: 0 };
        this.isDragging = false;
        this.dragTarget = null;
        this.editMode = false;
        this.autoRefreshTimer = null;

        // DOM elements
        this.svg = null;
        this.zonesLayer = null;
        this.furnitureLayer = null;
        this.selectionLayer = null;
        this.tooltip = null;

        // Event callbacks
        this.callbacks = {
            onSelect: null,
            onDeselect: null,
            onDateChange: null,
            onFurnitureClick: null,
            onError: null
        };

        // Bind methods
        this.handleFurnitureClick = this.handleFurnitureClick.bind(this);
        this.handleFurnitureMouseEnter = this.handleFurnitureMouseEnter.bind(this);
        this.handleFurnitureMouseLeave = this.handleFurnitureMouseLeave.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);

        // Initialize
        this.init();
    }

    async init() {
        this.createSVG();
        this.createTooltip();
        this.setupEventListeners();
        await this.loadData();
    }

    createSVG() {
        // Clear container
        this.container.innerHTML = '';

        // Create SVG element
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('id', 'beach-map');
        this.svg.setAttribute('class', 'beach-map-svg');
        this.svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

        // Create defs for patterns and filters
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <filter id="selected-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
            <pattern id="zone-pattern" patternUnits="userSpaceOnUse" width="20" height="20">
                <rect width="20" height="20" fill="rgba(245, 230, 211, 0.3)"/>
                <circle cx="10" cy="10" r="1" fill="rgba(212, 175, 55, 0.2)"/>
            </pattern>
        `;
        this.svg.appendChild(defs);

        // Create layers
        this.zonesLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.zonesLayer.setAttribute('id', 'zones-layer');

        this.furnitureLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.furnitureLayer.setAttribute('id', 'furniture-layer');

        this.selectionLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.selectionLayer.setAttribute('id', 'selection-layer');

        this.svg.appendChild(this.zonesLayer);
        this.svg.appendChild(this.furnitureLayer);
        this.svg.appendChild(this.selectionLayer);

        this.container.appendChild(this.svg);
    }

    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'map-tooltip';
        this.tooltip.style.display = 'none';
        document.body.appendChild(this.tooltip);
    }

    setupEventListeners() {
        // Keyboard navigation
        document.addEventListener('keydown', this.handleKeyDown);

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

        this.renderZones();
        this.renderFurniture();
        this.updateLegend();
    }

    renderZones() {
        this.zonesLayer.innerHTML = '';

        if (!this.data.zones || !this.data.zone_bounds) return;

        this.data.zones.forEach(zone => {
            const bounds = this.data.zone_bounds[zone.id];
            if (!bounds) return;

            const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            group.setAttribute('class', 'zone-group');
            group.setAttribute('data-zone-id', zone.id);

            // Zone background
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', bounds.x);
            rect.setAttribute('y', bounds.y);
            rect.setAttribute('width', bounds.width);
            rect.setAttribute('height', bounds.height);
            rect.setAttribute('fill', 'url(#zone-pattern)');
            rect.setAttribute('stroke', zone.color || '#D4AF37');
            rect.setAttribute('stroke-width', '2');
            rect.setAttribute('stroke-dasharray', '8 4');
            rect.setAttribute('rx', '8');

            // Zone label
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', bounds.x + 15);
            label.setAttribute('y', bounds.y + 25);
            label.setAttribute('class', 'zone-label');
            label.setAttribute('fill', '#1A3A5C');
            label.setAttribute('font-size', '14');
            label.setAttribute('font-weight', '600');
            label.textContent = zone.name;

            group.appendChild(rect);
            group.appendChild(label);
            this.zonesLayer.appendChild(group);
        });
    }

    renderFurniture() {
        this.furnitureLayer.innerHTML = '';

        if (!this.data.furniture) return;

        this.data.furniture.forEach(item => {
            const group = this.createFurnitureElement(item);
            this.furnitureLayer.appendChild(group);
        });
    }

    createFurnitureElement(item) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'furniture-item');
        group.setAttribute('data-furniture-id', item.id);
        group.setAttribute('transform', `translate(${item.position_x}, ${item.position_y}) rotate(${item.rotation || 0})`);
        group.style.cursor = 'pointer';

        // Get furniture type config
        const typeConfig = this.data.furniture_types[item.furniture_type] || {};

        // Determine color based on availability
        const availability = this.data.availability[item.id];
        const isAvailable = !availability || availability.available;
        const state = availability ? availability.state : null;

        let fillColor, strokeColor;
        if (isAvailable) {
            fillColor = '#F5E6D3';  // Warm sand - available
            strokeColor = '#D4AF37';  // Gold stroke
        } else if (state && this.data.state_colors[state]) {
            fillColor = this.data.state_colors[state];
            strokeColor = this.darkenColor(fillColor, 30);
        } else {
            fillColor = typeConfig.fill_color || '#A0522D';
            strokeColor = typeConfig.stroke_color || '#654321';
        }

        // Check if selected
        if (this.selectedFurniture.has(item.id)) {
            fillColor = '#D4AF37';  // Gold for selected
            strokeColor = '#8B6914';
            group.setAttribute('filter', 'url(#selected-glow)');
        }

        // Create shape based on type
        const width = item.width || typeConfig.default_width || 60;
        const height = item.height || typeConfig.default_height || 40;
        const shape = this.createShape(typeConfig.map_shape || 'rounded_rect', width, height, fillColor, strokeColor);
        group.appendChild(shape);

        // Add label
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('x', width / 2);
        label.setAttribute('y', height / 2);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('dominant-baseline', 'middle');
        label.setAttribute('fill', this.getContrastColor(fillColor));
        label.setAttribute('font-size', '12');
        label.setAttribute('font-weight', '600');
        label.setAttribute('pointer-events', 'none');
        label.textContent = item.number;
        group.appendChild(label);

        // Event listeners
        group.addEventListener('click', (e) => this.handleFurnitureClick(e, item));
        group.addEventListener('mouseenter', (e) => this.handleFurnitureMouseEnter(e, item));
        group.addEventListener('mouseleave', (e) => this.handleFurnitureMouseLeave(e, item));

        return group;
    }

    createShape(shapeType, width, height, fillColor, strokeColor) {
        const strokeWidth = 2;
        let shape;

        switch (shapeType) {
            case 'circle':
                shape = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                const radius = Math.min(width, height) / 2 - strokeWidth;
                shape.setAttribute('cx', width / 2);
                shape.setAttribute('cy', height / 2);
                shape.setAttribute('r', radius);
                break;

            case 'ellipse':
                shape = document.createElementNS('http://www.w3.org/2000/svg', 'ellipse');
                shape.setAttribute('cx', width / 2);
                shape.setAttribute('cy', height / 2);
                shape.setAttribute('rx', width / 2 - strokeWidth);
                shape.setAttribute('ry', height / 2 - strokeWidth);
                break;

            case 'rectangle':
            case 'rounded_rect':
            default:
                shape = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                shape.setAttribute('x', strokeWidth);
                shape.setAttribute('y', strokeWidth);
                shape.setAttribute('width', width - 2 * strokeWidth);
                shape.setAttribute('height', height - 2 * strokeWidth);
                if (shapeType === 'rounded_rect') {
                    shape.setAttribute('rx', '5');
                    shape.setAttribute('ry', '5');
                }
                break;
        }

        shape.setAttribute('fill', fillColor);
        shape.setAttribute('stroke', strokeColor);
        shape.setAttribute('stroke-width', strokeWidth);

        return shape;
    }

    // ==========================================================================
    // SELECTION
    // ==========================================================================

    handleFurnitureClick(event, item) {
        event.stopPropagation();
        const addToSelection = event.ctrlKey || event.metaKey;
        this.selectFurniture(item.id, addToSelection);

        if (this.callbacks.onFurnitureClick) {
            this.callbacks.onFurnitureClick(item, this.getSelectedFurniture());
        }
    }

    selectFurniture(id, addToSelection = false) {
        if (!addToSelection) {
            this.selectedFurniture.clear();
        }

        if (this.selectedFurniture.has(id)) {
            this.selectedFurniture.delete(id);
            if (this.callbacks.onDeselect) {
                this.callbacks.onDeselect(id);
            }
        } else {
            this.selectedFurniture.add(id);
            if (this.callbacks.onSelect) {
                this.callbacks.onSelect(id);
            }
        }

        this.renderFurniture();  // Re-render to update visual state
        this.updateSelectionPanel();
    }

    deselectFurniture(id) {
        this.selectedFurniture.delete(id);
        this.renderFurniture();
        this.updateSelectionPanel();
    }

    clearSelection() {
        this.selectedFurniture.clear();
        this.renderFurniture();
        this.updateSelectionPanel();
    }

    getSelectedFurniture() {
        return Array.from(this.selectedFurniture);
    }

    getSelectedFurnitureData() {
        return this.data.furniture.filter(f => this.selectedFurniture.has(f.id));
    }

    updateSelectionPanel() {
        const panel = document.getElementById('selection-panel');
        if (!panel) return;

        const selected = this.getSelectedFurnitureData();
        if (selected.length === 0) {
            panel.style.display = 'none';
            return;
        }

        panel.style.display = 'block';
        const countEl = panel.querySelector('.selection-count');
        const listEl = panel.querySelector('.selection-list');
        const capacityEl = panel.querySelector('.selection-capacity');

        if (countEl) countEl.textContent = selected.length;
        if (listEl) listEl.textContent = selected.map(f => f.number).join(', ');
        if (capacityEl) {
            const totalCapacity = selected.reduce((sum, f) => sum + (f.capacity || 2), 0);
            capacityEl.textContent = totalCapacity;
        }
    }

    // ==========================================================================
    // TOOLTIPS
    // ==========================================================================

    handleFurnitureMouseEnter(event, item) {
        const availability = this.data.availability[item.id];
        const typeConfig = this.data.furniture_types[item.furniture_type] || {};

        let content = `
            <div class="tooltip-header">
                <strong>${item.number}</strong>
                <span class="badge bg-secondary ms-2">${typeConfig.display_name || item.furniture_type}</span>
            </div>
            <div class="tooltip-body">
                <div><i class="fas fa-users me-1"></i> Capacidad: ${item.capacity} personas</div>
                <div><i class="fas fa-map-marker-alt me-1"></i> ${item.zone_name}</div>
        `;

        if (availability && !availability.available) {
            content += `
                <hr class="my-2">
                <div class="text-warning"><strong>Reservado</strong></div>
                <div><i class="fas fa-user me-1"></i> ${availability.customer_name || 'Cliente'}</div>
                <div><i class="fas fa-ticket-alt me-1"></i> ${availability.ticket_number || ''}</div>
                <div><span class="badge" style="background-color: ${this.data.state_colors[availability.state] || '#6c757d'}">${availability.state}</span></div>
            `;
        } else {
            content += `<div class="text-success mt-2"><strong>Disponible</strong></div>`;
        }

        content += '</div>';

        this.tooltip.innerHTML = content;
        this.tooltip.style.display = 'block';
        this.positionTooltip(event);
    }

    handleFurnitureMouseLeave(event, item) {
        this.tooltip.style.display = 'none';
    }

    positionTooltip(event) {
        const offset = 15;
        let x = event.pageX + offset;
        let y = event.pageY + offset;

        // Keep tooltip in viewport
        const rect = this.tooltip.getBoundingClientRect();
        if (x + rect.width > window.innerWidth) {
            x = event.pageX - rect.width - offset;
        }
        if (y + rect.height > window.innerHeight) {
            y = event.pageY - rect.height - offset;
        }

        this.tooltip.style.left = x + 'px';
        this.tooltip.style.top = y + 'px';
    }

    // ==========================================================================
    // DATE NAVIGATION
    // ==========================================================================

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
        const date = new Date(dateStr + 'T12:00:00');
        const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
        return date.toLocaleDateString('es-ES', options);
    }

    // ==========================================================================
    // ZOOM & PAN
    // ==========================================================================

    zoomIn(factor = 1.2) {
        this.setZoom(this.zoom * factor);
    }

    zoomOut(factor = 1.2) {
        this.setZoom(this.zoom / factor);
    }

    zoomReset() {
        this.setZoom(1);
        this.pan = { x: 0, y: 0 };
        this.updateTransform();
    }

    setZoom(level) {
        this.zoom = Math.max(this.options.minZoom, Math.min(this.options.maxZoom, level));
        this.updateTransform();
    }

    updateTransform() {
        const transform = `scale(${this.zoom}) translate(${this.pan.x}px, ${this.pan.y}px)`;
        this.svg.style.transform = transform;
    }

    // ==========================================================================
    // AUTO-REFRESH
    // ==========================================================================

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

    // ==========================================================================
    // DRAG & DROP (Admin Only)
    // ==========================================================================

    enableEditMode() {
        this.editMode = true;
        this.container.classList.add('edit-mode');
        this.setupDragDrop();
    }

    disableEditMode() {
        this.editMode = false;
        this.container.classList.remove('edit-mode');
    }

    setupDragDrop() {
        if (!this.editMode) return;

        this.furnitureLayer.querySelectorAll('.furniture-item').forEach(group => {
            group.style.cursor = 'move';
            group.addEventListener('mousedown', this.handleDragStart.bind(this));
        });

        document.addEventListener('mousemove', this.handleDrag.bind(this));
        document.addEventListener('mouseup', this.handleDragEnd.bind(this));
    }

    handleDragStart(event) {
        if (!this.editMode) return;

        const group = event.target.closest('.furniture-item');
        if (!group) return;

        this.isDragging = true;
        this.dragTarget = group;
        this.dragStart = {
            x: event.clientX,
            y: event.clientY
        };

        // Get current position
        const transform = group.getAttribute('transform');
        const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
        if (match) {
            this.dragStart.itemX = parseFloat(match[1]);
            this.dragStart.itemY = parseFloat(match[2]);
        }

        group.classList.add('dragging');
    }

    handleDrag(event) {
        if (!this.isDragging || !this.dragTarget) return;

        const dx = (event.clientX - this.dragStart.x) / this.zoom;
        const dy = (event.clientY - this.dragStart.y) / this.zoom;

        let newX = this.dragStart.itemX + dx;
        let newY = this.dragStart.itemY + dy;

        // Snap to grid
        if (this.options.snapToGrid) {
            newX = Math.round(newX / this.options.snapToGrid) * this.options.snapToGrid;
            newY = Math.round(newY / this.options.snapToGrid) * this.options.snapToGrid;
        }

        const rotation = this.dragTarget.getAttribute('transform').match(/rotate\(([^)]+)\)/);
        const rotationStr = rotation ? ` rotate(${rotation[1]})` : '';

        this.dragTarget.setAttribute('transform', `translate(${newX}, ${newY})${rotationStr}`);
    }

    async handleDragEnd(event) {
        if (!this.isDragging || !this.dragTarget) return;

        const group = this.dragTarget;
        const furnitureId = parseInt(group.dataset.furnitureId);

        // Get final position
        const transform = group.getAttribute('transform');
        const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);

        if (match) {
            const x = parseFloat(match[1]);
            const y = parseFloat(match[2]);

            // Save position
            await this.savePosition(furnitureId, x, y);
        }

        group.classList.remove('dragging');
        this.isDragging = false;
        this.dragTarget = null;
    }

    async savePosition(furnitureId, x, y, rotation = null) {
        try {
            const response = await fetch(`/beach/api/map/furniture/${furnitureId}/position`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ x, y, rotation })
            });

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error);
            }

            this.showToast('Posicion guardada', 'success');
        } catch (error) {
            console.error('Error saving position:', error);
            this.showToast('Error guardando posicion', 'error');
        }
    }

    // ==========================================================================
    // KEYBOARD NAVIGATION
    // ==========================================================================

    handleKeyDown(event) {
        // Escape to clear selection
        if (event.key === 'Escape') {
            this.clearSelection();
            return;
        }

        // Arrow keys for date navigation
        if (event.key === 'ArrowLeft' && event.altKey) {
            event.preventDefault();
            this.goToPreviousDay();
        } else if (event.key === 'ArrowRight' && event.altKey) {
            event.preventDefault();
            this.goToNextDay();
        }

        // Zoom with + and -
        if (event.key === '+' || event.key === '=') {
            this.zoomIn();
        } else if (event.key === '-') {
            this.zoomOut();
        }
    }

    // ==========================================================================
    // LEGEND
    // ==========================================================================

    updateLegend() {
        const legend = document.getElementById('map-legend');
        if (!legend || !this.data.states) return;

        let html = '<div class="legend-items d-flex flex-wrap gap-2">';

        // Available state
        html += `
            <div class="legend-item d-flex align-items-center">
                <span class="legend-color" style="background-color: #F5E6D3; border: 2px solid #D4AF37;"></span>
                <span class="ms-1">Disponible</span>
            </div>
        `;

        // State colors from database
        this.data.states.forEach(state => {
            if (state.active) {
                html += `
                    <div class="legend-item d-flex align-items-center">
                        <span class="legend-color" style="background-color: ${state.color};"></span>
                        <span class="ms-1">${state.name}</span>
                    </div>
                `;
            }
        });

        html += '</div>';
        legend.innerHTML = html;
    }

    // ==========================================================================
    // UTILITIES
    // ==========================================================================

    darkenColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.max(0, (num >> 16) - amt);
        const G = Math.max(0, ((num >> 8) & 0x00FF) - amt);
        const B = Math.max(0, (num & 0x0000FF) - amt);
        return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
    }

    getContrastColor(hexcolor) {
        const r = parseInt(hexcolor.slice(1, 3), 16);
        const g = parseInt(hexcolor.slice(3, 5), 16);
        const b = parseInt(hexcolor.slice(5, 7), 16);
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.5 ? '#1A3A5C' : '#FFFFFF';
    }

    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    showToast(message, type = 'info') {
        if (window.PuroBeach && window.PuroBeach.showToast) {
            window.PuroBeach.showToast(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger m-3';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
        this.container.appendChild(errorDiv);
    }

    // ==========================================================================
    // PUBLIC API
    // ==========================================================================

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
        document.removeEventListener('keydown', this.handleKeyDown);
        if (this.tooltip && this.tooltip.parentNode) {
            this.tooltip.parentNode.removeChild(this.tooltip);
        }
    }
}

// Export for use
window.BeachMap = BeachMap;
