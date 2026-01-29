/**
 * Edit Mode Mixin for ReservationPanel
 *
 * Handles switching between view and edit modes, including:
 * - toggleEditMode() - Switch between modes
 * - enterEditMode() - Activate edit mode with UI changes
 * - exitEditMode() - Return to view mode with optional discard confirmation
 *
 * Dependencies (provided by other mixins):
 * - highlightReservationFurniture() - From furniture mixin
 * - unhighlightReservationFurniture() - From furniture mixin
 * - enterPreferencesEditMode() - From preferences mixin
 * - exitPreferencesEditMode() - From preferences mixin
 * - enterPricingEditMode() - From pricing mixin
 * - exitPricingEditMode() - From pricing mixin
 * - hideCustomerSearch() - From customer mixin
 */

/**
 * Mixin that adds edit mode functionality to ReservationPanel
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with edit mode methods
 */
export const EditModeMixin = (Base) => class extends Base {

    /**
     * Toggle between view and edit modes
     */
    toggleEditMode() {
        if (this.state.mode === 'view') {
            this.enterEditMode();
        } else {
            this.exitEditMode(false);
        }
    }

    /**
     * Enter edit mode
     * - Sets mode to 'edit'
     * - Adds 'edit-mode' class to panel
     * - Updates edit button icon to eye (view mode indicator)
     * - Highlights reservation furniture on map
     * - Shows edit fields, hides view fields
     * - Pre-fills edit fields with current values
     * - Stores original data for dirty checking
     */
    async enterEditMode() {
        this.state.mode = 'edit';
        this.panel.classList.add('edit-mode');

        // Update edit button icon to indicate we're in edit mode
        if (this.editIcon) {
            this.editIcon.className = 'fas fa-eye';
        }

        // Highlight furniture on map
        this.highlightReservationFurniture();

        // Show edit fields, hide view fields for details section
        if (this.detailsViewMode) this.detailsViewMode.style.display = 'none';
        if (this.detailsEditMode) this.detailsEditMode.style.display = 'grid';

        // Show pricing edit mode, hide view mode
        if (this.pricingViewMode) this.pricingViewMode.style.display = 'none';
        if (this.pricingEditMode) this.pricingEditMode.style.display = 'block';

        // Show payment edit mode, hide view mode
        if (this.paymentViewMode) this.paymentViewMode.style.display = 'none';
        if (this.paymentEditMode) this.paymentEditMode.style.display = 'grid';

        // Pre-fill edit fields with current values (only if not manually edited)
        if (this.state.data) {
            const data = this.state.data;
            // Pre-fill date
            if (this.editReservationDate) {
                this.editReservationDate.value = data.reservation?.reservation_date ||
                    data.reservation?.start_date ||
                    this.state.currentDate || '';
                // Set minimum date to today to prevent past dates
                const today = new Date().toISOString().split('T')[0];
                this.editReservationDate.min = today;
            }
            if (this.editNumPeople && !this.state.numPeopleManuallyEdited) {
                this.editNumPeople.value = data.reservation?.num_people || 1;
            }
            if (this.editNotes) {
                this.editNotes.value = data.reservation?.notes || '';
            }
            // Pre-fill payment fields
            if (this.editPaymentTicket) {
                this.editPaymentTicket.value = data.reservation?.payment_ticket_number || '';
            }
            if (this.editPaymentMethod) {
                this.editPaymentMethod.value = data.reservation?.payment_method || '';
            }
        }

        // Store original data for dirty checking
        this.state.originalData = {
            reservation_date: this.editReservationDate?.value,
            num_people: this.editNumPeople?.value,
            notes: this.editNotes?.value,
            price: this.panelFinalPriceInput?.value,
            payment_ticket_number: this.editPaymentTicket?.value,
            payment_method: this.editPaymentMethod?.value,
            minimum_consumption_policy_id: this.state.data?.reservation?.minimum_consumption_policy_id || null,
            package_id: this.state.data?.reservation?.package_id || null
        };

        // Enter customer edit mode (shows guest dropdown for interno, search for externo)
        this.enterCustomerEditMode();

        // Also enter preferences edit mode
        await this.enterPreferencesEditMode();

        // Enter pricing edit mode - fetch packages and calculate pricing
        await this.enterPricingEditMode();
    }

    /**
     * Exit edit mode
     * - Optionally confirms discard if there are unsaved changes
     * - Sets mode back to 'view'
     * - Resets dirty and numPeopleManuallyEdited flags
     * - Removes 'edit-mode' class from panel
     * - Updates edit button icon to pen (edit mode indicator)
     * - Unhighlights reservation furniture on map
     * - Shows view fields, hides edit fields
     * - Exits preferences and pricing edit modes
     * - Hides customer search
     *
     * @param {boolean} discard - Whether to discard changes (prompts confirmation if dirty)
     */
    exitEditMode(discard = false) {
        // Check for unsaved changes if discarding
        if (discard && this.state.isDirty) {
            if (!confirm('Tienes cambios sin guardar. ¿Descartar cambios?')) {
                return;
            }
        }

        this.state.mode = 'view';
        this.state.isDirty = false;
        this.state.numPeopleManuallyEdited = false;  // Reset flag when exiting edit mode
        this.panel.classList.remove('edit-mode');

        // Update edit button icon to indicate we're in view mode
        if (this.editIcon) {
            this.editIcon.className = 'fas fa-pen';
        }

        // Re-highlight furniture on the map (stays visible in view mode)
        this.highlightReservationFurniture();

        // Show view fields, hide edit fields for details section
        if (this.detailsViewMode) this.detailsViewMode.style.display = 'grid';
        if (this.detailsEditMode) this.detailsEditMode.style.display = 'none';

        // Show pricing view mode, hide edit mode
        if (this.pricingViewMode) this.pricingViewMode.style.display = 'block';
        if (this.pricingEditMode) this.pricingEditMode.style.display = 'none';

        // Show payment view mode, hide edit mode
        if (this.paymentViewMode) this.paymentViewMode.style.display = 'grid';
        if (this.paymentEditMode) this.paymentEditMode.style.display = 'none';

        // Exit preferences edit mode
        this.exitPreferencesEditMode(discard);

        // Exit pricing edit mode
        this.exitPricingEditMode(discard);

        // Exit customer edit mode
        this.exitCustomerEditMode();
    }
};
