/**
 * ReservationPanel Furniture Mixin
 *
 * Handles furniture display functionality:
 * - Rendering furniture section with chips and summary
 * - Entering move mode from this reservation
 * - Highlighting furniture on the map
 * - Furniture lock toggle
 */

import { escapeHtml, getFurnitureIcon, parseDateToYMD, showToast } from './utils.js';

// =============================================================================
// FURNITURE MIXIN
// =============================================================================

/**
 * Mixin that adds furniture display functionality
 * @param {class} Base - The base class to extend
 * @returns {class} Extended class with furniture methods
 */
export const FurnitureMixin = (Base) => class extends Base {

    // =========================================================================
    // FURNITURE RENDERING
    // =========================================================================

    /**
     * Render the furniture section with chips showing assigned furniture
     * @param {object} reservation - Reservation data containing furniture array
     */
    renderFurnitureSection(reservation) {
        const furniture = reservation.furniture || [];
        const currentDate = this.state.currentDate;

        // Filter furniture for current date (if assignment_date exists) or show all
        let displayFurniture = furniture;
        if (furniture.length > 0 && furniture[0].assignment_date) {
            displayFurniture = furniture.filter(f => {
                // Parse any date format to YYYY-MM-DD for comparison
                const assignDate = parseDateToYMD(f.assignment_date);
                return assignDate === currentDate;
            });
        }

        if (displayFurniture.length === 0) {
            this.furnitureChipsContainer.innerHTML =
                '<span class="text-muted">Sin mobiliario asignado</span>';
            this.furnitureSummary.textContent = '';
            return;
        }

        const chipsHtml = displayFurniture.map(f => `
            <span class="furniture-chip">
                <span class="furniture-type-icon">${getFurnitureIcon(f.type_name || f.furniture_type)}</span>
                ${escapeHtml(f.number || f.furniture_number || `#${f.furniture_id || f.id}`)}
            </span>
        `).join('');

        this.furnitureChipsContainer.innerHTML = chipsHtml;

        // Summary
        const totalCapacity = displayFurniture.reduce((sum, f) => sum + (f.capacity || 2), 0);
        this.furnitureSummary.textContent =
            `${displayFurniture.length} ${displayFurniture.length === 1 ? 'item' : 'items'} • Capacidad: ${totalCapacity} personas`;

        // Render lock state
        this.renderLockState(reservation.is_furniture_locked || false);
    }

    // =========================================================================
    // MOVE MODE
    // =========================================================================

    /**
     * Enter move mode from this reservation
     * Closes the panel and activates global move mode with this reservation
     */
    async enterMoveMode() {
        const reservation = this.state.data?.reservation;
        if (!reservation) return;

        // Check if window.moveMode is available
        if (!window.moveMode) {
            showToast('Modo mover no disponible', 'error');
            return;
        }

        // Get current furniture IDs for this date
        const currentFurniture = (reservation.furniture || []).filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === this.state.currentDate;
        });

        const furnitureIds = currentFurniture.map(f => f.furniture_id || f.id);

        // Close the panel first
        this.close();

        // Activate move mode
        window.moveMode.activate(this.state.currentDate);

        // Unassign furniture from this reservation to add it to the pool
        // Pass the original furniture array so we can track what needs to be restored
        if (furnitureIds.length > 0) {
            await window.moveMode.unassignFurniture(reservation.id, furnitureIds, false, currentFurniture);
        } else {
            // No furniture assigned, just load the reservation to pool
            await window.moveMode.loadReservationToPool(reservation.id);
        }

        // Update toolbar button state
        const moveModeBtn = document.getElementById('btn-move-mode');
        if (moveModeBtn) {
            moveModeBtn.classList.add('active');
        }
        document.querySelector('.beach-map-container')?.classList.add('move-mode-active');

        showToast('Modo mover activado - selecciona nuevo mobiliario', 'info');
    }

    // =========================================================================
    // MAP HIGHLIGHTING
    // =========================================================================

    /**
     * Highlight reservation's furniture on the map with gold pulsing glow
     * Adds 'highlighted' class to furniture elements for the current date
     */
    highlightReservationFurniture() {
        const furniture = this.state.data?.reservation?.furniture;
        if (!furniture || furniture.length === 0) return;

        const currentDate = this.state.currentDate;

        // Filter furniture for current date
        const todayFurniture = furniture.filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === currentDate;
        });

        // Dispatch event so the map can highlight during its render cycle
        const furnitureIds = todayFurniture.map(f => f.furniture_id || f.id);
        document.dispatchEvent(new CustomEvent('reservation:highlightFurniture', {
            detail: { furnitureIds }
        }));
    }

    /**
     * Remove highlight from reservation's furniture
     */
    unhighlightReservationFurniture() {
        document.dispatchEvent(new CustomEvent('reservation:clearHighlight'));
    }

    // =========================================================================
    // FURNITURE LOCK
    // =========================================================================

    /**
     * Initialize furniture lock toggle
     */
    initFurnitureLock() {
        this.lockBtn = document.getElementById('toggleFurnitureLock');
        if (this.lockBtn) {
            this.lockBtn.addEventListener('click', () => this.toggleFurnitureLock());
        }
    }

    /**
     * Render the lock button state
     * @param {boolean} isLocked - Whether furniture is locked
     */
    renderLockState(isLocked) {
        if (!this.lockBtn) return;

        const icon = this.lockBtn.querySelector('i');
        if (isLocked) {
            this.lockBtn.classList.add('locked');
            this.lockBtn.dataset.locked = 'true';
            this.lockBtn.title = 'Desbloquear mobiliario';
            this.lockBtn.setAttribute('aria-label', 'Desbloquear mobiliario');
            icon.classList.remove('fa-lock-open');
            icon.classList.add('fa-lock');
        } else {
            this.lockBtn.classList.remove('locked');
            this.lockBtn.dataset.locked = 'false';
            this.lockBtn.title = 'Bloquear mobiliario';
            this.lockBtn.setAttribute('aria-label', 'Bloquear mobiliario');
            icon.classList.remove('fa-lock');
            icon.classList.add('fa-lock-open');
        }

        // Disable move mode button when locked
        const moveModeBtn = document.getElementById('panelMoveModeBtn');
        if (moveModeBtn) {
            moveModeBtn.disabled = isLocked;
            moveModeBtn.title = isLocked ? 'Mobiliario bloqueado' : 'Modo Mover';
        }
    }

    /**
     * Toggle furniture lock via API
     */
    async toggleFurnitureLock() {
        const reservation = this.state.data?.reservation;
        if (!reservation) return;

        const currentLocked = this.lockBtn.dataset.locked === 'true';
        const newLocked = !currentLocked;

        // Disable button during request
        this.lockBtn.disabled = true;

        try {
            const response = await fetch(
                `/beach/api/map/reservations/${reservation.id}/toggle-lock`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ locked: newLocked })
                }
            );

            const result = await response.json();

            if (result.success) {
                this.renderLockState(result.is_furniture_locked);
                // Update local state
                if (this.state.data.reservation) {
                    this.state.data.reservation.is_furniture_locked = result.is_furniture_locked;
                }
                showToast(
                    result.is_furniture_locked
                        ? 'Mobiliario bloqueado'
                        : 'Mobiliario desbloqueado',
                    'success'
                );
            } else {
                showToast(result.error || 'Error al cambiar bloqueo', 'error');
            }
        } catch (error) {
            console.error('Error toggling lock:', error);
            showToast('Error al cambiar bloqueo', 'error');
        } finally {
            this.lockBtn.disabled = false;
        }
    }

    /**
     * Get CSRF token from meta tag
     */
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }
};
