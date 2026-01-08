/**
 * Panel Lifecycle Mixin
 *
 * Handles the panel's lifecycle operations:
 * - Opening and closing the panel
 * - Loading reservation data from API
 * - Rendering content orchestration
 * - Collapse/expand functionality
 * - Error display
 */

import { formatDate } from './utils.js';

// =============================================================================
// PANEL LIFECYCLE MIXIN
// =============================================================================

/**
 * Mixin that adds lifecycle management methods to a panel class.
 * Handles opening, closing, loading data, and rendering orchestration.
 *
 * @param {class} Base - The base class to extend
 * @returns {class} Extended class with lifecycle methods
 */
export const PanelLifecycleMixin = (Base) => class extends Base {

    // =========================================================================
    // OPEN / CLOSE
    // =========================================================================

    /**
     * Open the panel with reservation data
     * @param {number} reservationId - The reservation ID to load
     * @param {string} date - The current date (YYYY-MM-DD)
     * @param {string} mode - 'view' or 'edit'
     */
    async open(reservationId, date, mode = 'view') {
        if (!this.panel) {
            console.error('ReservationPanel: Panel element not found');
            return;
        }

        // Set state
        this.state.reservationId = reservationId;
        this.state.currentDate = date;
        this.state.mode = mode;
        this.state.isOpen = true;
        this.state.isDirty = false;
        this.state.numPeopleManuallyEdited = false;  // Reset flag when opening new reservation

        // Show loading state
        this.showLoading(true);

        // Show panel and backdrop
        this.backdrop.classList.add('show');
        this.panel.classList.add('open');

        // Handle standalone vs map context
        if (this.isStandalone()) {
            this.panel.classList.add('standalone');
            this.backdrop.classList.add('standalone');
            // Don't lock body scroll in standalone mode - page should scroll normally
        } else {
            // Only lock body scroll in map context (overlay mode)
            document.body.style.overflow = 'hidden';
        }

        // Adjust map canvas if on tablet/desktop (only in map context)
        if (!this.isStandalone()) {
            const mapWrapper = document.querySelector('.map-canvas-wrapper');
            if (mapWrapper && window.innerWidth >= 768) {
                mapWrapper.classList.add('panel-open');
            }
        }

        // In standalone mode, fetch states if not already loaded
        if (this.isStandalone() && this.states.length === 0) {
            await this.fetchStates();
        }

        // Load reservation data
        await this.loadReservation(reservationId, date);

        // Apply mode
        if (mode === 'edit') {
            this.enterEditMode();
        } else {
            this.exitEditMode(false);
        }
    }

    /**
     * Close the panel
     */
    close() {
        if (!this.state.isOpen) return;

        // Check for unsaved changes
        if (this.state.mode === 'edit' && this.state.isDirty) {
            if (!confirm('Tienes cambios sin guardar. ¿Seguro que quieres cerrar?')) {
                return;
            }
        }

        // Reset state
        this.state.isOpen = false;
        this.state.isCollapsed = false;
        this.state.mode = 'view';
        this.state.isDirty = false;

        // Hide panel and backdrop
        this.backdrop.classList.remove('show');
        this.panel.classList.remove('open');
        this.panel.classList.remove('collapsed');
        this.panel.classList.remove('edit-mode');
        this.panel.classList.remove('standalone');
        this.backdrop.classList.remove('standalone');
        this.panel.style.transform = '';
        document.body.style.overflow = '';

        // Remove map canvas adjustment (only in map context)
        if (!this.isStandalone()) {
            const mapWrapper = document.querySelector('.map-canvas-wrapper');
            if (mapWrapper) {
                mapWrapper.classList.remove('panel-open');
            }
        }

        // Hide customer search
        this.hideCustomerSearch();

        // Callback
        if (this.options.onClose) {
            this.options.onClose();
        }
    }

    // =========================================================================
    // COLLAPSE / EXPAND
    // =========================================================================

    /**
     * Toggle collapsed state
     */
    toggleCollapse() {
        if (!this.state.isOpen) return;

        this.state.isCollapsed = !this.state.isCollapsed;

        // Get map canvas wrapper
        const mapWrapper = document.querySelector('.map-canvas-wrapper');

        if (this.state.isCollapsed) {
            this.panel.classList.add('collapsed');

            // Hide backdrop - allow map interaction
            if (this.backdrop) {
                this.backdrop.classList.remove('show');
            }

            // Remove map adjustment - let map fill full width
            if (mapWrapper) {
                mapWrapper.classList.remove('panel-open');
            }

            // Update button label
            if (this.toggleBtn) {
                this.toggleBtn.setAttribute('aria-label', 'Expandir panel');
                this.toggleBtn.setAttribute('title', 'Expandir');
            }
        } else {
            this.panel.classList.remove('collapsed');

            // Show backdrop again
            if (this.backdrop) {
                this.backdrop.classList.add('show');
            }

            // Add map adjustment - make room for panel
            if (mapWrapper) {
                mapWrapper.classList.add('panel-open');
            }

            // Update button label
            if (this.toggleBtn) {
                this.toggleBtn.setAttribute('aria-label', 'Colapsar panel');
                this.toggleBtn.setAttribute('title', 'Colapsar');
            }
        }
    }

    // =========================================================================
    // DATA LOADING
    // =========================================================================

    /**
     * Load reservation data from API
     * @param {number} reservationId - The reservation ID to load
     * @param {string} date - The date for the reservation details
     */
    async loadReservation(reservationId, date) {
        try {
            // Use the dedicated panel endpoint for full reservation + customer data
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${reservationId}/details?date=${date}`
            );

            if (!response.ok) {
                throw new Error('Error al cargar la reserva');
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Reserva no encontrada');
            }

            this.state.data = result;
            this.renderContent(result);
            this.showLoading(false);

        } catch (error) {
            console.error('Error loading reservation:', error);
            this.showError(error.message);
        }
    }

    // =========================================================================
    // CONTENT RENDERING
    // =========================================================================

    /**
     * Render all panel content
     * @param {Object} data - The reservation data from API
     */
    renderContent(data) {
        const res = data.reservation;
        const customer = data.customer;

        // Header - ticket number and date
        this.ticketEl.textContent = `Reserva #${res.ticket_number || res.id}`;
        this.dateEl.textContent = formatDate(res.reservation_date || res.start_date);

        // View more link
        if (this.viewMoreLink) {
            this.viewMoreLink.href = `/beach/reservations/${res.id}`;
        }

        // Render sections
        this.renderCustomerSection(customer);
        this.renderPreferencesSection(customer);
        this.renderStateSection(res);
        this.renderFurnitureSection(res);
        this.renderDetailsSection(res);
        this.renderPricingSection(res);
        this.renderPaymentSection(res);

        // Load state history (async, non-blocking)
        this.loadStateHistory(res.id);
    }

    // =========================================================================
    // ERROR HANDLING
    // =========================================================================

    /**
     * Show error state in panel
     * @param {string} message - Error message to display
     */
    showError(message) {
        this.showLoading(false);

        if (this.contentEl) {
            this.contentEl.innerHTML = `
                <div class="text-center text-danger py-4">
                    <i class="fas fa-exclamation-circle fa-3x mb-3"></i>
                    <p>${message}</p>
                    <button class="btn btn-outline-primary mt-2" onclick="document.getElementById('reservationPanel').__panel?.close()">
                        Cerrar
                    </button>
                </div>
            `;
            this.contentEl.style.display = 'block';
        }
    }
};
