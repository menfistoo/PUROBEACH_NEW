/**
 * DateAvailabilityHandler - Manages date picker and real-time availability checking
 * SG-02: Real-time availability check when dates change
 */
export class DateAvailabilityHandler {
    constructor(panel) {
        this.panel = panel;
        this._availabilityCheckTimeout = null;
    }

    /**
     * Initialize DatePicker for the panel
     */
    initDatePicker(date) {
        const container = document.getElementById('newPanelDatePicker');
        if (!container) return null;

        // Destroy existing picker if any
        if (this.panel.datePicker) {
            this.panel.datePicker.destroy();
        }

        // Create new DatePicker with current date
        const datePicker = new DatePicker({
            container: container,
            initialDates: [date],
            onDateChange: (dates) => {
                // SG-02: Real-time availability check when dates change
                this.checkAvailabilityRealtime(dates);
                // Calculate pricing when dates change
                this.panel.pricingCalculator.calculateAndDisplayPricing();
            }
        });

        return datePicker;
    }

    /**
     * SG-02: Real-time availability check (called when dates change)
     * Uses debouncing to avoid excessive API calls
     */
    checkAvailabilityRealtime(dates) {
        // Clear any pending check
        if (this._availabilityCheckTimeout) {
            clearTimeout(this._availabilityCheckTimeout);
        }

        // Debounce: wait 300ms before checking
        this._availabilityCheckTimeout = setTimeout(async () => {
            if (!dates || dates.length === 0) return;

            const furnitureIds = this.panel.state.selectedFurniture.map(f => f.id);
            if (furnitureIds.length === 0) return;

            try {
                const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
                const response = await fetch(`${this.panel.options.apiBaseUrl}/reservations/check-availability`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        furniture_ids: furnitureIds,
                        dates: dates
                    })
                });

                if (!response.ok) return;

                const result = await response.json();

                if (!result.all_available && result.unavailable && result.unavailable.length > 0) {
                    // Show inline warning in the furniture section
                    this.showAvailabilityWarning(result.unavailable, dates);
                } else {
                    // Clear any existing warning
                    this.clearAvailabilityWarning();
                }
            } catch (error) {
                console.error('Real-time availability check error:', error);
            }
        }, 300);
    }

    /**
     * Show inline availability warning in furniture section
     */
    showAvailabilityWarning(conflicts, selectedDates) {
        const furnitureChips = document.getElementById('newPanelFurnitureChips');
        if (!furnitureChips) return;

        // Find or create warning element
        let warningEl = furnitureChips.parentElement?.querySelector('.availability-warning');
        if (!warningEl) {
            warningEl = document.createElement('div');
            warningEl.className = 'availability-warning';
            furnitureChips.parentElement?.appendChild(warningEl);
        }

        // Get furniture numbers for display
        const furnitureMap = {};
        this.panel.state.selectedFurniture.forEach(f => {
            furnitureMap[f.id] = f.number;
        });

        // Group conflicts by date
        const conflictsByDate = {};
        conflicts.forEach(c => {
            if (!conflictsByDate[c.date]) conflictsByDate[c.date] = [];
            conflictsByDate[c.date].push({
                ...c,
                furniture_number: furnitureMap[c.furniture_id] || `#${c.furniture_id}`
            });
        });

        // Build warning message
        const formatDate = (dateStr) => {
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
        };

        let warningHtml = '<i class="fas fa-exclamation-triangle"></i> ';
        const conflictDates = Object.keys(conflictsByDate);

        if (conflictDates.length === 1) {
            const date = conflictDates[0];
            const items = conflictsByDate[date];
            warningHtml += `<strong>${items.map(i => i.furniture_number).join(', ')}</strong> ocupado el ${formatDate(date)}`;
        } else {
            warningHtml += `Mobiliario no disponible para ${conflictDates.length} fechas`;
        }

        warningEl.innerHTML = warningHtml;
        warningEl.style.display = 'flex';
    }

    /**
     * Clear availability warning
     */
    clearAvailabilityWarning() {
        const furnitureChips = document.getElementById('newPanelFurnitureChips');
        const warningEl = furnitureChips?.parentElement?.querySelector('.availability-warning');
        if (warningEl) {
            warningEl.style.display = 'none';
        }
    }

    /**
     * Show capacity warning when guest count exceeds furniture capacity
     */
    showCapacityWarning(guestCount, capacity) {
        const furnitureSummary = document.getElementById('newPanelFurnitureSummary');
        if (!furnitureSummary) return;

        // Find or create warning element in furniture section
        let warningEl = document.getElementById('newPanelCapacityWarning');
        if (!warningEl) {
            warningEl = document.createElement('div');
            warningEl.id = 'newPanelCapacityWarning';
            warningEl.className = 'capacity-warning';
            furnitureSummary.parentElement?.appendChild(warningEl);
        }

        const needed = guestCount - capacity;
        warningEl.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>
                <strong>${guestCount} huespedes</strong> en la habitacion pero el mobiliario seleccionado
                solo tiene capacidad para <strong>${capacity}</strong>.
            </span>
            <button type="button" class="btn-add-furniture" id="btnAddMoreFurniture">
                <i class="fas fa-plus"></i> Agregar mobiliario
            </button>
        `;
        warningEl.style.display = 'flex';

        // Bind click event for add furniture button
        const addBtn = document.getElementById('btnAddMoreFurniture');
        addBtn?.addEventListener('click', () => this.triggerAddMoreFurniture(needed));
    }

    /**
     * Hide capacity warning
     */
    hideCapacityWarning() {
        const warningEl = document.getElementById('newPanelCapacityWarning');
        if (warningEl) {
            warningEl.style.display = 'none';
        }
    }

    /**
     * Trigger the add more furniture flow
     */
    triggerAddMoreFurniture(neededCapacity) {
        const panel = document.getElementById('newReservationPanel');
        const backdrop = document.getElementById('newReservationPanelBackdrop');

        // Minimize the panel and hide backdrop to allow map interaction
        panel.classList.add('minimized');
        backdrop.classList.remove('show');

        // Dispatch event to tell the map to enter furniture addition mode
        document.dispatchEvent(new CustomEvent('reservation:addMoreFurniture', {
            detail: {
                currentFurniture: this.panel.state.selectedFurniture.map(f => f.id),
                neededCapacity: neededCapacity,
                currentDate: this.panel.state.currentDate
            }
        }));
    }

    /**
     * Add furniture to the current selection (called from map)
     */
    addFurniture(furniture) {
        // Add to selected furniture
        furniture.forEach(f => {
            if (!this.panel.state.selectedFurniture.find(sf => sf.id === f.id)) {
                this.panel.state.selectedFurniture.push(f);
            }
        });

        // Re-render furniture chips
        this.panel.renderFurnitureChips();

        // Check capacity again
        const capacity = this.panel.calculateCapacity();
        const numPeopleInput = document.getElementById('newPanelNumPeople');
        const guestCount = this.panel.customerHandler.state.roomGuests.length ||
                          parseInt(numPeopleInput?.value) || 2;

        if (guestCount > capacity) {
            this.showCapacityWarning(guestCount, capacity);
        } else {
            this.hideCapacityWarning();
        }

        // Restore panel and backdrop
        const panel = document.getElementById('newReservationPanel');
        const backdrop = document.getElementById('newReservationPanelBackdrop');
        panel.classList.remove('minimized');
        backdrop.classList.add('show');

        // Calculate pricing after furniture changes
        this.panel.pricingCalculator.calculateAndDisplayPricing();
    }
}
