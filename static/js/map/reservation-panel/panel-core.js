/**
 * NewReservationPanel - Main panel coordinator
 * Integrates all specialized modules for creating reservations
 *
 * Module Architecture:
 * - CustomerHandler: Customer selection, creation, display
 * - DateAvailabilityHandler: Date picker, availability checks
 * - PricingCalculator: Pricing fetch, display, editing
 * - ConflictResolver: Conflict modal, per-day selections
 * - SafeguardChecks: All validation checks (SG-01 to SG-07)
 *
 * Dependencies (must be loaded before this file):
 * - customer-handler.js
 * - date-availability.js
 * - pricing-calculator.js
 * - conflict-resolver.js
 * - safeguard-checks.js
 */

class NewReservationPanel {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '/beach/api',
            onSave: null,
            onCancel: null,
            ...options
        };

        // State
        this.state = {
            isOpen: false,
            selectedFurniture: [],
            currentDate: null,
            preferences: [],
            conflictResolutionMode: false,
            furnitureByDate: {},   // {date: [furniture_ids]} - per-day selections
            savedCustomerForRetry: null,  // Saved customer data during conflict resolution
            waitlistEntryId: null  // Track waitlist entry ID for conversion
        };

        // Available characteristics (loaded from API)
        this.availableCharacteristics = [];

        // Cache DOM elements
        this.cacheElements();

        // CSRF token
        this.csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';

        // Initialize modules
        this.customerHandler = new CustomerHandler(this);
        this.dateAvailabilityHandler = new DateAvailabilityHandler(this);
        this.pricingCalculator = new PricingCalculator(this);
        this.conflictResolver = new ConflictResolver(this);
        this.safeguardChecks = new SafeguardChecks(this);

        // Shared components (initialized on first open)
        this.customerSearch = null;
        this.datePicker = null;

        // Setup event listeners
        this.setupEventListeners();
        this.initCustomerSearch();
    }

    /**
     * Cache DOM elements for quick access
     */
    cacheElements() {
        this.panel = document.getElementById('newReservationPanel');
        this.backdrop = document.getElementById('newReservationPanelBackdrop');

        if (!this.panel || !this.backdrop) {
            console.warn('NewReservationPanel: Required elements not found');
            return;
        }

        // Furniture elements
        this.dateDisplay = document.getElementById('newPanelDate');
        this.furnitureChips = document.getElementById('newPanelFurnitureChips');
        this.furnitureSummary = document.getElementById('newPanelFurnitureSummary');

        // Details elements
        this.numPeopleInput = document.getElementById('newPanelNumPeople');
        this.notesInput = document.getElementById('newPanelNotes');
        this.preferencesInput = document.getElementById('newPanelPreferences');
        this.preferenceChipsContainer = document.getElementById('newPanelPreferenceChips');

        // Buttons
        this.closeBtn = document.getElementById('newPanelCloseBtn');
        this.cancelBtn = document.getElementById('newPanelCancelBtn');
        this.createBtn = document.getElementById('newPanelCreateBtn');
    }

    /**
     * Initialize CustomerSearch component
     */
    initCustomerSearch() {
        const searchInput = document.getElementById('newPanelCustomerSearch');
        const resultsContainer = document.getElementById('newPanelCustomerResults');

        if (searchInput && resultsContainer) {
            this.customerSearch = new CustomerSearch({
                inputElement: searchInput,
                resultsContainer: resultsContainer,
                apiUrl: `${this.options.apiBaseUrl}/customers/search`,
                compact: true,
                showCreateLink: false,
                showInlineCreate: true,
                onSelect: (customer) => {
                    document.getElementById('newPanelCustomerId').value = customer.id;
                    document.getElementById('newPanelCustomerSource').value = 'customer';
                    this.customerHandler.autoFillCustomerData(customer);
                },
                onHotelGuestSelect: (guest) => {
                    this.customerHandler.handleHotelGuestSelect(guest);
                },
                onShowCreateForm: (prefillData) => {
                    this.customerHandler.showCreateCustomerForm(prefillData);
                }
            });
        }
    }

    /**
     * Load available characteristics from API
     */
    async loadCharacteristics() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/preferences`);
            if (response.ok) {
                const result = await response.json();
                this.availableCharacteristics = result.preferences || [];
                this.renderPreferenceChips();
            }
        } catch (error) {
            console.warn('Could not load characteristics:', error);
            if (this.preferenceChipsContainer) {
                this.preferenceChipsContainer.innerHTML =
                    '<span class="text-muted small">Error al cargar preferencias</span>';
            }
        }
    }

    /**
     * Render preference chips dynamically
     */
    renderPreferenceChips() {
        if (!this.preferenceChipsContainer) return;

        if (this.availableCharacteristics.length === 0) {
            this.preferenceChipsContainer.innerHTML =
                '<span class="text-muted small">No hay preferencias disponibles</span>';
            return;
        }

        const chipsHtml = this.availableCharacteristics.map(char => {
            // Normalize icon class
            let icon = char.icon || 'fa-star';
            if (!icon.startsWith('fas ') && !icon.startsWith('far ') && !icon.startsWith('fab ')) {
                icon = 'fas ' + icon;
            }
            const isActive = this.state.preferences.includes(char.code);
            return `
                <button type="button" class="pref-chip ${isActive ? 'active' : ''}" data-pref="${char.code}">
                    <i class="${icon}"></i> ${char.name}
                </button>
            `;
        }).join('');

        this.preferenceChipsContainer.innerHTML = chipsHtml;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Close buttons
        this.closeBtn?.addEventListener('click', () => this.close());
        this.cancelBtn?.addEventListener('click', () => this.close());
        this.backdrop?.addEventListener('click', () => this.close());

        // Create button
        this.createBtn?.addEventListener('click', () => this.createReservation());

        // Customer clear button
        const clearBtn = document.getElementById('newPanelCustomerClearBtn');
        clearBtn?.addEventListener('click', () => this.customerHandler.clearCustomerSelection());

        // Guest selector change
        const guestSelector = document.getElementById('newPanelGuestSelector');
        guestSelector?.addEventListener('change', () => this.customerHandler.onGuestSelectorChange());

        // Preference chips - use event delegation for dynamic chips
        this.preferenceChipsContainer?.addEventListener('click', (e) => {
            const chip = e.target.closest('.pref-chip');
            if (chip) {
                this.togglePreference(chip);
            }
        });

        // Load available characteristics
        this.loadCharacteristics();

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.state.isOpen) {
                this.close();
            }
        });

        // Track manual edits to num_people
        this.numPeopleManuallyEdited = false;

        // Track changes to num_people for pricing calculation
        this.numPeopleInput?.addEventListener('change', () => {
            // Mark as manually edited when user changes the value
            this.numPeopleManuallyEdited = true;

            // Calculate pricing when num_people changes
            this.pricingCalculator.calculateAndDisplayPricing();

            // Show capacity warning if exceeded (but don't prevent it)
            const capacity = this.calculateCapacity();
            const numPeople = parseInt(this.numPeopleInput.value) || 0;
            if (numPeople > capacity) {
                this.showCapacityWarning(numPeople, capacity);
            } else {
                this.hideCapacityWarning();
            }
        });

        // Also track input events (typing) as manual edits
        this.numPeopleInput?.addEventListener('input', () => {
            this.numPeopleManuallyEdited = true;
        });
    }

    /**
     * Open the panel with selected furniture
     */
    open(furniture, date) {
        if (!furniture || furniture.length === 0) {
            this.showToast('Selecciona mobiliario primero', 'warning');
            return;
        }

        // Set state
        this.state.isOpen = true;
        this.state.selectedFurniture = furniture;
        this.state.currentDate = date;
        this.state.preferences = [];

        // Reset manual edit flag when opening new reservation
        this.numPeopleManuallyEdited = false;

        // Reset form
        this.resetForm();

        // Populate furniture chips
        this.renderFurnitureChips();

        // Set date display
        this.dateDisplay.textContent = this.formatDateDisplay(date);

        // Initialize DatePicker with current date
        this.datePicker = this.dateAvailabilityHandler.initDatePicker(date);

        // Set default num_people based on capacity
        const capacity = this.calculateCapacity();
        this.numPeopleInput.value = Math.min(2, capacity);

        // Show panel
        this.panel.classList.add('open');
        this.backdrop.classList.add('show');

        // Focus on customer search
        setTimeout(() => {
            document.getElementById('newPanelCustomerSearch')?.focus();
        }, 300);

        // Calculate initial pricing if customer already selected
        if (document.getElementById('newPanelCustomerId').value) {
            this.pricingCalculator.calculateAndDisplayPricing();
        }
    }

    /**
     * Close the panel
     */
    close() {
        this.state.isOpen = false;
        this.state.conflictResolutionMode = false;
        this.state.savedCustomerForRetry = null;
        this.state.waitlistEntryId = null;  // Clear waitlist entry on close
        this.panel.classList.remove('open');
        this.panel.classList.remove('minimized');
        this.backdrop.classList.remove('show');

        // Notify callback
        if (this.options.onCancel) {
            this.options.onCancel();
        }
    }

    /**
     * Open the panel pre-filled from a waitlist entry
     * Called when user clicks "Convertir" on a waitlist entry
     * @param {Object} entry - Waitlist entry with customer and preference data
     */
    async openFromWaitlist(entry) {
        if (!entry) {
            console.warn('NewReservationPanel.openFromWaitlist: No entry provided');
            return;
        }

        // Store waitlist entry ID for conversion after reservation is created
        this.state.waitlistEntryId = entry.id;

        // We need furniture selected to open the panel
        // If preferred zone/type specified, we could suggest furniture
        // For now, just notify user they need to select furniture
        this.showToast('Selecciona mobiliario en el mapa para crear la reserva', 'info');

        // Store waitlist data for pre-filling when panel opens
        this._pendingWaitlistEntry = entry;

        // Dispatch event to notify map that we're in waitlist convert mode
        document.dispatchEvent(new CustomEvent('waitlist:selectFurnitureForConvert', {
            detail: { entry }
        }));
    }

    /**
     * Pre-fill the panel with waitlist entry data
     * Called after furniture is selected
     * @param {Object} entry - Waitlist entry data
     */
    async prefillFromWaitlist(entry) {
        if (!entry) return;

        // Store waitlist entry ID
        this.state.waitlistEntryId = entry.id;

        // Pre-fill customer if available
        if (entry.customer_id) {
            try {
                // Fetch full customer data
                const response = await fetch(`${this.options.apiBaseUrl}/customers/${entry.customer_id}`);
                const data = await response.json();

                if (data.success && data.customer) {
                    document.getElementById('newPanelCustomerId').value = data.customer.id;
                    document.getElementById('newPanelCustomerSource').value = 'customer';
                    this.customerHandler.autoFillCustomerData(data.customer);
                }
            } catch (error) {
                console.error('Error fetching customer for waitlist conversion:', error);
            }
        } else if (entry.customer_name || entry.external_name) {
            // No customer_id but have name info
            const isInterno = entry.customer_type === 'interno';
            const displayName = entry.customer_name || entry.external_name || '';
            const phone = entry.phone || entry.external_phone || '';

            if (!isInterno) {
                // External customer: Show create customer form pre-filled
                // so user can complete the customer profile
                const nameParts = displayName.split(' ');
                const firstName = nameParts[0] || '';
                const lastName = nameParts.slice(1).join(' ') || '';

                this.customerHandler.showCreateCustomerForm({
                    first_name: firstName,
                    last_name: lastName,
                    phone: phone,
                    email: entry.email || ''
                });

                // Update charge_to_room visibility for external
                this.customerHandler.updateChargeToRoomVisibility('externo', false);
            } else {
                // Internal customer (hotel guest) without customer_id
                // Display as pending customer info
                const tempCustomer = {
                    display_name: displayName,
                    first_name: displayName.split(' ')[0] || '',
                    last_name: displayName.split(' ').slice(1).join(' ') || '',
                    customer_type: 'interno',
                    room_number: entry.room_number || null,
                    phone: phone,
                    source: 'hotel_guest'
                };

                // Show in display (but don't set customer_id since it doesn't exist yet)
                this.customerHandler.showCustomerDisplay(tempCustomer);

                // Update charge_to_room visibility
                this.customerHandler.updateChargeToRoomVisibility('interno', true);
            }
        }

        // Pre-fill number of people
        if (entry.num_people && this.numPeopleInput) {
            this.numPeopleInput.value = entry.num_people;
            this.numPeopleManuallyEdited = true; // Mark as set so it's not overwritten
        }

        // Pre-fill notes with waitlist context
        if (entry.notes && this.notesInput) {
            this.notesInput.value = 'Desde lista de espera: ' + entry.notes;
        }

        // Pre-fill date if available (initialize DatePicker with the requested date)
        if (entry.requested_date && this.datePicker) {
            this.datePicker.setSelectedDates([entry.requested_date]);
        }

        // Calculate pricing after pre-filling
        this.pricingCalculator.calculateAndDisplayPricing();
    }

    /**
     * Reset the form to initial state
     */
    resetForm() {
        // Clear customer search
        if (this.customerSearch) {
            this.customerSearch.clear();
        }
        document.getElementById('newPanelCustomerId').value = '';
        document.getElementById('newPanelCustomerSource').value = 'customer';

        // Hide customer display, show search wrapper
        const customerDisplay = document.getElementById('newPanelCustomerDisplay');
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const clearBtn = document.getElementById('newPanelCustomerClearBtn');

        if (customerDisplay) customerDisplay.style.display = 'none';
        if (searchWrapper) searchWrapper.style.display = 'block';
        if (clearBtn) clearBtn.style.display = 'none';

        // Hide guest selector and clear room guests state
        this.customerHandler.hideGuestSelector();
        this.customerHandler.state.selectedGuest = null;
        this.customerHandler.state.selectedCustomer = null;

        // Hide charge_to_room on form reset
        this.customerHandler.updateChargeToRoomVisibility(null, false);

        // Reset inputs
        if (this.notesInput) this.notesInput.value = '';

        // Clear payment fields
        const paymentTicketInput = document.getElementById('newPanelPaymentTicket');
        const paymentMethodSelect = document.getElementById('newPanelPaymentMethod');
        if (paymentTicketInput) paymentTicketInput.value = '';
        if (paymentMethodSelect) paymentMethodSelect.value = '';

        // Clear preferences
        this.clearPreferences();
    }

    /**
     * Render furniture chips
     */
    renderFurnitureChips() {
        if (!this.furnitureChips) return;

        const chipsHtml = this.state.selectedFurniture.map(f => `
            <span class="furniture-chip">
                <span class="furniture-type-icon">${this.getFurnitureIcon(f.type_name)}</span>
                ${f.number}
            </span>
        `).join('');

        this.furnitureChips.innerHTML = chipsHtml;

        // Update summary
        const count = this.state.selectedFurniture.length;
        const capacity = this.calculateCapacity();
        this.furnitureSummary.textContent = `${count} item${count !== 1 ? 's' : ''} • Capacidad: ${capacity} personas`;
    }

    /**
     * Get furniture icon based on type
     */
    getFurnitureIcon(typeName) {
        if (!typeName) return '🪑';
        const name = typeName.toLowerCase();
        if (name.includes('hamaca')) return '🛏️';
        if (name.includes('balinesa')) return '🛖';
        if (name.includes('sombrilla')) return '☂️';
        return '🪑';
    }

    /**
     * Calculate total capacity
     */
    calculateCapacity() {
        return this.state.selectedFurniture.reduce((sum, f) => sum + (f.capacity || 2), 0);
    }

    /**
     * Format date for display
     */
    formatDateDisplay(dateStr) {
        const date = new Date(dateStr + 'T12:00:00');
        const options = { weekday: 'short', day: 'numeric', month: 'short' };
        return date.toLocaleDateString('es-ES', options);
    }

    /**
     * Toggle preference chip
     */
    togglePreference(chip) {
        const pref = chip.dataset.pref;
        chip.classList.toggle('active');

        if (chip.classList.contains('active')) {
            if (!this.state.preferences.includes(pref)) {
                this.state.preferences.push(pref);
            }
        } else {
            this.state.preferences = this.state.preferences.filter(p => p !== pref);
        }

        // Update hidden input
        this.preferencesInput.value = this.state.preferences.join(',');
    }

    /**
     * Clear all preferences
     */
    clearPreferences() {
        // Query all chips within the container (dynamic chips)
        const chips = this.preferenceChipsContainer?.querySelectorAll('.pref-chip');
        chips?.forEach(chip => chip.classList.remove('active'));
        this.state.preferences = [];
        if (this.preferencesInput) {
            this.preferencesInput.value = '';
        }
    }

    /**
     * Create the reservation
     */
    async createReservation() {
        // Validate customer
        const customerId = document.getElementById('newPanelCustomerId').value;
        const customerSource = document.getElementById('newPanelCustomerSource').value;

        if (!customerId) {
            this.showToast('Selecciona un cliente', 'warning');
            document.getElementById('newPanelCustomerSearch')?.focus();
            return;
        }

        // Get selected dates from DatePicker
        const selectedDates = this.datePicker ? this.datePicker.getSelectedDates() : [];
        if (selectedDates.length === 0) {
            this.showToast('Selecciona al menos una fecha', 'warning');
            return;
        }

        // Run safeguard checks before proceeding
        const safeguardResult = await this.safeguardChecks.runSafeguardChecks(customerId, customerSource, selectedDates);
        if (!safeguardResult.proceed) {
            // Check if user wants to view an existing reservation
            if (safeguardResult.viewExisting) {
                // Dispatch event to open the existing reservation panel
                document.dispatchEvent(new CustomEvent('reservation:openExisting', {
                    detail: { reservationId: safeguardResult.viewExisting }
                }));
            }
            return; // User cancelled or viewing existing
        }

        // Show loading state
        this.createBtn.disabled = true;
        this.createBtn.querySelector('.save-text').style.display = 'none';
        this.createBtn.querySelector('.save-loading').style.display = 'flex';

        try {
            let finalCustomerId = parseInt(customerId);

            // If hotel guest, convert to beach customer first
            if (customerSource === 'hotel_guest') {
                const convertResponse = await fetch(`${this.options.apiBaseUrl}/customers/from-hotel-guest`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
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

            // Get selected package_id if any
            const selectedPackageIdInput = document.getElementById('newPanelSelectedPackageId');
            const packageId = selectedPackageIdInput?.value || '';

            // Get manual price override if any
            const priceOverrideInput = document.getElementById('newPanelPriceOverride');
            const priceOverride = priceOverrideInput?.value || '';

            // Get payment fields
            const paymentTicketInput = document.getElementById('newPanelPaymentTicket');
            const paymentMethodSelect = document.getElementById('newPanelPaymentMethod');

            // Get payment values for auto-toggle paid logic
            const paymentTicketValue = paymentTicketInput?.value.trim() || null;
            const paymentMethodValue = paymentMethodSelect?.value || null;

            // Create reservation using map quick-reservation endpoint
            const payload = {
                customer_id: finalCustomerId,
                furniture_ids: this.state.selectedFurniture.map(f => f.id),
                dates: selectedDates,
                num_people: parseInt(this.numPeopleInput.value) || 2,
                time_slot: 'all_day',
                notes: this.notesInput.value.trim(),
                preferences: this.state.preferences,
                charge_to_room: document.getElementById('newPanelChargeToRoom')?.checked || false,
                payment_ticket_number: paymentTicketValue,
                payment_method: paymentMethodValue,
                // Auto-toggle paid when payment details are provided
                paid: (paymentTicketValue || paymentMethodValue) ? 1 : 0
            };

            // Add package_id if selected (otherwise use minimum consumption)
            if (packageId) {
                payload.package_id = parseInt(packageId);
            }

            // Add manual price override if user edited the price
            if (priceOverride) {
                payload.price_override = parseFloat(priceOverride);
            }

            const response = await fetch(`${this.options.apiBaseUrl}/map/quick-reservation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(result.message || 'Reserva creada exitosamente', 'success');

                // Mark waitlist entry as converted if this reservation came from waitlist
                // Note: API returns 'reservation_id', not 'parent_id'
                const reservationId = result.reservation_id || result.parent_id;
                if (this.state.waitlistEntryId && reservationId) {
                    await this.markWaitlistAsConverted(this.state.waitlistEntryId, reservationId);
                }

                this.close();

                // Notify callback
                if (this.options.onSave) {
                    this.options.onSave({ id: reservationId, ticket_number: result.ticket_number || result.parent_ticket });
                }
            } else {
                // Check if this is a conflict error (multi-day with unavailable furniture)
                if (result.unavailable && result.unavailable.length > 0) {
                    this.conflictResolver.handleConflictError(result, selectedDates);
                } else {
                    throw new Error(result.error || 'Error al crear reserva');
                }
            }

        } catch (error) {
            console.error('Create reservation error:', error);
            this.showToast(error.message, 'error');
        } finally {
            // Reset button state
            this.createBtn.disabled = false;
            this.createBtn.querySelector('.save-text').style.display = 'inline';
            this.createBtn.querySelector('.save-loading').style.display = 'none';
        }
    }

    /**
     * Show toast message
     */
    showToast(message, type = 'info') {
        if (window.PuroBeach && window.PuroBeach.showToast) {
            window.PuroBeach.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Check if panel is open
     */
    isOpen() {
        return this.state.isOpen;
    }

    /**
     * Delegate methods to DateAvailabilityHandler
     */
    showCapacityWarning(guestCount, capacity) {
        this.dateAvailabilityHandler.showCapacityWarning(guestCount, capacity);
    }

    hideCapacityWarning() {
        this.dateAvailabilityHandler.hideCapacityWarning();
    }

    addFurniture(furniture) {
        this.dateAvailabilityHandler.addFurniture(furniture);
    }

    /**
     * Mark a waitlist entry as converted after reservation creation
     * @param {number} entryId - Waitlist entry ID
     * @param {number} reservationId - Created reservation ID
     */
    async markWaitlistAsConverted(entryId, reservationId) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/waitlist/${entryId}/convert`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ reservation_id: reservationId })
            });

            const data = await response.json();

            if (data.success) {
                // Dispatch event to update waitlist badge count
                window.dispatchEvent(new CustomEvent('waitlist:countUpdate'));
            } else {
                console.error('Error marking waitlist as converted:', data.error);
            }
        } catch (error) {
            console.error('Error marking waitlist as converted:', error);
        }
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NewReservationPanel;
}
