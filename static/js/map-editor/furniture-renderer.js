/**
 * Map Editor - Furniture Renderer Module
 * Handles furniture element creation and rendering
 */

/**
 * Mixin that adds furniture rendering to MapEditor
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with rendering methods
 */
export const FurnitureRendererMixin = (Base) => class extends Base {

    /**
     * Render all furniture items on the canvas
     */
    renderFurniture() {
        if (!this.furnitureLayer) return;
        this.furnitureLayer.innerHTML = '';
        this.furniture.forEach(item => {
            const group = this.createFurnitureElement(item);
            this.furnitureLayer.appendChild(group);
        });
    }

    /**
     * Create a furniture SVG element
     * @param {Object} item - Furniture data object
     * @returns {SVGGElement} SVG group element
     */
    createFurnitureElement(item) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'furniture-item');
        group.setAttribute('data-id', item.id);
        group.setAttribute('transform',
            `translate(${item.position_x}, ${item.position_y}) rotate(${item.rotation || 0}, ${item.width / 2}, ${item.height / 2})`
        );

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

    /**
     * Create the shape element for a furniture item
     * @param {Object} item - Furniture data
     * @param {Object} type - Furniture type definition
     * @returns {SVGElement} Shape element (rect or ellipse)
     */
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

    /**
     * Setup mouse events for furniture element (drag to move)
     * @param {SVGGElement} group - The furniture group element
     * @param {Object} item - Furniture data
     */
    setupFurnitureEvents(group, item) {
        let startX, startY;
        let startPositions = new Map(); // Store start positions for all selected items

        group.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;

            // Ctrl+click/drag should initiate marquee selection, not move items
            // Let the event bubble up to the viewport handler
            if (e.ctrlKey || e.metaKey) {
                // Just toggle selection on click, marquee will be handled by viewport
                this.toggleItemSelection(item);
                return;
            }

            e.preventDefault();
            e.stopPropagation();

            // If item is not selected, select it (and clear others unless Shift)
            if (!this.isSelected(item.id)) {
                this.selectItem(item, e.shiftKey);
            }

            // Start dragging all selected items
            this.isDragging = true;

            const pt = this.getSVGPoint(e);
            startX = pt.x;
            startY = pt.y;

            // Store start positions for all selected items
            startPositions.clear();
            this.getSelectedItems().forEach(selectedItem => {
                startPositions.set(selectedItem.id, {
                    x: selectedItem.position_x,
                    y: selectedItem.position_y
                });
                const g = this.furnitureLayer.querySelector(`[data-id="${selectedItem.id}"]`);
                if (g) g.classList.add('dragging');
            });
        });

        const handleMouseMove = (e) => {
            if (!this.isDragging || startPositions.size === 0) return;

            const pt = this.getSVGPoint(e);
            const deltaX = pt.x - startX;
            const deltaY = pt.y - startY;

            // Move all selected items
            this.getSelectedItems().forEach(selectedItem => {
                const startPos = startPositions.get(selectedItem.id);
                if (!startPos) return;

                let newX = startPos.x + deltaX;
                let newY = startPos.y + deltaY;

                // Snap to grid
                newX = Math.round(newX / this.options.snapToGrid) * this.options.snapToGrid;
                newY = Math.round(newY / this.options.snapToGrid) * this.options.snapToGrid;

                // Bounds check
                newX = Math.max(0, Math.min(newX, this.canvasConfig.width - selectedItem.width));
                newY = Math.max(0, Math.min(newY, this.canvasConfig.height - selectedItem.height));

                const g = this.furnitureLayer.querySelector(`[data-id="${selectedItem.id}"]`);
                if (g) {
                    g.setAttribute('transform',
                        `translate(${newX}, ${newY}) rotate(${selectedItem.rotation || 0}, ${selectedItem.width / 2}, ${selectedItem.height / 2})`
                    );
                }

                selectedItem.position_x = newX;
                selectedItem.position_y = newY;
            });

            this.emit('itemMoved', { count: startPositions.size });
        };

        const handleMouseUp = async () => {
            if (!this.isDragging) return;

            this.isDragging = false;

            // Check if any items moved
            let anyMoved = false;
            const updates = [];

            this.getSelectedItems().forEach(selectedItem => {
                const startPos = startPositions.get(selectedItem.id);
                const g = this.furnitureLayer.querySelector(`[data-id="${selectedItem.id}"]`);
                if (g) g.classList.remove('dragging');

                if (startPos && (selectedItem.position_x !== startPos.x || selectedItem.position_y !== startPos.y)) {
                    anyMoved = true;
                    updates.push({
                        id: selectedItem.id,
                        x: selectedItem.position_x,
                        y: selectedItem.position_y,
                        rotation: selectedItem.rotation
                    });
                }
            });

            // Save all positions in batch if any moved
            if (anyMoved && updates.length > 0) {
                await this.saveBatchPositions(updates);
            }

            startPositions.clear();
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        group.addEventListener('mousedown', () => {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        });
    }

    /**
     * Convert client coordinates to SVG coordinates
     * @param {MouseEvent} e - Mouse event
     * @returns {Object} Point with x, y in SVG coordinates
     */
    getSVGPoint(e) {
        const pt = this.svg.createSVGPoint();
        pt.x = e.clientX;
        pt.y = e.clientY;
        const ctm = this.svg.getScreenCTM();
        if (!ctm) return { x: -1, y: -1 };  // Return invalid point if CTM not available
        return pt.matrixTransform(ctm.inverse());
    }
};
