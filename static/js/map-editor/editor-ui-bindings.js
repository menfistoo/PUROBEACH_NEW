/**
 * Map Editor - UI Bindings
 * Shared DOM event wiring for map_editor.html and furniture_manager.html.
 * Each function attaches listeners to standard DOM IDs used by both templates.
 */

import { parseFeatures, toggleFeature } from './feature-utils.js';

// =============================================================================
// HELPERS
// =============================================================================

/** Get CSRF token from meta tag. */
function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

/** Shorthand for safe getElementById (null-safe event binding). */
function el(id) {
    return document.getElementById(id);
}

// =============================================================================
// PALETTE COLLAPSE
// =============================================================================

/**
 * Bind the palette collapse/expand toggle button.
 * DOM IDs: editor-container, btn-collapse-palette
 */
export function bindPaletteCollapse() {
    const container = el('editor-container');
    const btn = el('btn-collapse-palette');
    if (!btn || !container) return;

    btn.addEventListener('click', function () {
        container.classList.toggle('palette-collapsed');
        const icon = this.querySelector('i');
        if (container.classList.contains('palette-collapsed')) {
            icon.classList.replace('fa-chevron-left', 'fa-chevron-right');
        } else {
            icon.classList.replace('fa-chevron-right', 'fa-chevron-left');
        }
    });
}

// =============================================================================
// ZONE CONTROLS
// =============================================================================

/**
 * Bind zone selector change + zone settings modal.
 * DOM IDs: zone-selector, btn-zone-settings, empty-canvas,
 *          zone-canvas-width, zone-canvas-height, zone-bg-color,
 *          zone-bg-preview, btn-save-zone-settings, zoneSettingsModal
 * @param {object} editor - MapEditor instance
 * @param {object} [options]
 * @param {string} [options.emptyCanvasId='empty-canvas']
 */
export function bindZoneControls(editor, options = {}) {
    const emptyCanvasId = options.emptyCanvasId || 'empty-canvas';
    const zoneSelector = el('zone-selector');
    const btnZoneSettings = el('btn-zone-settings');
    if (!zoneSelector) return;

    zoneSelector.addEventListener('change', function () {
        const zoneId = this.value;
        if (zoneId) {
            const opt = this.options[this.selectedIndex];
            editor.loadZone(zoneId, {
                width: parseFloat(opt.dataset.width) || 800,
                height: parseFloat(opt.dataset.height) || 400,
                backgroundColor: opt.dataset.bg || '#FAFAFA'
            });
            if (btnZoneSettings) btnZoneSettings.disabled = false;
            el(emptyCanvasId)?.classList.add('d-none');
        } else {
            editor.clearCanvas();
            if (btnZoneSettings) btnZoneSettings.disabled = true;
            el(emptyCanvasId)?.classList.remove('d-none');
        }
    });

    // Zone settings modal
    if (btnZoneSettings) {
        btnZoneSettings.addEventListener('click', function () {
            const opt = zoneSelector.options[zoneSelector.selectedIndex];
            el('zone-canvas-width').value = opt.dataset.width || 800;
            el('zone-canvas-height').value = opt.dataset.height || 400;
            el('zone-bg-color').value = opt.dataset.bg || '#FAFAFA';
            el('zone-bg-preview').style.backgroundColor = opt.dataset.bg || '#FAFAFA';
            new bootstrap.Modal(el('zoneSettingsModal')).show();
        });
    }

    el('zone-bg-color')?.addEventListener('input', function () {
        el('zone-bg-preview').style.backgroundColor = this.value;
    });

    el('btn-save-zone-settings')?.addEventListener('click', async function () {
        const saveBtn = this;
        const zoneId = zoneSelector.value;
        const width = el('zone-canvas-width').value;
        const height = el('zone-canvas-height').value;
        const bgColor = el('zone-bg-color').value;

        if (window.PuroBeach) window.PuroBeach.setButtonLoading(saveBtn, true, 'Guardando...');

        try {
            const response = await fetch(`/beach/config/map-editor/zone/${zoneId}/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
                body: JSON.stringify({
                    canvas_width: parseFloat(width),
                    canvas_height: parseFloat(height),
                    background_color: bgColor
                })
            });

            const result = await response.json();
            if (result.success) {
                const opt = zoneSelector.options[zoneSelector.selectedIndex];
                opt.dataset.width = width;
                opt.dataset.height = height;
                opt.dataset.bg = bgColor;

                editor.loadZone(zoneId, {
                    width: parseFloat(width),
                    height: parseFloat(height),
                    backgroundColor: bgColor
                });

                bootstrap.Modal.getInstance(el('zoneSettingsModal')).hide();
                if (window.PuroBeach) window.PuroBeach.showToast('Configuración guardada', 'success');
            }
        } catch (error) {
            console.error('Error saving zone settings:', error);
            if (window.PuroBeach) window.PuroBeach.showToast('Error al guardar', 'error');
        } finally {
            if (window.PuroBeach) window.PuroBeach.setButtonLoading(saveBtn, false);
        }
    });
}

// =============================================================================
// TOOLBAR CONTROLS
// =============================================================================

/**
 * Bind snap, grid, center, zoom, save-view buttons + restore saved view.
 * @param {object} editor - MapEditor instance
 */
export function bindToolbarControls(editor) {
    // Snap size buttons
    document.querySelectorAll('[id^="btn-snap-"]').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('[id^="btn-snap-"]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            editor.setSnapSize(parseInt(this.id.replace('btn-snap-', '')));
        });
    });

    // Grid toggle
    el('btn-toggle-grid')?.addEventListener('click', function () {
        this.classList.toggle('active');
        editor.toggleGrid();
    });

    // Center guides toggle
    el('btn-toggle-center')?.addEventListener('click', function () {
        this.classList.toggle('active');
        editor.toggleCenterGuides();
    });

    // Zoom
    el('btn-zoom-in')?.addEventListener('click', () => editor.zoomIn());
    el('btn-zoom-out')?.addEventListener('click', () => editor.zoomOut());
    el('btn-zoom-reset')?.addEventListener('click', () => editor.zoomReset());

    // Save view
    el('btn-save-view')?.addEventListener('click', function () {
        if (editor.saveCurrentView()) {
            if (window.PuroBeach) window.PuroBeach.showToast('Vista guardada', 'success');
        } else {
            if (window.PuroBeach) window.PuroBeach.showToast('Error al guardar vista', 'error');
        }
    });

    // Restore saved view settings
    const savedView = editor.getSavedView();
    if (savedView) {
        if (savedView.showGrid) {
            el('btn-toggle-grid')?.classList.add('active');
            editor.showGrid = true;
        }
        if (savedView.showCenterGuides === false) {
            el('btn-toggle-center')?.classList.remove('active');
            editor.showCenterGuides = false;
        }
        if (savedView.snapSize) {
            document.querySelectorAll('[id^="btn-snap-"]').forEach(b => b.classList.remove('active'));
            const snapBtn = el(`btn-snap-${savedView.snapSize}`);
            if (snapBtn) {
                snapBtn.classList.add('active');
                editor.setSnapSize(savedView.snapSize);
            }
        }
    }

    // Initialize zoom display
    const zoomLevel = el('zoom-level');
    if (zoomLevel) zoomLevel.textContent = `${Math.round(editor.zoom * 100)}%`;

    // Delete selected
    el('btn-delete-selected')?.addEventListener('click', function () {
        PuroBeach.confirmAction({
            title: 'Confirmar eliminación',
            message: '¿Eliminar el elemento seleccionado?',
            confirmText: 'Eliminar',
            confirmClass: 'btn-danger',
            iconClass: 'fa-trash-alt',
            onConfirm: function() {
                editor.deleteSelected();
            }
        });
    });
}

// =============================================================================
// PROPERTY PANEL
// =============================================================================

/**
 * Bind property input change handlers + close button.
 * @param {object} editor - MapEditor instance
 * @param {object} [options]
 * @param {string[]} [options.propertyIds] - DOM IDs of property inputs (e.g. ['prop-x', 'prop-y', ...])
 */
export function bindPropertyPanel(editor, options = {}) {
    // Close button
    el('btn-close-properties')?.addEventListener('click', function () {
        el('properties-panel')?.classList.remove('active');
        editor.deselectAll();
    });

    // Property inputs
    const ids = options.propertyIds || ['prop-x', 'prop-y', 'prop-rotation', 'prop-capacity'];
    ids.forEach(id => {
        el(id)?.addEventListener('change', function () {
            const prop = id.replace('prop-', '');
            const value = parseInt(this.value) || 0;
            if (prop === 'x') editor.updateSelectedProperty('position_x', value);
            else if (prop === 'y') editor.updateSelectedProperty('position_y', value);
            else editor.updateSelectedProperty(prop, value);
        });
    });
}

// =============================================================================
// FEATURE MANAGER
// =============================================================================

/**
 * Create a feature manager that loads and renders furniture features.
 * Returns { loadFeatures, renderFeatures } bound to the editor and API.
 * @param {object} editor - MapEditor instance
 * @param {string} apiBaseUrl - e.g. '/beach/config/map-editor'
 * @returns {{ loadFeatures: Function, renderFeatures: Function }}
 */
export function createFeatureManager(editor, apiBaseUrl) {
    let availableFeatures = [];
    let featuresLoaded = false;

    async function loadFeatures() {
        if (featuresLoaded) return;
        try {
            const response = await fetch(`${apiBaseUrl}/features`);
            const result = await response.json();
            if (result.success) {
                availableFeatures = result.features;
                featuresLoaded = true;
            }
        } catch (e) {
            console.warn('Could not load features:', e);
        }
    }

    // Start loading immediately
    loadFeatures();

    async function renderFeatures(selectedFeatures) {
        const container = el('prop-features');
        if (!container) return;

        if (!featuresLoaded) await loadFeatures();

        const features = parseFeatures(selectedFeatures);

        const html = availableFeatures.map(f => {
            const isActive = features.includes(f.code);
            return `<span class="feature-tag ${isActive ? 'active' : ''}" data-code="${f.code}">
                <i class="fas ${f.icon}"></i>${f.name}
            </span>`;
        }).join('');

        container.innerHTML = html;

        // Click handlers for toggling features
        container.querySelectorAll('.feature-tag').forEach(tag => {
            tag.addEventListener('click', async function () {
                const selectedItems = editor.getSelectedItems();
                if (selectedItems.length === 0) return;

                const selectedItem = selectedItems[0];
                const code = this.dataset.code;
                const current = parseFeatures(selectedItem.features);
                const { features: updated, added } = toggleFeature(current, code);

                if (added) this.classList.add('active');
                else this.classList.remove('active');

                const featuresJson = JSON.stringify(updated);
                selectedItem.features = featuresJson;
                await editor.saveFurnitureProperty(selectedItem.id, 'features', featuresJson);
            });
        });
    }

    return { loadFeatures, renderFeatures };
}

// =============================================================================
// DUPLICATE
// =============================================================================

/**
 * Bind duplicate horizontal/vertical buttons.
 * DOM IDs: btn-duplicate-h, btn-duplicate-v, prop-copies, prop-spacing, zone-selector
 * @param {object} editor - MapEditor instance
 */
export function bindDuplicate(editor) {
    async function duplicateFurniture(direction) {
        const selectedItems = editor.getSelectedItems();
        if (selectedItems.length === 0) return;

        const selectedItem = selectedItems[0];
        const count = parseInt(el('prop-copies')?.value) || 1;
        const spacing = parseInt(el('prop-spacing')?.value) || 10;

        try {
            const response = await fetch(`/beach/config/map-editor/furniture/${selectedItem.id}/duplicate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
                body: JSON.stringify({ direction, spacing, count })
            });

            const result = await response.json();
            if (result.success) {
                // Reload zone to show new furniture
                const zoneSelector = el('zone-selector');
                const zoneId = zoneSelector?.value;
                if (zoneId) {
                    const opt = zoneSelector.options[zoneSelector.selectedIndex];
                    await editor.loadZone(zoneId, {
                        width: parseFloat(opt.dataset.width) || 2000,
                        height: parseFloat(opt.dataset.height) || 1000,
                        backgroundColor: opt.dataset.bg || '#FAFAFA'
                    });
                }
                if (window.PuroBeach) window.PuroBeach.showToast(`${result.count} elementos creados`, 'success');
            } else {
                if (window.PuroBeach) window.PuroBeach.showToast(result.error || 'Error al duplicar', 'error');
            }
        } catch (e) {
            console.error('Error duplicating:', e);
            if (window.PuroBeach) window.PuroBeach.showToast('Error al duplicar', 'error');
        }
    }

    el('btn-duplicate-h')?.addEventListener('click', () => duplicateFurniture('horizontal'));
    el('btn-duplicate-v')?.addEventListener('click', () => duplicateFurniture('vertical'));
}

// =============================================================================
// MULTI-SELECTION TOOLBAR
// =============================================================================

/**
 * Bind multi-selection toolbar: alignment, rotation, delete, deselect buttons.
 * DOM IDs: [data-align], btn-rotate-0, btn-rotate-90, btn-delete-multiple,
 *          btn-deselect-all, multi-select-toolbar
 * @param {object} editor - MapEditor instance
 */
export function bindMultiSelectionToolbar(editor) {
    document.querySelectorAll('[data-align]').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            editor.alignSelectedItems(this.dataset.align);
        });
    });

    el('btn-rotate-0')?.addEventListener('click', () => editor.rotateSelectedItems(0));
    el('btn-rotate-90')?.addEventListener('click', () => editor.rotateSelectedItems(90));
    el('btn-delete-multiple')?.addEventListener('click', () => editor.deleteSelectedItems());
    el('btn-deselect-all')?.addEventListener('click', () => editor.deselectAll());
}

// =============================================================================
// EDITOR EVENTS
// =============================================================================

/**
 * Bind standard editor event listeners to DOM elements.
 * @param {object} editor - MapEditor instance
 * @param {object} [options]
 * @param {{ renderFeatures: Function }} [options.featureManager] - Feature manager from createFeatureManager
 * @param {boolean} [options.hasSize=false] - Whether to populate width/height fields
 * @param {boolean} [options.hasColor=false] - Whether to populate color picker fields
 */
export function bindEditorEvents(editor, options = {}) {
    const { featureManager, hasSize = false, hasColor = false } = options;

    editor.on('furnitureChanged', count => {
        const e = el('furniture-count');
        if (e) e.textContent = count;
    });

    editor.on('selectionChanged', selected => {
        if (!selected) return;

        el('prop-x').value = Math.round(selected.position_x);
        el('prop-y').value = Math.round(selected.position_y);
        el('prop-rotation').value = selected.rotation || 0;
        el('prop-capacity').value = selected.capacity || 2;
        el('prop-number').value = selected.number || '';

        if (hasSize) {
            el('prop-width').value = selected.width || 60;
            el('prop-height').value = selected.height || 40;
        }

        if (hasColor) {
            const fillColor = selected.fill_color || selected.typeInfo?.fill_color || '#A0522D';
            el('prop-fill-color').value = fillColor;
            el('prop-fill-color-text').value = fillColor;

            const isDecorative = selected.typeInfo?.is_decorative || selected.is_decorative;
            el('prop-capacity-group').style.display = isDecorative ? 'none' : 'block';
            el('prop-features-group').style.display = isDecorative ? 'none' : 'block';
        }

        if (featureManager) featureManager.renderFeatures(selected.features);
    });

    editor.on('canvasLoaded', info => {
        const e = el('canvas-dimensions');
        if (e) e.textContent = `${info.width} x ${info.height} px`;
    });

    editor.on('zoomChanged', zoom => {
        const e = el('zoom-level');
        if (e) e.textContent = `${Math.round(zoom * 100)}%`;
    });

    editor.on('cursorMove', pos => {
        const e = el('cursor-pos');
        if (e) e.textContent = pos ? `${pos.x}, ${pos.y}` : '-';
    });

    editor.on('itemMoved', data => {
        if (data.x !== undefined) {
            el('prop-x').value = Math.round(data.x);
            el('prop-y').value = Math.round(data.y);
        }
    });

    // Multi-selection toolbar visibility (only relevant when toolbar exists)
    editor.on('multiSelectionChanged', selected => {
        const toolbar = el('multi-select-toolbar');
        if (!toolbar) return;

        if (selected.length > 1) {
            toolbar.classList.remove('d-none');
            toolbar.querySelector('.selection-count').textContent = selected.length;
        } else {
            toolbar.classList.add('d-none');
        }
    });
}

// =============================================================================
// COLOR PICKER SYNC (furniture_manager only)
// =============================================================================

/**
 * Bind color picker input to text input + save on change.
 * @param {object} editor - MapEditor instance
 * @param {string} pickerId - Color input DOM ID
 * @param {string} textId - Text input DOM ID
 * @param {string} property - Editor property name to save
 */
export function bindColorPicker(editor, pickerId, textId, property) {
    const picker = el(pickerId);
    const text = el(textId);
    if (!picker || !text) return;

    picker.addEventListener('input', function () {
        text.value = this.value;
    });
    picker.addEventListener('change', function () {
        text.value = this.value;
        editor.updateSelectedProperty(property, this.value);
    });
}
