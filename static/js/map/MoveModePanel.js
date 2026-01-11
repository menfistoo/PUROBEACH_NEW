/**
 * Move Mode Panel Component
 * Displays the pool of reservations waiting to be assigned during move mode
 */

import { formatDateDisplay, showToast } from './utils.js';

/**
 * Move Mode Panel Class
 * Renders and manages the side panel showing unassigned reservations
 */
export class MoveModePanel {
    constructor(containerId, moveMode) {
        this.container = document.getElementById(containerId);
        this.moveMode = moveMode;

        // Create panel structure if container exists
        if (this.container) {
            this.createPanelStructure();
            this.setupEventListeners();
        } else {
            console.warn(`MoveModePanel: Container #${containerId} not found`);
        }
    }

    /**
     * Create the panel HTML structure
     */
    createPanelStructure() {
        this.container.innerHTML = `
            <div class="move-mode-panel">
                <div class="move-mode-panel-header">
                    <h5>
                        <i class="fas fa-exchange-alt me-2"></i>
                        Reservas sin asignar
                        <span class="badge bg-warning text-dark ms-2" id="moveModePoolCount">0</span>
                    </h5>
                    <button type="button" class="btn btn-sm btn-outline-secondary" id="moveModeExitBtn" title="Salir del modo mover">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div class="move-mode-panel-body" id="moveModePoolList">
                    <div class="move-mode-empty-state">
                        <i class="fas fa-hand-pointer fa-2x text-muted mb-2"></i>
                        <p class="text-muted mb-0">Haz clic en mobiliario ocupado para liberarlo</p>
                    </div>
                </div>

                <div class="move-mode-panel-footer">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <button type="button" class="btn btn-sm btn-outline-secondary" id="moveModeUndoBtn" disabled>
                            <i class="fas fa-undo me-1"></i>Deshacer
                        </button>
                        <small class="text-muted" id="moveModeUndoCount"></small>
                    </div>
                    <div class="move-mode-shortcuts">
                        <small class="text-muted d-block"><kbd>Clic</kbd> Liberar 1 mobiliario</small>
                        <small class="text-muted d-block"><kbd>Ctrl+Clic</kbd> Liberar toda la reserva</small>
                        <small class="text-muted d-block"><kbd>Ctrl+Z</kbd> Deshacer</small>
                    </div>
                </div>

                <div class="move-mode-legend" id="moveModeLegend" style="display: none;">
                    <div class="legend-header">Buscando:</div>
                    <div class="legend-items" id="moveModeLegendItems"></div>
                </div>
            </div>
        `;

        // Cache elements
        this.poolCount = document.getElementById('moveModePoolCount');
        this.poolList = document.getElementById('moveModePoolList');
        this.exitBtn = document.getElementById('moveModeExitBtn');
        this.undoBtn = document.getElementById('moveModeUndoBtn');
        this.undoCount = document.getElementById('moveModeUndoCount');
        this.legend = document.getElementById('moveModeLegend');
        this.legendItems = document.getElementById('moveModeLegendItems');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Exit button
        this.exitBtn?.addEventListener('click', () => {
            this.moveMode.deactivate();
        });

        // Undo button
        this.undoBtn?.addEventListener('click', () => {
            this.moveMode.undo();
        });

        // MoveMode events
        this.moveMode.on('onPoolUpdate', (data) => this.renderPool(data.pool));
        this.moveMode.on('onSelectionChange', (data) => this.updateSelection(data.reservation));
        this.moveMode.on('onFurnitureHighlight', (data) => this.updateLegend(data.preferences));
        this.moveMode.on('onActivate', () => this.show());
        this.moveMode.on('onDeactivate', () => this.hide());
        this.moveMode.on('onUndo', () => this.updateUndoState());
    }

    /**
     * Show the panel
     */
    show() {
        this.container?.classList.add('visible');
        this.updateUndoState();
    }

    /**
     * Hide the panel
     */
    hide() {
        this.container?.classList.remove('visible');
    }

    /**
     * Render the pool of reservations
     * @param {Array} pool - Pool reservations
     */
    renderPool(pool) {
        if (!this.poolList) return;

        // Update count badge
        this.poolCount.textContent = pool.length;

        if (pool.length === 0) {
            this.poolList.innerHTML = `
                <div class="move-mode-empty-state">
                    <i class="fas fa-check-circle fa-2x text-success mb-2"></i>
                    <p class="text-muted mb-0">Todas las reservas asignadas</p>
                </div>
            `;
            return;
        }

        this.poolList.innerHTML = pool.map(res => this.renderReservationCard(res)).join('');

        // Add click handlers to cards
        this.poolList.querySelectorAll('.move-mode-card').forEach(card => {
            card.addEventListener('click', () => {
                const resId = parseInt(card.dataset.reservationId);
                this.moveMode.selectReservation(resId);
            });
        });

        // Add restore handlers
        this.poolList.querySelectorAll('.restore-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const card = btn.closest('.move-mode-card');
                const resId = parseInt(card.dataset.reservationId);
                const res = this.moveMode.pool.find(r => r.reservation_id === resId);

                // Use initialFurniture (what it had when first entering pool)
                if (!res || !res.initialFurniture?.length) {
                    showToast('No hay posición original para restaurar', 'warning');
                    return;
                }

                // Get original furniture IDs (furniture_id is the actual furniture, id is the assignment record)
                const originalIds = res.initialFurniture.map(f => f.furniture_id || f.id);

                // Assign back to original furniture
                const result = await this.moveMode.assignFurniture(resId, originalIds);
                if (result.success) {
                    showToast('Posición original restaurada', 'success');
                }
            });
        });

        this.updateUndoState();
    }

    /**
     * Render a single reservation card
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderReservationCard(res) {
        const isSelected = res.reservation_id === this.moveMode.selectedReservationId;
        const selectedClass = isSelected ? 'selected' : '';
        const progressDots = this.renderProgressDots(res.assignedCount, res.totalNeeded);
        const prefDots = this.renderPreferenceDots(res.preferences?.length || 0);
        const multidayBadge = res.is_multiday
            ? `<span class="badge bg-info ms-1" title="${res.total_days} días">📅${res.total_days}</span>`
            : '';

        // Use initialFurniture (what it had when entering pool) or fall back to original_furniture
        const furnitureSource = res.initialFurniture?.length > 0 ? res.initialFurniture : res.original_furniture;
        const originalFurniture = furnitureSource?.map(f => f.number || f.furniture_number).join(', ') || '-';
        const roomDisplay = res.room_number
            ? `<span class="badge bg-primary me-1"><i class="fas fa-door-open me-1"></i>${res.room_number}</span>`
            : '';

        return `
            <div class="move-mode-card ${selectedClass}" data-reservation-id="${res.reservation_id}">
                <div class="card-header">
                    ${roomDisplay}
                    <span class="customer-name">${res.customer_name}</span>
                    ${multidayBadge}
                </div>
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span><i class="fas fa-users me-1"></i>${res.num_people} personas</span>
                        <span class="preference-dots">${prefDots}</span>
                    </div>
                    <div class="text-muted small">
                        <i class="fas fa-map-marker-alt me-1"></i>Era: ${originalFurniture}
                    </div>
                    <div class="progress-indicator mt-2">
                        ${progressDots}
                        <span class="progress-text">${res.assignedCount} de ${res.totalNeeded}</span>
                    </div>
                </div>
                ${isSelected ? this.renderExpandedContent(res) : ''}
            </div>
        `;
    }

    /**
     * Render expanded content for selected reservation
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderExpandedContent(res) {
        const preferences = res.preferences?.map(p =>
            `<div class="preference-item"><span class="pref-icon">${p.icon || '⭐'}</span> ${p.name}</div>`
        ).join('') || '<span class="text-muted">Sin preferencias</span>';

        const notes = res.notes
            ? `<div class="notes-section"><i class="fas fa-sticky-note me-1"></i>${res.notes}</div>`
            : '';

        const dayAssignments = res.is_multiday && res.day_assignments
            ? this.renderDayAssignments(res)
            : '';

        return `
            <div class="card-expanded">
                <div class="preferences-section">
                    <strong>Preferencias:</strong>
                    ${preferences}
                </div>
                ${notes}
                ${dayAssignments}
                <button type="button" class="btn btn-sm btn-outline-secondary w-100 mt-2 restore-btn">
                    <i class="fas fa-undo me-1"></i>Restaurar posición original
                </button>
            </div>
        `;
    }

    /**
     * Render day assignments for multi-day reservations
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderDayAssignments(res) {
        const days = Object.entries(res.day_assignments || {}).map(([date, furniture]) => {
            const isToday = date === res.target_date;
            const todayBadge = isToday ? ' <span class="badge bg-warning">hoy</span>' : '';
            return `<div class="day-assignment ${isToday ? 'today' : ''}">${formatDateDisplay(date)}${todayBadge}: ${furniture}</div>`;
        }).join('');

        return `
            <div class="days-section mt-2">
                <strong>Días de reserva:</strong>
                ${days}
            </div>
        `;
    }

    /**
     * Render progress dots
     * @param {number} assigned - Number assigned
     * @param {number} total - Total needed
     * @returns {string} HTML string
     */
    renderProgressDots(assigned, total) {
        const dots = [];
        for (let i = 0; i < total; i++) {
            const filled = i < assigned ? 'filled' : '';
            dots.push(`<span class="progress-dot ${filled}"></span>`);
        }
        return dots.join('');
    }

    /**
     * Render preference dots indicator
     * @param {number} count - Preference count
     * @returns {string} HTML string
     */
    renderPreferenceDots(count) {
        if (count === 0) return '';
        const filled = '●'.repeat(Math.min(count, 3));
        const empty = '○'.repeat(Math.max(0, 3 - count));
        return `<span title="${count} preferencias">${filled}${empty}</span>`;
    }

    /**
     * Update selection state
     * @param {Object|null} reservation - Selected reservation or null
     */
    updateSelection(reservation) {
        // Re-render to update selection state
        this.renderPool(this.moveMode.getPool());

        // Show/hide legend
        if (reservation && reservation.preferences?.length > 0) {
            this.legend.style.display = 'block';
        } else {
            this.legend.style.display = 'none';
        }
    }

    /**
     * Update the preference legend
     * @param {Array} preferences - Preferences to display
     */
    updateLegend(preferences) {
        if (!this.legendItems) return;

        if (!preferences || preferences.length === 0) {
            this.legend.style.display = 'none';
            return;
        }

        this.legend.style.display = 'block';
        this.legendItems.innerHTML = preferences.map(p =>
            `<div class="legend-item"><span class="legend-icon">${p.icon || '⭐'}</span> ${p.name}</div>`
        ).join('');
    }

    /**
     * Update undo button state
     */
    updateUndoState() {
        const canUndo = this.moveMode.canUndo();
        const undoCount = this.moveMode.getUndoCount();

        if (this.undoBtn) {
            this.undoBtn.disabled = !canUndo;
        }

        if (this.undoCount) {
            this.undoCount.textContent = canUndo ? `(${undoCount})` : '';
        }
    }
}
