/**
 * Map Editor - Drag & Drop Module
 * Handles palette drag & drop functionality for creating new furniture
 */

/**
 * Mixin that adds drag & drop from palette to MapEditor
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with drag-drop methods
 */
export const DragDropMixin = (Base) => class extends Base {

    /**
     * Setup drag & drop from the furniture palette
     */
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

    /**
     * Setup drop zone on the canvas
     */
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
            if (pt.x < 0 || pt.y < 0 ||
                pt.x > this.canvasConfig.width ||
                pt.y > this.canvasConfig.height) {
                if (window.PuroBeach) {
                    window.PuroBeach.showToast('Soltar dentro del canvas', 'warning');
                }
                return;
            }

            // Calculate position (centered on drop point, snapped to grid)
            let x = Math.round((pt.x - data.width / 2) / this.options.snapToGrid) * this.options.snapToGrid;
            let y = Math.round((pt.y - data.height / 2) / this.options.snapToGrid) * this.options.snapToGrid;

            // Constrain to canvas bounds
            x = Math.max(0, Math.min(x, this.canvasConfig.width - data.width));
            y = Math.max(0, Math.min(y, this.canvasConfig.height - data.height));

            await this.createFurniture(data, x, y);
        });
    }
};
