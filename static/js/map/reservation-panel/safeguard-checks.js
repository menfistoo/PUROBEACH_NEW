/**
 * SafeguardChecks - Validation checks before creating reservations
 * SG-01: Duplicate reservation check
 * SG-02: Furniture availability check
 * SG-03: Hotel stay dates validation
 * SG-04: Capacity mismatch warnings
 * SG-05: Past dates error
 * SG-07: Furniture contiguity check
 */
class SafeguardChecks {
    constructor(panel) {
        this.panel = panel;
    }

    /**
     * Run all safeguard checks before creating reservation
     * @returns {Object} { proceed: boolean, viewExisting: number|null }
     */
    async runSafeguardChecks(customerId, customerSource, selectedDates) {
        // SG-05: Check for past dates
        const pastDateResult = await this.checkPastDates(selectedDates);
        if (!pastDateResult.proceed) {
            return { proceed: false };
        }

        // SG-03: Check hotel stay dates (only for hotel guests)
        if (customerSource === 'hotel_guest' && this.panel.customerHandler.state.selectedGuest) {
            const hotelStayResult = await this.checkHotelStayDates(selectedDates);
            if (!hotelStayResult.proceed) {
                return { proceed: false };
            }
        }

        // SG-04: Check capacity mismatch
        const capacityResult = await this.checkCapacityMismatch();
        if (!capacityResult.proceed) {
            return { proceed: false };
        }

        // SG-02: Check furniture availability
        const availabilityResult = await this.checkFurnitureAvailability(selectedDates);
        if (!availabilityResult.proceed) {
            return { proceed: false };
        }

        // SG-01: Check for duplicate reservation
        const duplicateResult = await this.checkDuplicateReservation(customerId, customerSource, selectedDates);
        if (!duplicateResult.proceed) {
            if (duplicateResult.viewExisting) {
                // User wants to view existing reservation
                return { proceed: false, viewExisting: duplicateResult.viewExisting };
            }
            return { proceed: false };
        }

        // SG-07: Check furniture contiguity (only for multiple furniture)
        if (this.panel.state.selectedFurniture.length > 1) {
            const contiguityResult = await this.checkFurnitureContiguity(selectedDates[0]);
            if (!contiguityResult.proceed) {
                return { proceed: false };
            }
        }

        return { proceed: true };
    }

    /**
     * SG-05: Check for past dates
     */
    async checkPastDates(selectedDates) {
        const today = new Date().toISOString().split('T')[0];
        const pastDates = selectedDates.filter(d => d < today);

        if (pastDates.length > 0) {
            await SafeguardModal.showPastDateError(pastDates);
            return { proceed: false };
        }

        return { proceed: true };
    }

    /**
     * SG-03: Check if selected dates are within hotel guest's stay
     */
    async checkHotelStayDates(selectedDates) {
        const guest = this.panel.customerHandler.state.selectedGuest;
        if (!guest || !guest.arrival_date || !guest.departure_date) {
            return { proceed: true }; // No hotel dates to check
        }

        // Normalize dates to YYYY-MM-DD for consistent comparison
        const normalizeDate = (dateStr) => {
            if (!dateStr) return null;
            // Handle ISO format (2025-12-21T00:00:00) or plain date
            return dateStr.split('T')[0];
        };

        const arrivalDate = normalizeDate(guest.arrival_date);
        const departureDate = normalizeDate(guest.departure_date);

        if (!arrivalDate || !departureDate) {
            return { proceed: true }; // Invalid dates, skip check
        }

        const outOfRangeDates = selectedDates.filter(date => {
            const normalizedDate = normalizeDate(date);
            return normalizedDate < arrivalDate || normalizedDate > departureDate;
        });

        if (outOfRangeDates.length > 0) {
            const action = await SafeguardModal.showHotelStayWarning(guest, outOfRangeDates);

            if (action === 'proceed') {
                return { proceed: true };
            }
            return { proceed: false };
        }

        return { proceed: true };
    }

    /**
     * SG-04: Check if num_people exceeds furniture capacity
     * SG-04b: Check if furniture capacity exceeds num_people
     */
    async checkCapacityMismatch() {
        const numPeople = parseInt(document.getElementById('newPanelNumPeople')?.value) || 2;
        const capacity = this.panel.calculateCapacity();

        // SG-04: More people than furniture capacity
        if (numPeople > capacity) {
            const action = await SafeguardModal.showCapacityWarning(numPeople, capacity);

            if (action === 'adjust') {
                document.getElementById('newPanelNumPeople').value = capacity;
                return { proceed: true };
            } else if (action === 'keep') {
                return { proceed: true };
            }
            return { proceed: false };
        }

        // SG-04b: More furniture capacity than people (excess sunbeds)
        if (capacity > numPeople) {
            const action = await SafeguardModal.showExcessCapacityWarning(numPeople, capacity);

            if (action === 'proceed') {
                return { proceed: true };
            }
            return { proceed: false };
        }

        return { proceed: true };
    }

    /**
     * SG-02: Check furniture availability for selected dates
     */
    async checkFurnitureAvailability(selectedDates) {
        try {
            const furnitureIds = this.panel.state.selectedFurniture.map(f => f.id);

            if (furnitureIds.length === 0 || selectedDates.length === 0) {
                return { proceed: true };
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/reservations/check-availability`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    furniture_ids: furnitureIds,
                    dates: selectedDates
                })
            });

            if (!response.ok) {
                console.error('Availability check failed:', response.status);
                this.panel.showToast('Error verificando disponibilidad. Intenta de nuevo.', 'error');
                return { proceed: false };
            }

            const result = await response.json();

            if (!result.all_available && result.unavailable && result.unavailable.length > 0) {
                console.log('[Safeguard] Furniture conflicts found:', result.unavailable);

                // Get furniture numbers for display
                const furnitureMap = {};
                this.panel.state.selectedFurniture.forEach(f => {
                    furnitureMap[f.id] = f.number;
                });

                // Enhance conflict data with furniture numbers
                const conflicts = result.unavailable.map(c => ({
                    ...c,
                    furniture_number: furnitureMap[c.furniture_id] || `#${c.furniture_id}`
                }));

                // For multi-day reservations, use the Conflict Resolution Modal
                // which allows selecting alternative furniture per day
                if (selectedDates.length > 1) {
                    // Trigger the conflict resolution flow
                    this.panel.conflictResolver.handleConflictError({ unavailable: conflicts }, selectedDates);
                    return { proceed: false, conflictResolution: true };
                }

                // For single-day reservations, show simple error modal
                await SafeguardModal.showFurnitureConflictError(conflicts);
                return { proceed: false };
            }

            return { proceed: true };

        } catch (error) {
            console.error('Furniture availability check error:', error);
            this.panel.showToast('Error verificando disponibilidad. Intenta de nuevo.', 'error');
            return { proceed: false };
        }
    }

    /**
     * SG-07: Check if selected furniture is contiguous (no gaps with occupied furniture)
     */
    async checkFurnitureContiguity(date) {
        try {
            const furnitureIds = this.panel.state.selectedFurniture.map(f => f.id);

            // Only check contiguity when multiple furniture selected
            if (furnitureIds.length <= 1) {
                return { proceed: true };
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/reservations/validate-contiguity`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    furniture_ids: furnitureIds,
                    date: date
                })
            });

            if (!response.ok) {
                console.error('Contiguity check failed:', response.status);
                this.panel.showToast('Error verificando contigüidad. Intenta de nuevo.', 'error');
                return { proceed: false };
            }

            const result = await response.json();

            // If not contiguous, show warning
            if (!result.is_contiguous && result.gap_count > 0) {
                console.log('[Safeguard] Non-contiguous furniture detected:', result);

                const action = await SafeguardModal.showContiguityWarning(result);

                if (action === 'proceed') {
                    return { proceed: true };
                }
                return { proceed: false };
            }

            return { proceed: true };

        } catch (error) {
            console.error('Contiguity check error:', error);
            this.panel.showToast('Error verificando contigüidad. Intenta de nuevo.', 'error');
            return { proceed: false };
        }
    }

    /**
     * SG-01: Check for duplicate reservation (same customer, same date)
     */
    async checkDuplicateReservation(customerId, customerSource, selectedDates) {
        try {
            // Build query params
            const params = new URLSearchParams();

            if (customerSource === 'hotel_guest') {
                params.append('hotel_guest_id', customerId);
            } else {
                params.append('customer_id', customerId);
            }

            // Check each date
            for (const date of selectedDates) {
                params.set('date', date);

                const response = await fetch(
                    `${this.panel.options.apiBaseUrl}/reservations/check-duplicate?${params.toString()}`
                );

                if (!response.ok) continue;

                const result = await response.json();

                if (result.has_duplicate && result.existing_reservation) {
                    console.log('[Safeguard] Duplicate found:', result.existing_reservation);
                    const action = await SafeguardModal.showDuplicateWarning(result.existing_reservation);
                    console.log('[Safeguard] User action:', action);

                    if (action === 'proceed') {
                        console.log('[Safeguard] User chose to proceed with duplicate');
                        return { proceed: true };
                    } else if (action === 'view') {
                        console.log('[Safeguard] User chose to view existing');
                        this.panel.close();
                        return { proceed: false, viewExisting: result.existing_reservation.id };
                    }
                    console.log('[Safeguard] User cancelled duplicate creation');
                    return { proceed: false };
                }
            }

            return { proceed: true };

        } catch (error) {
            console.error('Duplicate check error:', error);
            this.panel.showToast('Error verificando duplicados. Intenta de nuevo.', 'error');
            return { proceed: false };
        }
    }
}
