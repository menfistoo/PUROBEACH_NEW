/**
 * ReservationPanel Furniture Mixin
 *
 * Handles furniture display and reassignment functionality:
 * - Rendering furniture section with chips and summary
 * - Entering/exiting reassignment mode
 * - Toggling furniture selection
 * - Saving furniture reassignments
 * - Highlighting furniture on the map
 */

import { getFurnitureIcon, parseDateToYMD, showToast } from './utils.js';

// =============================================================================
// FURNITURE MIXIN
// =============================================================================

/**
 * Mixin that adds furniture display and reassignment functionality
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
                ${f.number || f.furniture_number || `#${f.furniture_id || f.id}`}
            </span>
        `).join('');

        this.furnitureChipsContainer.innerHTML = chipsHtml;

        // Summary
        const totalCapacity = displayFurniture.reduce((sum, f) => sum + (f.capacity || 2), 0);
        this.furnitureSummary.textContent =
            `${displayFurniture.length} ${displayFurniture.length === 1 ? 'item' : 'items'} • Capacidad: ${totalCapacity} personas`;
    }

    // =========================================================================
    // REASSIGNMENT MODE
    // =========================================================================

    /**
     * Enter furniture reassignment mode
     * Sets up UI for selecting new furniture from the map
     */
    enterReassignmentMode() {
        const reservation = this.state.data?.reservation;
        if (!reservation) return;

        // In standalone mode, navigate to map for furniture selection
        if (this.isStandalone()) {
            // Build return URL with current location
            const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
            const mapUrl = `/beach/map?mode=furniture_select&reservation_id=${reservation.id}&date=${this.state.currentDate}&return_url=${returnUrl}`;
            window.location.href = mapUrl;
            return;
        }

        // Get current furniture for this date
        const currentFurniture = (reservation.furniture || []).filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === this.state.currentDate;
        });

        // Set up reassignment state
        this.reassignmentState.originalFurniture = currentFurniture.map(f =>
            f.furniture_id || f.id
        );
        this.reassignmentState.selectedFurniture = []; // Start with empty selection
        this.reassignmentState.maxAllowed = reservation.num_people || 2;

        // Switch mode
        this.state.mode = 'reassignment';
        this.panel.classList.add('reassignment-mode');
        this.backdrop.classList.add('reassignment-mode');

        // Hide view mode, show reassignment mode
        if (this.furnitureViewMode) this.furnitureViewMode.style.display = 'none';
        if (this.furnitureReassignmentMode) this.furnitureReassignmentMode.style.display = 'flex';

        // Render original furniture chips
        this.renderOriginalFurnitureChips(currentFurniture);

        // Update counter and clear new chips
        this.updateReassignmentUI();

        // Show hint toast
        showToast(`Selecciona hasta ${this.reassignmentState.maxAllowed} mobiliarios en el mapa`, 'info');

        // Notify map to enter reassignment mode (for highlighting available furniture)
        if (this.options.onFurnitureReassign) {
            this.options.onFurnitureReassign(
                reservation.id,
                currentFurniture,
                reservation.num_people,
                'enter' // Signal entering mode, not closing
            );
        }
    }

    /**
     * Exit reassignment mode
     * @param {boolean} cancel - Whether to cancel without saving
     */
    exitReassignmentMode(cancel = false) {
        if (this.state.mode !== 'reassignment') return;

        // Switch back to view mode
        this.state.mode = 'view';
        this.panel.classList.remove('reassignment-mode');
        this.backdrop.classList.remove('reassignment-mode');

        // Show view mode, hide reassignment mode
        if (this.furnitureViewMode) this.furnitureViewMode.style.display = 'block';
        if (this.furnitureReassignmentMode) this.furnitureReassignmentMode.style.display = 'none';

        // Clear reassignment state
        this.reassignmentState.selectedFurniture = [];

        // Notify map to exit reassignment mode
        if (this.options.onFurnitureReassign) {
            this.options.onFurnitureReassign(
                this.state.reservationId,
                [],
                0,
                'exit' // Signal exiting mode
            );
        }

        if (cancel) {
            showToast('Cambio de mobiliario cancelado', 'info');
        }
    }

    // =========================================================================
    // FURNITURE SELECTION
    // =========================================================================

    /**
     * Toggle furniture selection (called from map when furniture is clicked)
     * @param {number} furnitureId - The furniture ID to toggle
     * @param {object} furnitureData - Full furniture data {id, number, type_name, capacity}
     * @returns {boolean} Whether the toggle was successful
     */
    toggleFurnitureSelection(furnitureId, furnitureData = null) {
        if (this.state.mode !== 'reassignment') return false;

        const index = this.reassignmentState.selectedFurniture.findIndex(
            f => (f.id || f) === furnitureId
        );

        if (index >= 0) {
            // Remove from selection
            this.reassignmentState.selectedFurniture.splice(index, 1);
        } else {
            // Check max limit
            if (this.reassignmentState.selectedFurniture.length >= this.reassignmentState.maxAllowed) {
                showToast(`Maximo ${this.reassignmentState.maxAllowed} mobiliarios permitidos`, 'warning');
                return false;
            }
            // Add to selection
            const furnitureInfo = furnitureData || { id: furnitureId };
            this.reassignmentState.selectedFurniture.push(furnitureInfo);
        }

        // Update UI
        this.updateReassignmentUI();
        return true;
    }

    /**
     * Check if panel is in reassignment mode
     * @returns {boolean} True if in reassignment mode
     */
    isInReassignmentMode() {
        return this.state.mode === 'reassignment';
    }

    // =========================================================================
    // REASSIGNMENT UI
    // =========================================================================

    /**
     * Update reassignment UI (counter and chips)
     * Shows capacity status and enables/disables save button
     */
    updateReassignmentUI() {
        const selected = this.reassignmentState.selectedFurniture;
        const max = this.reassignmentState.maxAllowed;

        // Calculate total capacity
        const totalCapacity = selected.reduce((sum, f) => sum + (f.capacity || 2), 0);
        const numPeople = this.state.data?.reservation?.num_people || max;

        // Determine capacity status
        let capacityStatus = '';
        let capacityClass = '';
        if (selected.length > 0) {
            if (totalCapacity < numPeople) {
                capacityStatus = ` Warning: Capacidad insuficiente: ${totalCapacity}/${numPeople} personas`;
                capacityClass = 'capacity-insufficient';
            } else if (totalCapacity > numPeople) {
                capacityStatus = ` Info: Capacidad excedente: ${totalCapacity}/${numPeople} personas`;
                capacityClass = 'capacity-excess';
            } else {
                capacityStatus = ` Check: Capacidad correcta: ${totalCapacity}/${numPeople} personas`;
                capacityClass = 'capacity-correct';
            }
        }

        // Update counter with capacity info
        if (this.reassignmentCounter) {
            this.reassignmentCounter.innerHTML = `
                ${selected.length} / ${max} seleccionados
                <span class="${capacityClass}" style="display: block; font-size: 11px; margin-top: 4px;">
                    ${capacityStatus}
                </span>
            `;
        }

        // Update new chips
        if (this.reassignmentNewChips) {
            if (selected.length === 0) {
                this.reassignmentNewChips.innerHTML =
                    '<span class="text-muted" style="font-size: 12px;">Ninguno seleccionado</span>';
            } else {
                const chipsHtml = selected.map(f => `
                    <span class="furniture-chip">
                        <span class="furniture-type-icon">${getFurnitureIcon(f.type_name)}</span>
                        ${f.number || f.furniture_number || `#${f.id}`}
                        <span style="font-size: 10px; opacity: 0.7;">(${f.capacity || 2}p)</span>
                    </span>
                `).join('');
                this.reassignmentNewChips.innerHTML = chipsHtml;
            }
        }

        // Enable/disable save button based on selection and capacity
        if (this.reassignmentSaveBtn) {
            const hasSelection = selected.length > 0;
            const hasInsufficientCapacity = totalCapacity < numPeople;

            // Disable button if no selection OR insufficient capacity
            this.reassignmentSaveBtn.disabled = !hasSelection || hasInsufficientCapacity;

            // Update button text to indicate why it's disabled
            if (hasInsufficientCapacity) {
                const icon = this.reassignmentSaveBtn.querySelector('i');
                const iconHtml = icon ? `<i class="${icon.className}"></i> ` : '';
                this.reassignmentSaveBtn.innerHTML = `${iconHtml}Capacidad insuficiente`;
            } else {
                this.reassignmentSaveBtn.innerHTML = '<i class="fas fa-check"></i> Guardar cambios';
            }
        }
    }

    /**
     * Render original furniture chips (dimmed, for reference)
     * @param {Array} furniture - Array of furniture objects
     */
    renderOriginalFurnitureChips(furniture) {
        if (!this.reassignmentOriginalChips) return;

        if (furniture.length === 0) {
            this.reassignmentOriginalChips.innerHTML =
                '<span class="text-muted" style="font-size: 12px;">Sin mobiliario</span>';
            return;
        }

        const chipsHtml = furniture.map(f => `
            <span class="furniture-chip">
                <span class="furniture-type-icon">${getFurnitureIcon(f.type_name || f.furniture_type)}</span>
                ${f.number || f.furniture_number || `#${f.furniture_id || f.id}`}
            </span>
        `).join('');

        this.reassignmentOriginalChips.innerHTML = chipsHtml;
    }

    // =========================================================================
    // SAVE REASSIGNMENT
    // =========================================================================

    /**
     * Save furniture reassignment
     * Sends API request to update furniture assignments for the reservation
     */
    async saveReassignment() {
        if (this.state.mode !== 'reassignment') return;
        if (this.reassignmentState.selectedFurniture.length === 0) {
            showToast('Selecciona al menos un mobiliario', 'warning');
            return;
        }

        // Show loading state
        if (this.reassignmentSaveBtn) {
            this.reassignmentSaveBtn.disabled = true;
            this.reassignmentSaveBtn.innerHTML =
                '<span class="spinner-border spinner-border-sm"></span> Guardando...';
        }

        try {
            const furnitureIds = this.reassignmentState.selectedFurniture.map(
                f => f.id || f.furniture_id || f
            );

            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/reassign-furniture`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({
                        furniture_ids: furnitureIds,
                        date: this.state.currentDate
                    })
                }
            );

            const result = await response.json();

            if (result.success) {
                // Exit reassignment mode
                this.exitReassignmentMode(false);

                // Reload reservation data to get updated furniture
                await this.loadReservation(this.state.reservationId, this.state.currentDate);

                // Show success message
                let message = 'Mobiliario actualizado exitosamente';

                // Show capacity warning if present
                if (result.warning) {
                    showToast(result.warning, 'warning');
                    // Delay success message slightly so both toasts are visible
                    setTimeout(() => {
                        showToast(message, 'success');
                    }, 100);
                } else {
                    showToast(message, 'success');
                }

                // Notify map to refresh
                if (this.options.onSave) {
                    this.options.onSave(this.state.reservationId, { furniture_changed: true });
                }
            } else {
                // Handle error response (e.g., insufficient capacity)
                throw new Error(result.error || 'Error al guardar');
            }

        } catch (error) {
            console.error('Reassignment save error:', error);
            // Show error with more details if available
            const errorMsg = error.message || 'Error al actualizar mobiliario';
            showToast(errorMsg, 'error');
        } finally {
            // Reset button state
            if (this.reassignmentSaveBtn) {
                this.reassignmentSaveBtn.disabled = false;
                this.reassignmentSaveBtn.innerHTML =
                    '<i class="fas fa-check"></i> Guardar cambios';
            }
        }
    }

    // =========================================================================
    // MAP HIGHLIGHTING
    // =========================================================================

    /**
     * Highlight reservation's furniture on the map with editing style
     * Adds 'furniture-editing' class to furniture elements
     */
    highlightReservationFurniture() {
        if (!this.state.data?.furniture) return;

        // Get furniture IDs for this reservation
        const furnitureIds = this.state.data.furniture.map(f => f.id || f.furniture_id);

        // Find and highlight each furniture element on the map
        furnitureIds.forEach(id => {
            const furnitureEl = document.querySelector(`[data-furniture-id="${id}"]`);
            if (furnitureEl) {
                furnitureEl.classList.add('furniture-editing');
            }
        });
    }

    /**
     * Remove highlight from reservation's furniture
     * Removes 'furniture-editing' class from all furniture elements
     */
    unhighlightReservationFurniture() {
        // Remove highlight from all furniture elements
        const highlightedElements = document.querySelectorAll('.furniture-editing');
        highlightedElements.forEach(el => {
            el.classList.remove('furniture-editing');
        });
    }

    // =========================================================================
    // LEGACY SUPPORT
    // =========================================================================

    /**
     * Legacy method for backwards compatibility
     * @deprecated Use enterReassignmentMode() instead
     */
    triggerFurnitureReassign() {
        this.enterReassignmentMode();
    }
};
