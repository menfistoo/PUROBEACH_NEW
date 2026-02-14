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
     * Handle reservation date change
     * Checks availability and either changes the date directly or shows conflict modal
     *
     * @param {Event} event - Change event from date input
     * @returns {Promise<void>}
     */
    async handleDateChange(event) {
        const newDate = event.target.value;
        const originalDate = this.state.originalData?.reservation_date;

        // Skip if same date
        if (newDate === originalDate) return;

        // Validate not a past date
        const today = new Date().toISOString().split('T')[0];
        if (newDate < today) {
            showToast('No se puede cambiar a una fecha pasada', 'error');
            this.editReservationDate.value = originalDate;
            return;
        }

        try {
            // Check availability on new date
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/check-date-availability`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ new_date: newDate })
                }
            );

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al verificar disponibilidad');
            }

            if (result.all_available) {
                // All furniture available - change date directly
                await this._changeDateDirectly(newDate);
            } else {
                // Furniture unavailable - show conflict modal
                await this._showDateConflictModal(newDate, originalDate, result);
            }

        } catch (error) {
            console.error('Date change error:', error);
            showToast(error.message, 'error');
            this.editReservationDate.value = originalDate;
        }
    }

    /**
     * Show modal when furniture is unavailable on new date
     * @private
     * @param {string} newDate - The new date
     * @param {string} originalDate - The original date to revert to
     * @param {object} availabilityResult - Result from check-date-availability
     */
    async _showDateConflictModal(newDate, originalDate, availabilityResult) {
        // Get SafeguardModal instance
        const SafeguardModal = window.SafeguardModal;
        if (!SafeguardModal) {
            // Fallback if modal not available
            showToast('El mobiliario no está disponible. Usa Modo Mover para cambiar.', 'warning');
            this.editReservationDate.value = originalDate;
            return;
        }

        const modal = SafeguardModal.getInstance();

        // Format date for display
        const formattedDate = new Date(newDate + 'T12:00:00').toLocaleDateString('es-ES', {
            weekday: 'long',
            day: 'numeric',
            month: 'long'
        });

        // Build conflict list HTML
        const conflicts = availabilityResult.conflicts || [];
        let conflictHtml = '';
        if (conflicts.length > 0) {
            const conflictItems = conflicts.map(c => {
                const furnitureName = c.furniture_number || `#${c.furniture_id}`;
                const customerName = c.customer_name || 'Otra reserva';
                return `<span class="blocking-item">${furnitureName}</span>`;
            }).join(' ');
            conflictHtml = `
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Mobiliario ocupado:</span>
                    </div>
                    <div class="blocking-list" style="margin-top: 8px;">
                        ${conflictItems}
                    </div>
                </div>
            `;
        }

        // Show modal
        const action = await modal.show({
            title: 'Mobiliario no disponible',
            type: 'warning',
            message: `
                <p>El mobiliario actual no está disponible para el <strong>${formattedDate}</strong>.</p>
                ${conflictHtml}
                <div class="safeguard-note" style="margin-top: 12px;">
                    <i class="fas fa-info-circle"></i>
                    <span>Puedes continuar sin mobiliario y asignarlo con el <strong>Modo Mover</strong>.</span>
                </div>
            `,
            buttons: [
                { label: 'Cancelar', action: 'cancel', style: 'secondary' },
                { label: 'Continuar', action: 'continue', style: 'primary', icon: 'fas fa-arrow-right' }
            ]
        });

        if (action === 'continue') {
            // User wants to continue without furniture
            await this._changeDateWithoutFurniture(newDate);
        } else {
            // User cancelled - revert date input
            this.editReservationDate.value = originalDate;
        }
    }

    /**
     * Change date and clear furniture, then activate move mode
     * @private
     * @param {string} newDate - The new date
     */
    async _changeDateWithoutFurniture(newDate) {
        try {
            // Call API with clear_furniture flag
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/change-date`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({
                        new_date: newDate,
                        clear_furniture: true
                    })
                }
            );

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al cambiar fecha');
            }

            // Store reservation ID for move mode
            const reservationId = this.state.reservationId;

            // Close the panel
            this.close();

            // Navigate map to new date and activate move mode
            if (window.moveMode) {
                // Navigate map to new date first
                if (window.beachMap && typeof window.beachMap.goToDate === 'function') {
                    await window.beachMap.goToDate(newDate);
                }

                // Activate move mode (this also loads unassigned reservations)
                await window.moveMode.activate(newDate);

                // Update toolbar button state
                const moveModeBtn = document.getElementById('btn-move-mode');
                if (moveModeBtn) {
                    moveModeBtn.classList.add('active');
                }
                document.querySelector('.beach-map-container')?.classList.add('move-mode-active');

                // Show success toast
                const formattedDate = new Date(newDate + 'T12:00:00').toLocaleDateString('es-ES', {
                    day: 'numeric',
                    month: 'short'
                });
                showToast(`Reserva movida al ${formattedDate} - selecciona mobiliario`, 'info');
            } else {
                // Fallback if move mode not available
                showToast('Reserva movida. Usa Modo Mover para asignar mobiliario.', 'warning');
            }

            // Notify parent to refresh map
            if (this.options.onSave) {
                this.options.onSave(reservationId, { date_changed: true, furniture_cleared: true });
            }

        } catch (error) {
            console.error('Date change without furniture error:', error);
            showToast(error.message || 'Error al cambiar fecha', 'error');
        }
    }

    /**
     * Change reservation date directly (when all furniture is available)
     * @private
     * @param {string} newDate - The new date in YYYY-MM-DD format
     */
    async _changeDateDirectly(newDate) {
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/change-date`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ new_date: newDate })
                }
            );

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al cambiar fecha');
            }

            // Update local state
            if (this.state.data?.reservation) {
                this.state.data.reservation.reservation_date = newDate;
                this.state.data.reservation.start_date = newDate;
            }
            this.state.currentDate = newDate;
            this.state.originalData.reservation_date = newDate;

            // Update header date display
            if (this.dateEl) {
                this.dateEl.textContent = this._formatDate(newDate);
            }

            // Notify parent to refresh map for old and new dates
            if (this.options.onDateChange) {
                this.options.onDateChange(this.state.reservationId, newDate);
            }

            showToast('Fecha actualizada', 'success');
            this.markDirty();

        } catch (error) {
            console.error('Date change error:', error);
            showToast(error.message, 'error');
            // Revert date input
            this.editReservationDate.value = this.state.originalData?.reservation_date;
        }
    }

    /**
     * Format date for display
     * @private
     * @param {string} dateStr - Date string in YYYY-MM-DD format
     * @returns {string} Formatted date string
     */
    _formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr + 'T12:00:00');
        return date.toLocaleDateString('es-ES', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    }

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
            const selectedPackageId = this.pricingEditState?.selectedPackageId;
            const originalPackageId = this.state.originalData?.package_id;
            if (selectedPackageId !== originalPackageId) {
                updates.package_id = selectedPackageId || null;
                hasChanges = true;
            }
        }

        // Minimum consumption policy
        const selectedPolicyId = this.pricingEditState?.selectedPolicyId;
        const originalPolicyId = this.state.originalData?.minimum_consumption_policy_id;
        if (selectedPolicyId !== originalPolicyId) {
            updates.minimum_consumption_policy_id = selectedPolicyId || null;
            hasChanges = true;
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

        // ---------------------------------------------------------------------
        // Check if tags have changed
        // ---------------------------------------------------------------------
        const originalTagIds = [...(this.tagsEditState.originalIds || [])].sort();
        const selectedTagIds = [...(this.tagsEditState.selectedIds || [])].sort();
        const tagsChanged = JSON.stringify(originalTagIds) !== JSON.stringify(selectedTagIds);

        // Include tag_ids in the main updates payload to avoid a separate API call
        if (tagsChanged) {
            updates.tag_ids = this.tagsEditState.selectedIds;
            hasChanges = true;
        }

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

            // Also save characteristics to the reservation itself
            if (preferencesChanged) {
                await fetch(
                    `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/update`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.csrfToken
                        },
                        body: JSON.stringify({
                            preferences: selectedCodes.join(',')
                        })
                    }
                );
            }

            // -----------------------------------------------------------------
            // Update local tag data if tags changed
            // -----------------------------------------------------------------
            if (tagsChanged) {
                const allTags = this.tagsEditState.allTags;
                const newTags = this.tagsEditState.selectedIds.map(id => {
                    return allTags.find(t => t.id === id);
                }).filter(Boolean);

                if (this.state.data?.reservation) {
                    this.state.data.reservation.tags = newTags;
                }

                this.renderTagsSection(this.state.data?.reservation);
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
                    preferences_changed: preferencesChanged,
                    tags_changed: tagsChanged
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
