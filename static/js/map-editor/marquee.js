/**
 * Map Editor - Marquee Selection Module
 * Handles rectangle-drag selection of multiple items
 */

/**
 * Mixin that adds marquee selection to MapEditor
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with marquee selection methods
 */
export const MarqueeMixin = (Base) => class extends Base {

    /**
     * Setup marquee selection (drag rectangle to select multiple items)
     */
    setupMarqueeSelection() {
        if (!this.viewport) return;

        let startPoint = null;
        let mouseDownPos = null;
        let isMouseDown = false;
        let marqueeStarted = false;

        // Start potential marquee on mousedown
        // Use capture phase to intercept Ctrl+drag even on furniture items
        this.viewport.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;

            const target = e.target;
            const isOnFurniture = target.closest('.furniture-item');

            // If Ctrl is held, always allow marquee selection (even on furniture)
            // If not on furniture, also allow normal marquee
            if (!e.ctrlKey && isOnFurniture) return;

            // For Ctrl+click on furniture, the toggle was already done by setupFurnitureEvents
            // But we still want to enable marquee if they drag

            // Store initial position to detect drag vs click
            mouseDownPos = { x: e.clientX, y: e.clientY };
            isMouseDown = true;
            marqueeStarted = false;

            const pt = this.getSVGPoint(e);
            startPoint = { x: pt.x, y: pt.y };
        }, true); // Use capture phase

        // Update marquee on mousemove
        document.addEventListener('mousemove', (e) => {
            if (!isMouseDown || !startPoint) return;

            // Check if we've moved enough to start marquee (5px threshold)
            const dx = Math.abs(e.clientX - mouseDownPos.x);
            const dy = Math.abs(e.clientY - mouseDownPos.y);

            if (!marqueeStarted && (dx > 5 || dy > 5)) {
                // Start marquee
                marqueeStarted = true;
                this.isMarqueeSelecting = true;

                // Clear selection if not holding Shift
                if (!e.shiftKey) {
                    this.deselectAll();
                }

                // Create marquee rectangle
                this.marqueeRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                this.marqueeRect.setAttribute('class', 'marquee-rect');
                this.marqueeRect.setAttribute('x', startPoint.x);
                this.marqueeRect.setAttribute('y', startPoint.y);
                this.marqueeRect.setAttribute('width', 0);
                this.marqueeRect.setAttribute('height', 0);
                this.selectionLayer?.appendChild(this.marqueeRect);
            }

            if (!this.isMarqueeSelecting || !this.marqueeRect) return;

            const pt = this.getSVGPoint(e);
            const x = Math.min(startPoint.x, pt.x);
            const y = Math.min(startPoint.y, pt.y);
            const width = Math.abs(pt.x - startPoint.x);
            const height = Math.abs(pt.y - startPoint.y);

            this.marqueeRect.setAttribute('x', x);
            this.marqueeRect.setAttribute('y', y);
            this.marqueeRect.setAttribute('width', width);
            this.marqueeRect.setAttribute('height', height);

            // Preview selection (highlight items within marquee)
            this.previewMarqueeSelection(x, y, width, height);
        });

        // End marquee on mouseup
        document.addEventListener('mouseup', (e) => {
            if (this.isMarqueeSelecting && this.marqueeRect) {
                const x = parseFloat(this.marqueeRect.getAttribute('x'));
                const y = parseFloat(this.marqueeRect.getAttribute('y'));
                const width = parseFloat(this.marqueeRect.getAttribute('width'));
                const height = parseFloat(this.marqueeRect.getAttribute('height'));

                // Only select if marquee has some size
                if (width > 5 && height > 5) {
                    // Use Ctrl or Shift to add to selection
                    const addToSelection = e.shiftKey || e.ctrlKey;
                    this.selectItemsInRect(x, y, width, height, addToSelection);
                    // Prevent the click handler from deselecting
                    this.justFinishedMarquee = true;
                }

                this.marqueeRect.remove();
                this.marqueeRect = null;
            }

            // Remove preview highlights
            this.furnitureLayer?.querySelectorAll('.marquee-preview').forEach(el => {
                el.classList.remove('marquee-preview');
            });

            // Reset state
            this.isMarqueeSelecting = false;
            isMouseDown = false;
            marqueeStarted = false;
            startPoint = null;
            mouseDownPos = null;
        });
    }

    /**
     * Preview items that would be selected by the marquee
     * @param {number} x - Rectangle X
     * @param {number} y - Rectangle Y
     * @param {number} width - Rectangle width
     * @param {number} height - Rectangle height
     */
    previewMarqueeSelection(x, y, width, height) {
        // Remove previous previews
        this.furnitureLayer?.querySelectorAll('.marquee-preview').forEach(el => {
            el.classList.remove('marquee-preview');
        });

        // Add preview to items within marquee
        this.furniture.forEach(item => {
            if (this.isItemInRect(item, x, y, width, height)) {
                const group = this.furnitureLayer.querySelector(`[data-id="${item.id}"]`);
                if (group && !this.selectedItems.has(item.id)) {
                    group.classList.add('marquee-preview');
                }
            }
        });
    }

    /**
     * Select all items within a rectangle
     * @param {number} x - Rectangle X
     * @param {number} y - Rectangle Y
     * @param {number} width - Rectangle width
     * @param {number} height - Rectangle height
     * @param {boolean} addToSelection - Add to existing selection
     */
    selectItemsInRect(x, y, width, height, addToSelection = false) {
        const itemsToSelect = [];

        this.furniture.forEach(item => {
            if (this.isItemInRect(item, x, y, width, height)) {
                itemsToSelect.push(item.id);
            }
        });

        if (itemsToSelect.length > 0) {
            this.selectMultiple(itemsToSelect, addToSelection);
        }
    }

    /**
     * Check if an item's center is within a rectangle
     * @param {Object} item - Furniture item
     * @param {number} rectX - Rectangle X
     * @param {number} rectY - Rectangle Y
     * @param {number} rectWidth - Rectangle width
     * @param {number} rectHeight - Rectangle height
     * @returns {boolean} True if item center is in rectangle
     */
    isItemInRect(item, rectX, rectY, rectWidth, rectHeight) {
        // Check if item center is within rectangle
        const itemCenterX = item.position_x + item.width / 2;
        const itemCenterY = item.position_y + item.height / 2;

        return itemCenterX >= rectX &&
               itemCenterX <= rectX + rectWidth &&
               itemCenterY >= rectY &&
               itemCenterY <= rectY + rectHeight;
    }
};
