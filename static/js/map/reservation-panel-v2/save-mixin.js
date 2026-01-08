/**
 * ReservationPanel Save Mixin
 *
 * Handles saving all changes made in edit mode - reservation updates and
 * customer preferences. Orchestrates multiple API calls and updates local state.
 *
 * Extracted from reservation-panel.js as part of the modular refactoring.
 */

import { showToast } from './utils.js';

// =============================================================================
// SAVE MIXIN
// =============================================================================

/**
 * Mixin that adds save functionality to the ReservationPanel
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with save methods
 */
export const SaveMixin = (Base) => class extends Base {

    /**
     * Save changes made in edit mode
     *
     * Collects all changed values from edit fields, validates them,
     * and sends updates to the server. Also handles preference changes
     * for the customer separately.
     *
     * @returns {Promise<void>}
     */
    async saveChanges() {
        // Guard against double-submit
        if (this.state.isSubmitting) return;

        const updates = {};
        let hasChanges = false;
        let preferencesChanged = false;
        let priceChanged = false;

        // ---------------------------------------------------------------------
        // Collect changed values
        // ---------------------------------------------------------------------

        // Number of people
        if (this.editNumPeople && this.editNumPeople.value !== this.state.originalData?.num_people) {
            updates.num_people = parseInt(this.editNumPeople.value) || 1;
            hasChanges = true;
        }

        // Observations/notes
        if (this.editNotes && this.editNotes.value !== this.state.originalData?.notes) {
            updates.observations = this.editNotes.value;
            hasChanges = true;
        }

        // Price and package
        if (this.panelFinalPriceInput) {
            const currentPrice = this.panelFinalPriceInput.value;
            const originalPrice = this.state.originalData?.price;
            if (currentPrice !== originalPrice) {
                updates.total_price = parseFloat(currentPrice) || 0;
                priceChanged = true;
                hasChanges = true;
            }

            // Also include package_id if changed
            const selectedPackageId = this.panelSelectedPackageId?.value;
            if (selectedPackageId) {
                updates.package_id = parseInt(selectedPackageId);
            }
        }

        // Payment ticket number
        if (this.editPaymentTicket) {
            const currentTicket = this.editPaymentTicket.value.trim();
            const originalTicket = this.state.originalData?.payment_ticket_number || '';
            if (currentTicket !== originalTicket) {
                updates.payment_ticket_number = currentTicket || null;
                hasChanges = true;
            }
        }

        // Payment method
        if (this.editPaymentMethod) {
            const currentMethod = this.editPaymentMethod.value;
            const originalMethod = this.state.originalData?.payment_method || '';
            if (currentMethod !== originalMethod) {
                updates.payment_method = currentMethod || null;
                hasChanges = true;
            }
        }

        // ---------------------------------------------------------------------
        // Auto-toggle paid when payment details are filled
        // ---------------------------------------------------------------------
        const hasPaymentTicket = this.editPaymentTicket?.value.trim();
        const hasPaymentMethod = this.editPaymentMethod?.value;
        if (hasPaymentTicket || hasPaymentMethod) {
            const currentPaid = this.state.data?.reservation?.paid;
            if (!currentPaid) {
                updates.paid = 1;
                hasChanges = true;
            }
        }

        // ---------------------------------------------------------------------
        // Check if preferences have changed
        // ---------------------------------------------------------------------
        const originalCodes = this.preferencesEditState.originalCodes || [];
        const selectedCodes = this.preferencesEditState.selectedCodes || [];
        preferencesChanged = JSON.stringify(originalCodes.sort()) !== JSON.stringify(selectedCodes.sort());

        // Exit early if no changes
        if (!hasChanges && !preferencesChanged) {
            this.exitEditMode(false);
            return;
        }

        // ---------------------------------------------------------------------
        // Show loading state on save button
        // ---------------------------------------------------------------------
        this.state.isSubmitting = true;
        this.saveBtn.querySelector('.save-text').style.display = 'none';
        this.saveBtn.querySelector('.save-loading').style.display = 'inline-flex';
        this.saveBtn.disabled = true;

        try {
            // -----------------------------------------------------------------
            // Save reservation updates if any
            // -----------------------------------------------------------------
            if (hasChanges) {
                const response = await fetch(
                    `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/update`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.csrfToken
                        },
                        body: JSON.stringify(updates)
                    }
                );

                const result = await response.json();

                if (!result.success) {
                    throw new Error(result.error || 'Error al guardar reserva');
                }

                // Update local data
                if (this.state.data?.reservation) {
                    Object.assign(this.state.data.reservation, updates);
                }

                // Re-render sections with new data
                this.renderDetailsSection(this.state.data.reservation);
                this.renderPricingSection(this.state.data.reservation);
                this.renderPaymentSection(this.state.data.reservation);
            }

            // -----------------------------------------------------------------
            // Save preferences if changed
            // -----------------------------------------------------------------
            if (preferencesChanged) {
                const customerId = this.state.data?.customer?.id;
                if (customerId) {
                    const prefResponse = await fetch(
                        `${this.options.apiBaseUrl}/customers/${customerId}/preferences`,
                        {
                            method: 'PUT',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': this.csrfToken
                            },
                            body: JSON.stringify({ preference_codes: selectedCodes })
                        }
                    );

                    const prefResult = await prefResponse.json();

                    if (!prefResult.success) {
                        throw new Error(prefResult.error || 'Error al guardar preferencias');
                    }

                    // Update local customer data with new preferences
                    const allPrefs = this.preferencesEditState.allPreferences;
                    const newPrefs = selectedCodes.map(code => {
                        return allPrefs.find(p => p.code === code);
                    }).filter(Boolean);

                    if (this.state.data?.customer) {
                        this.state.data.customer.preferences = newPrefs;
                    }
                }
            }

            // -----------------------------------------------------------------
            // Exit edit mode and notify
            // -----------------------------------------------------------------
            this.state.isDirty = false;
            this.state.numPeopleManuallyEdited = false;  // Reset flag after successful save
            this.exitEditMode(false);

            // Call onSave callback if provided
            if (this.options.onSave) {
                this.options.onSave(this.state.reservationId, {
                    ...updates,
                    preferences_changed: preferencesChanged
                });
            }

            showToast('Reserva actualizada', 'success');

        } catch (error) {
            console.error('Save error:', error);
            showToast(error.message, 'error');
        } finally {
            // Reset button state
            this.state.isSubmitting = false;
            this.saveBtn.querySelector('.save-text').style.display = 'inline-flex';
            this.saveBtn.querySelector('.save-loading').style.display = 'none';
            this.saveBtn.disabled = false;
        }
    }
};
