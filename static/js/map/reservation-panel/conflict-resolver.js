/**
 * ConflictResolver - Handles multi-day furniture conflicts
 * Shows conflict modal, navigates to conflict days, retries with per-day selections
 */
class ConflictResolver {
    constructor(panel) {
        this.panel = panel;
        this.conflictModal = null;
    }

    /**
     * Initialize the conflict resolution modal (lazy)
     */
    initConflictModal() {
        if (this.conflictModal) return;

        this.conflictModal = new ConflictResolutionModal({
            onNavigateToDay: (date, conflicts) => {
                this.handleNavigateToConflictDay(date, conflicts);
            },
            onRetry: (furnitureByDate) => {
                this.retryWithPerDayFurniture(furnitureByDate);
            },
            onCancel: () => {
                this.panel.state.conflictResolutionMode = false;
                const panelEl = document.getElementById('newReservationPanel');
                panelEl.classList.remove('minimized');
            },
            onRemoveDate: (date) => {
                // Update the DatePicker when a date is removed from conflict modal
                if (this.panel.datePicker) {
                    this.panel.datePicker.removeDate(date);
                }
            }
        });
    }

    /**
     * Handle conflict error from API - show the conflict modal
     */
    handleConflictError(result, selectedDates) {
        this.initConflictModal();

        const originalFurniture = this.panel.state.selectedFurniture.map(f => f.id);

        // Save customer data for retry - the DOM might get reset during conflict resolution
        this.panel.state.savedCustomerForRetry = {
            customerId: document.getElementById('newPanelCustomerId').value,
            customerSource: document.getElementById('newPanelCustomerSource').value,
            selectedGuest: this.panel.customerHandler.state.selectedGuest,
            selectedCustomer: this.panel.customerHandler.state.selectedCustomer,
            chargeToRoom: document.getElementById('newPanelChargeToRoom')?.checked || false,
            numPeople: parseInt(document.getElementById('newPanelNumPeople').value) || 2,
            notes: document.getElementById('newPanelNotes')?.value || '',
            preferences: [...this.panel.state.preferences]
        };

        this.conflictModal.show(
            result.unavailable,
            selectedDates,
            originalFurniture
        );

        this.panel.state.conflictResolutionMode = true;
    }

    /**
     * Handle navigation to a conflict day - minimize panel and navigate map
     */
    handleNavigateToConflictDay(date, conflicts) {
        const panelEl = document.getElementById('newReservationPanel');
        // Minimize the panel
        panelEl.classList.add('minimized');

        // Get original selection for this date (or all furniture if not set)
        const originalSelection = this.panel.state.furnitureByDate[date] ||
                                  this.panel.state.selectedFurniture.map(f => f.id);

        // Build furniture number map for display
        const furnitureMap = {};
        this.panel.state.selectedFurniture.forEach(f => {
            furnitureMap[f.id] = f.number;
        });

        // Enhance conflicts with furniture numbers
        const enhancedConflicts = conflicts.map(c => ({
            ...c,
            furniture_number: c.furniture_number || furnitureMap[c.furniture_id] || `#${c.furniture_id}`
        }));

        // Dispatch event to tell the map to navigate and enter selection mode
        document.dispatchEvent(new CustomEvent('conflictResolution:selectAlternative', {
            detail: {
                date: date,
                conflicts: enhancedConflicts,
                currentSelection: originalSelection,
                originalCount: originalSelection.length,  // Total furniture to select
                conflictingLabels: enhancedConflicts.map(c => c.furniture_number).join(', ')
            }
        }));
    }

    /**
     * Retry creating reservation with per-day furniture selections
     */
    async retryWithPerDayFurniture(furnitureByDate) {
        const selectedDates = Object.keys(furnitureByDate).sort();

        if (selectedDates.length === 0) {
            this.panel.showToast('No hay fechas seleccionadas', 'warning');
            return;
        }

        // Validate all dates have furniture selections
        const missingDates = selectedDates.filter(d => !furnitureByDate[d]?.length);
        if (missingDates.length > 0) {
            this.panel.showToast('Selecciona mobiliario para todas las fechas', 'warning');
            return;
        }

        // Show loading state
        const createBtn = document.getElementById('newPanelCreateBtn');
        createBtn.disabled = true;
        createBtn.querySelector('.save-text').style.display = 'none';
        createBtn.querySelector('.save-loading').style.display = 'flex';

        try {
            // Use saved customer data from conflict resolution - PRIORITIZE saved values
            // because DOM might have been reset during conflict resolution flow
            const saved = this.panel.state.savedCustomerForRetry || {};

            // In conflict resolution, always use saved data if available
            const customerId = saved.customerId || document.getElementById('newPanelCustomerId').value;
            const customerSource = saved.customerSource || document.getElementById('newPanelCustomerSource').value || 'customer';

            console.log('[RetryReservation] Customer data:', {
                savedCustomerId: saved.customerId,
                domCustomerId: document.getElementById('newPanelCustomerId').value,
                finalCustomerId: customerId,
                savedSource: saved.customerSource,
                domSource: document.getElementById('newPanelCustomerSource').value,
                finalSource: customerSource
            });

            if (!customerId) {
                throw new Error('Cliente requerido');
            }

            let finalCustomerId = parseInt(customerId);

            // If hotel guest, convert to beach customer first
            if (customerSource === 'hotel_guest') {
                const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
                const convertResponse = await fetch(`${this.panel.options.apiBaseUrl}/customers/from-hotel-guest`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        hotel_guest_id: finalCustomerId
                    })
                });

                const convertData = await convertResponse.json();

                if (!convertData.success) {
                    throw new Error(convertData.error || 'Error al convertir huesped a cliente');
                }

                finalCustomerId = convertData.customer.id;
            }

            // Build payload with furniture_by_date, using saved values as fallback
            const numPeople = parseInt(document.getElementById('newPanelNumPeople').value) || saved.numPeople || 2;
            const notes = document.getElementById('newPanelNotes')?.value?.trim() || saved.notes || '';
            const preferences = this.panel.state.preferences?.length > 0 ? this.panel.state.preferences : (saved.preferences || []);
            const chargeToRoom = document.getElementById('newPanelChargeToRoom')?.checked ?? saved.chargeToRoom ?? false;

            const payload = {
                customer_id: finalCustomerId,
                dates: selectedDates,
                furniture_by_date: furnitureByDate,  // Per-day furniture selections
                num_people: numPeople,
                time_slot: 'all_day',
                notes: notes,
                preferences: preferences,
                charge_to_room: chargeToRoom
            };

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/map/quick-reservation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                this.panel.showToast(result.message || 'Reserva creada exitosamente', 'success');
                this.panel.state.conflictResolutionMode = false;
                this.panel.state.savedCustomerForRetry = null;  // Clear saved data after success
                const panelEl = document.getElementById('newReservationPanel');
                panelEl.classList.remove('minimized');
                this.panel.close();

                // Notify callback
                if (this.panel.options.onSave) {
                    this.panel.options.onSave(result.reservation);
                }
            } else {
                // Still conflicts? Show modal again
                if (result.unavailable && result.unavailable.length > 0) {
                    const originalFurniture = Object.values(furnitureByDate)[0] || [];
                    this.conflictModal.show(
                        result.unavailable,
                        selectedDates,
                        originalFurniture
                    );
                } else {
                    throw new Error(result.error || 'Error al crear reserva');
                }
            }

        } catch (error) {
            console.error('Retry reservation error:', error);
            this.panel.showToast(error.message, 'error');
        } finally {
            // Reset button state
            const createBtn = document.getElementById('newPanelCreateBtn');
            createBtn.disabled = false;
            createBtn.querySelector('.save-text').style.display = 'inline';
            createBtn.querySelector('.save-loading').style.display = 'none';
        }
    }
}
