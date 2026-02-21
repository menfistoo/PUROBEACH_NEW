/**
 * ConflictResolutionModal - Modal for handling multi-day reservation conflicts
 *
 * Displays conflicts when furniture is not available for some dates in a
 * multi-day reservation. Allows users to either:
 * - Navigate to the map to select alternative furniture for each day
 * - Remove problematic days from the reservation
 *
 * Usage:
 *   const modal = new ConflictResolutionModal({
 *       onNavigateToDay: (date, conflicts) => { ... },
 *       onRetry: (furnitureByDate) => { ... },
 *       onCancel: () => { ... }
 *   });
 *   modal.show(conflicts, selectedDates, originalFurniture);
 */
class ConflictResolutionModal {
    constructor(options = {}) {
        this.options = {
            onNavigateToDay: null,  // (date, conflicts) => void
            onRetry: null,          // (furnitureByDate) => void
            onCancel: null,         // () => void
            onRemoveDate: null,     // (date) => void - notify parent when date is removed
            ...options
        };

        // State
        this.state = {
            isOpen: false,
            conflicts: [],           // [{furniture_id, date, ticket_number, customer_name}]
            selectedDates: [],       // All dates in the reservation
            furnitureByDate: {},     // {date: [furniture_ids]} - per-day selections
            originalFurniture: [],   // Initial furniture selection
            resolvedDates: new Set() // Dates that have alternative furniture selected
        };

        this.buildModal();
        this.bindEvents();
    }

    /**
     * Build the modal DOM structure
     */
    buildModal() {
        this.modal = document.createElement('div');
        this.modal.className = 'conflict-modal';
        this.modal.innerHTML = `
            <div class="conflict-modal-backdrop"></div>
            <div class="conflict-modal-content">
                <div class="conflict-modal-header">
                    <h3>
                        <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                        Conflictos de Disponibilidad
                    </h3>
                    <button type="button" class="conflict-modal-close" aria-label="Cerrar">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="conflict-modal-body">
                    <p class="conflict-intro">
                        El mobiliario seleccionado no esta disponible para algunas fechas.
                        Puedes seleccionar mobiliario alternativo o quitar los dias problematicos.
                    </p>
                    <div class="conflict-list"></div>
                    <div class="conflict-summary"></div>
                </div>
                <div class="conflict-modal-footer">
                    <button type="button" class="btn btn-outline-secondary conflict-cancel-btn">
                        Cancelar
                    </button>
                    <button type="button" class="btn btn-primary conflict-retry-btn" disabled>
                        <i class="fas fa-check me-1"></i>
                        Reintentar con Cambios
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(this.modal);

        // Cache DOM references
        this.backdrop = this.modal.querySelector('.conflict-modal-backdrop');
        this.closeBtn = this.modal.querySelector('.conflict-modal-close');
        this.cancelBtn = this.modal.querySelector('.conflict-cancel-btn');
        this.retryBtn = this.modal.querySelector('.conflict-retry-btn');
        this.listEl = this.modal.querySelector('.conflict-list');
        this.summaryEl = this.modal.querySelector('.conflict-summary');
    }

    /**
     * Bind event handlers
     */
    bindEvents() {
        this.backdrop.addEventListener('click', () => this.close());
        this.closeBtn.addEventListener('click', () => this.close());
        this.cancelBtn.addEventListener('click', () => this.close());

        this.retryBtn.addEventListener('click', () => {
            if (this.options.onRetry) {
                this.options.onRetry(this.state.furnitureByDate);
            }
            this.close();
        });

        // Event delegation for dynamic buttons
        this.listEl.addEventListener('click', (e) => {
            const navBtn = e.target.closest('.navigate-to-day-btn');
            const removeBtn = e.target.closest('.remove-day-btn');

            if (navBtn) {
                const date = navBtn.dataset.date;
                const dateConflicts = this.getConflictsForDate(date);
                if (this.options.onNavigateToDay) {
                    this.options.onNavigateToDay(date, dateConflicts);
                }
                this.minimize();
            }

            if (removeBtn) {
                const date = removeBtn.dataset.date;
                this.removeDate(date);
            }
        });

        // Listen for alternative selection from map
        document.addEventListener('conflictResolution:alternativeSelected', (e) => {
            const { date, furnitureIds } = e.detail;
            this.updateDateSelection(date, furnitureIds);
        });

        // Listen for cancellation from map (when user clicks "Cancelar" in selection bar)
        document.addEventListener('conflictResolution:cancelled', () => {
            // Show the modal again
            this.modal.classList.remove('minimized');
            this.modal.classList.add('open');
            this.modal.style.removeProperty('display');
            this.modal.style.setProperty('display', 'flex', 'important');
            this.state.isOpen = true;
        });
    }

    /**
     * Show the modal with conflict data
     * @param {Array} conflicts - Array of conflict objects from API
     * @param {Array} selectedDates - All dates in the reservation
     * @param {Array} originalFurniture - Initial furniture selection (IDs)
     */
    show(conflicts, selectedDates, originalFurniture) {
        this.state.conflicts = conflicts;
        this.state.selectedDates = [...selectedDates];
        this.state.originalFurniture = [...originalFurniture];
        this.state.resolvedDates = new Set();

        // Initialize furniture by date with original selection
        this.state.furnitureByDate = {};
        selectedDates.forEach(date => {
            this.state.furnitureByDate[date] = [...originalFurniture];
        });

        this.renderConflicts();
        this.updateSummary();
        this.updateRetryButton();

        this.modal.classList.remove('minimized');
        this.modal.classList.add('open');
        this.modal.style.display = 'flex';  // Force display
        this.state.isOpen = true;
    }

    /**
     * Close the modal
     */
    close() {
        this.modal.classList.remove('open');
        this.modal.classList.remove('minimized');
        this.modal.style.display = 'none';  // Reset inline style
        this.state.isOpen = false;

        if (this.options.onCancel) {
            this.options.onCancel();
        }
    }

    /**
     * Minimize the modal (when navigating to map)
     */
    minimize() {
        this.modal.classList.add('minimized');
        this.modal.style.display = 'none';  // Hide when minimized
    }

    /**
     * Restore the modal from minimized state
     */
    restore() {
        this.modal.classList.remove('minimized');
    }

    /**
     * Render the conflict list grouped by date
     */
    renderConflicts() {
        // Group conflicts by date
        const conflictsByDate = {};
        this.state.conflicts.forEach(c => {
            if (!conflictsByDate[c.date]) conflictsByDate[c.date] = [];
            conflictsByDate[c.date].push(c);
        });

        // Only show dates that are still selected
        const activeDates = Object.keys(conflictsByDate).filter(
            date => this.state.selectedDates.includes(date)
        );

        if (activeDates.length === 0) {
            this.listEl.innerHTML = `
                <div class="conflict-empty">
                    <i class="fas fa-check-circle text-success"></i>
                    <p>Todos los conflictos han sido resueltos.</p>
                </div>
            `;
            return;
        }

        this.listEl.innerHTML = activeDates.map(date => {
            const dateConflicts = conflictsByDate[date];
            const formattedDate = this.formatDate(date);
            const isResolved = this.state.resolvedDates.has(date);
            const canRemove = this.state.selectedDates.length > 1;

            return `
                <div class="conflict-date-group ${isResolved ? 'resolved' : ''}" data-date="${date}">
                    <div class="conflict-date-header">
                        <span class="conflict-date">${formattedDate}</span>
                        ${isResolved
                    ? '<span class="badge bg-success"><i class="fas fa-check me-1"></i>Alternativa seleccionada</span>'
                    : '<span class="badge bg-warning text-dark"><i class="fas fa-exclamation me-1"></i>Requiere accion</span>'
                }
                    </div>
                    <div class="conflict-items">
                        ${dateConflicts.map(c => `
                            <div class="conflict-item">
                                <span class="conflict-furniture">
                                    <i class="fas fa-chair me-1"></i>
                                    ${c.furniture_number || 'Mobiliario #' + c.furniture_id}
                                </span>
                                <span class="conflict-blocker">
                                    Ocupado por: ${c.customer_name} (${c.ticket_number})
                                </span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="conflict-actions">
                        <button type="button" class="btn btn-sm btn-outline-primary navigate-to-day-btn"
                                data-date="${date}">
                            <i class="fas fa-map-marker-alt me-1"></i>
                            Ir al Mapa
                        </button>
                        ${canRemove ? `
                            <button type="button" class="btn btn-sm btn-outline-danger remove-day-btn"
                                    data-date="${date}">
                                <i class="fas fa-trash me-1"></i>
                                Quitar Dia
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Update the summary section
     */
    updateSummary() {
        const totalDates = this.state.selectedDates.length;
        const conflictDates = this.getUnresolvedConflictDates().length;
        const resolvedDates = this.state.resolvedDates.size;

        if (conflictDates === 0) {
            this.summaryEl.innerHTML = `
                <div class="conflict-summary-success">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    <span>Listo para reintentar con ${totalDates} dia${totalDates !== 1 ? 's' : ''}</span>
                </div>
            `;
        } else {
            this.summaryEl.innerHTML = `
                <div class="conflict-summary-pending">
                    <i class="fas fa-info-circle text-warning me-2"></i>
                    <span>${conflictDates} dia${conflictDates !== 1 ? 's' : ''} pendiente${conflictDates !== 1 ? 's' : ''} de resolver</span>
                </div>
            `;
        }
    }

    /**
     * Update retry button state
     */
    updateRetryButton() {
        const unresolvedDates = this.getUnresolvedConflictDates();
        const canRetry = unresolvedDates.length === 0 && this.state.selectedDates.length > 0;

        this.retryBtn.disabled = !canRetry;
    }

    /**
     * Get dates with unresolved conflicts
     */
    getUnresolvedConflictDates() {
        const conflictDates = new Set(this.state.conflicts.map(c => c.date));
        return this.state.selectedDates.filter(
            date => conflictDates.has(date) && !this.state.resolvedDates.has(date)
        );
    }

    /**
     * Get conflicts for a specific date
     */
    getConflictsForDate(date) {
        return this.state.conflicts.filter(c => c.date === date);
    }

    /**
     * Check if a date has alternative furniture selected
     */
    hasAlternativeSelection(date) {
        return this.state.resolvedDates.has(date);
    }

    /**
     * Update furniture selection for a specific date
     * Called when user selects alternative furniture from the map
     */
    updateDateSelection(date, furnitureIds) {
        // Update state
        this.state.furnitureByDate[date] = [...furnitureIds]; // Copy array
        this.state.resolvedDates.add(date);

        // Re-render UI
        this.renderConflicts();
        this.updateSummary();
        this.updateRetryButton();

        // Force modal to be visible - remove ALL hiding states and force display
        this.modal.classList.remove('minimized');
        this.modal.classList.add('open');

        // Clear any inline display:none and force flex with !important
        this.modal.style.removeProperty('display');
        this.modal.style.setProperty('display', 'flex', 'important');

        this.state.isOpen = true;

    }

    /**
     * Remove a date from the reservation
     */
    removeDate(date) {
        // Remove from selected dates
        this.state.selectedDates = this.state.selectedDates.filter(d => d !== date);

        // Remove from furniture map
        delete this.state.furnitureByDate[date];

        // Remove from resolved set
        this.state.resolvedDates.delete(date);

        // Notify parent (to update DatePicker)
        if (this.options.onRemoveDate) {
            this.options.onRemoveDate(date);
        }

        // Check if we still have dates
        if (this.state.selectedDates.length === 0) {
            this.close();
            return;
        }

        this.renderConflicts();
        this.updateSummary();
        this.updateRetryButton();
    }

    /**
     * Format date for display
     */
    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr + 'T12:00:00');
        const options = { weekday: 'short', day: 'numeric', month: 'short' };
        return date.toLocaleDateString('es-ES', options);
    }

    /**
     * Check if modal is open
     */
    isOpen() {
        return this.state.isOpen;
    }

    /**
     * Get the current furniture by date map
     */
    getFurnitureByDate() {
        return { ...this.state.furnitureByDate };
    }

    /**
     * Get remaining selected dates
     */
    getSelectedDates() {
        return [...this.state.selectedDates];
    }

    /**
     * Destroy the modal
     */
    destroy() {
        this.modal.remove();
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConflictResolutionModal;
}
