/**
 * NewReservationPanel - Side panel for creating new reservations
 * Uses shared CustomerSearch and DatePicker components
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
            roomGuests: [],       // All guests in the selected hotel room
            selectedGuest: null,  // Currently selected hotel guest
            // Conflict resolution state
            conflictResolutionMode: false,
            furnitureByDate: {}   // {date: [furniture_ids]} - per-day selections
        };

        // Conflict resolution modal (lazy initialized)
        this.conflictModal = null;

        // Cache DOM elements
        this.panel = document.getElementById('newReservationPanel');
        this.backdrop = document.getElementById('newReservationPanelBackdrop');

        if (!this.panel || !this.backdrop) {
            console.warn('NewReservationPanel: Required elements not found');
            return;
        }

        // Cache form elements
        this.dateDisplay = document.getElementById('newPanelDate');
        this.furnitureChips = document.getElementById('newPanelFurnitureChips');
        this.furnitureSummary = document.getElementById('newPanelFurnitureSummary');

        // Customer elements
        this.customerSearchWrapper = document.getElementById('newPanelCustomerWrapper');
        this.customerSearchInput = document.getElementById('newPanelCustomerSearch');
        this.customerResults = document.getElementById('newPanelCustomerResults');
        this.customerIdInput = document.getElementById('newPanelCustomerId');
        this.customerSourceInput = document.getElementById('newPanelCustomerSource');
        this.customerClearBtn = document.getElementById('newPanelCustomerClearBtn');

        // Selected customer display elements
        this.customerDisplay = document.getElementById('newPanelCustomerDisplay');
        this.customerAvatar = document.getElementById('newPanelCustomerAvatar');
        this.customerInitials = document.getElementById('newPanelCustomerInitials');
        this.customerNameEl = document.getElementById('newPanelCustomerName');
        this.customerMeta = document.getElementById('newPanelCustomerMeta');
        this.customerRoom = document.getElementById('newPanelCustomerRoom');
        this.customerCheckin = document.getElementById('newPanelCustomerCheckin');
        this.customerCheckout = document.getElementById('newPanelCustomerCheckout');
        this.customerBookingRef = document.getElementById('newPanelCustomerBookingRef');
        this.customerRoomItem = document.getElementById('newPanelRoomItem');
        this.customerCheckinItem = document.getElementById('newPanelCheckinItem');
        this.customerCheckoutItem = document.getElementById('newPanelCheckoutItem');
        this.customerBookingItem = document.getElementById('newPanelBookingItem');
        this.customerDetailsGrid = document.getElementById('newPanelCustomerDetailsGrid');

        // Guest selector elements (for hotel rooms with multiple guests)
        this.guestSelectorWrapper = document.getElementById('newPanelGuestSelectorWrapper');
        this.guestCountDisplay = document.getElementById('newPanelGuestCount');
        this.guestSelector = document.getElementById('newPanelGuestSelector');

        // Date picker container
        this.datePickerContainer = document.getElementById('newPanelDatePicker');

        // Details elements
        this.numPeopleInput = document.getElementById('newPanelNumPeople');
        this.notesInput = document.getElementById('newPanelNotes');
        this.preferencesInput = document.getElementById('newPanelPreferences');
        this.preferenceChips = document.querySelectorAll('#newPanelPreferenceChips .pref-chip');

        // SG-06: Charge to room elements
        this.chargeToRoomWrapper = document.getElementById('newPanelChargeToRoomWrapper');
        this.chargeToRoomCheckbox = document.getElementById('newPanelChargeToRoom');

        // Buttons
        this.closeBtn = document.getElementById('newPanelCloseBtn');
        this.cancelBtn = document.getElementById('newPanelCancelBtn');
        this.createBtn = document.getElementById('newPanelCreateBtn');

        // CSRF token
        this.csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';

        // Shared components (initialized on first open)
        this.customerSearch = null;
        this.datePicker = null;

        this.setupEventListeners();
        this.initComponents();
    }

    /**
     * Initialize shared components
     */
    initComponents() {
        // Cache create form elements
        this.createCustomerForm = document.getElementById('newPanelCreateCustomerForm');
        this.createCustFirstName = document.getElementById('newCustFirstName');
        this.createCustLastName = document.getElementById('newCustLastName');
        this.createCustPhone = document.getElementById('newCustPhone');
        this.createCustEmail = document.getElementById('newCustEmail');
        this.createCustLanguage = document.getElementById('newCustLanguage');
        this.createCustError = document.getElementById('newCustError');
        this.cancelCreateBtn = document.getElementById('newPanelCancelCreateBtn');
        this.saveCustomerBtn = document.getElementById('newPanelSaveCustomerBtn');

        // Bind create form events
        this.cancelCreateBtn?.addEventListener('click', () => this.hideCreateCustomerForm());
        this.saveCustomerBtn?.addEventListener('click', () => this.saveNewCustomer());

        // Initialize CustomerSearch component
        if (this.customerSearchInput && this.customerResults) {
            this.customerSearch = new CustomerSearch({
                inputElement: this.customerSearchInput,
                resultsContainer: this.customerResults,
                apiUrl: `${this.options.apiBaseUrl}/customers/search`,
                compact: true,
                showCreateLink: false,
                showInlineCreate: true,
                onSelect: (customer) => {
                    this.customerIdInput.value = customer.id;
                    this.customerSourceInput.value = 'customer';
                    // Auto-fill preferences and notes from customer record
                    this.autoFillCustomerData(customer);
                },
                onHotelGuestSelect: (guest) => {
                    this.handleHotelGuestSelect(guest);
                },
                onShowCreateForm: (prefillData) => {
                    // Show the inline create customer form
                    this.showCreateCustomerForm(prefillData);
                }
            });
        }

        // DatePicker will be initialized in open() with the correct initial date
    }

    /**
     * Show the inline create customer form
     */
    showCreateCustomerForm(prefillData = {}) {
        if (!this.createCustomerForm) return;

        // Hide search wrapper
        this.customerSearchWrapper.style.display = 'none';

        // Pre-fill name if provided
        if (prefillData.first_name) {
            this.createCustFirstName.value = prefillData.first_name;
        }
        if (prefillData.last_name) {
            this.createCustLastName.value = prefillData.last_name;
        }

        // Show create form
        this.createCustomerForm.style.display = 'block';
        this.createCustFirstName?.focus();
    }

    /**
     * Hide the inline create customer form
     */
    hideCreateCustomerForm() {
        if (!this.createCustomerForm) return;

        // Clear form
        if (this.createCustFirstName) this.createCustFirstName.value = '';
        if (this.createCustLastName) this.createCustLastName.value = '';
        if (this.createCustPhone) this.createCustPhone.value = '';
        if (this.createCustEmail) this.createCustEmail.value = '';
        if (this.createCustLanguage) this.createCustLanguage.value = '';
        if (this.createCustError) this.createCustError.style.display = 'none';

        // Hide form, show search
        this.createCustomerForm.style.display = 'none';
        this.customerSearchWrapper.style.display = 'block';
        this.customerSearchInput.value = '';
    }

    /**
     * Save the new customer from the inline form
     */
    async saveNewCustomer() {
        const firstName = this.createCustFirstName?.value.trim() || '';
        const lastName = this.createCustLastName?.value.trim() || '';
        const phone = this.createCustPhone?.value.trim() || '';
        const email = this.createCustEmail?.value.trim() || '';
        const language = this.createCustLanguage?.value || '';

        // Validation
        if (!firstName) {
            this.showCreateError('El nombre es requerido');
            return;
        }
        if (!phone && !email) {
            this.showCreateError('Se requiere telefono o email');
            return;
        }

        // Disable button
        this.saveCustomerBtn.disabled = true;
        this.saveCustomerBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando...';

        try {
            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.options.apiBaseUrl}/customers/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    customer_type: 'externo',
                    first_name: firstName,
                    last_name: lastName,
                    phone: phone,
                    email: email,
                    language: language,
                    country_code: '+34'
                })
            });

            const result = await response.json();

            if (result.success && result.customer) {
                // Hide form
                this.hideCreateCustomerForm();

                // Handle newly created customer
                this.handleNewCustomerCreated(result.customer);
            } else {
                this.showCreateError(result.error || 'Error al crear cliente');
            }
        } catch (error) {
            console.error('Error creating customer:', error);
            this.showCreateError('Error de conexion');
        } finally {
            this.saveCustomerBtn.disabled = false;
            this.saveCustomerBtn.innerHTML = '<i class="fas fa-check"></i> Crear Cliente';
        }
    }

    /**
     * Show error in create form
     */
    showCreateError(message) {
        if (this.createCustError) {
            this.createCustError.textContent = message;
            this.createCustError.style.display = 'block';
            setTimeout(() => {
                this.createCustError.style.display = 'none';
            }, 3000);
        }
    }

    /**
     * Handle newly created customer from inline form
     */
    handleNewCustomerCreated(customer) {
        this.customerIdInput.value = customer.id;
        this.customerSourceInput.value = 'customer';
        this.state.selectedCustomer = customer;
        this.state.selectedGuest = null;

        // Show customer display
        this.showCustomerDisplay(customer);

        // Hide guest selector (external customers don't have room guests)
        this.hideGuestSelector();

        // SG-06: External customers can't charge to room
        this.updateChargeToRoomVisibility('externo', false);

        // Set num_people from the form if provided
        if (customer.num_people && this.numPeopleInput) {
            this.numPeopleInput.value = customer.num_people;
        }

        // Clear preferences (new customer has no preferences yet)
        this.clearPreferences();
    }

    /**
     * Auto-fill preferences and notes from customer record
     * Unified flow: internal customers with room numbers get the same treatment as hotel guests
     */
    async autoFillCustomerData(customer) {
        this.state.selectedCustomer = customer;

        // Show customer display with details
        this.showCustomerDisplay(customer);

        // SG-06: Update charge_to_room visibility based on customer type
        const isInterno = customer.customer_type === 'interno';
        this.updateChargeToRoomVisibility(customer.customer_type, isInterno);

        // Clear current preferences first
        this.clearPreferences();

        // If customer has preferences, activate matching chips
        if (customer.preferences && customer.preferences.length > 0) {
            customer.preferences.forEach(prefCode => {
                // Find the matching chip (preferences come as codes like 'pref_primera_linea')
                const chip = document.querySelector(`#newPanelPreferenceChips .pref-chip[data-pref="${prefCode}"]`);
                if (chip) {
                    chip.classList.add('active');
                    if (!this.state.preferences.includes(prefCode)) {
                        this.state.preferences.push(prefCode);
                    }
                }
            });
            // Update hidden input
            if (this.preferencesInput) {
                this.preferencesInput.value = this.state.preferences.join(',');
            }
        }

        // Auto-fill notes from customer record (but filter out date patterns if we show dates in UI)
        if (customer.notes && this.notesInput) {
            let notes = customer.notes;
            // If we're showing dates in UI, remove date patterns from notes
            // (legacy data may have dates stored in notes)
            if (isInterno && customer.room_number) {
                // Remove full Spanish pattern: "Huesped hotel (llegada: 2025-12-21, salida: 2025-12-30)"
                notes = notes
                    .replace(/huesped\s+hotel\s*\([^)]*llegada[^)]*salida[^)]*\)/gi, '')
                    // Remove patterns like "Check-in: 25/12", "Check-out: 30/12", etc.
                    .replace(/check[- ]?in:?\s*[\d\-\/]+/gi, '')
                    .replace(/check[- ]?out:?\s*[\d\-\/]+/gi, '')
                    .replace(/entrada:?\s*[\d\-\/]+/gi, '')
                    .replace(/salida:?\s*[\d\-\/]+/gi, '')
                    .replace(/llegada:?\s*[\d\-\/]+/gi, '')
                    // Date ranges like "25/12/2024 - 30/12/2024"
                    .replace(/\d{1,4}[\/\-]\d{1,2}[\/\-]\d{1,4}\s*[-–]\s*\d{1,4}[\/\-]\d{1,2}[\/\-]\d{1,4}/g, '')
                    .replace(/\s*[,;]\s*[,;]\s*/g, ', ')  // Clean up double separators
                    .replace(/^\s*[,;]\s*/g, '')  // Clean leading separators
                    .replace(/\s*[,;]\s*$/g, '')  // Clean trailing separators
                    .trim();
            }
            this.notesInput.value = notes;
        }

        // For internal customers with a room number, fetch room guests like hotel guests
        if (isInterno && customer.room_number) {
            try {
                const response = await fetch(
                    `${this.options.apiBaseUrl}/hotel-guests/lookup?room=${encodeURIComponent(customer.room_number)}`
                );
                const data = await response.json();

                this.state.roomGuests = data.guests || [];
                const guestCount = data.guest_count || 1;

                // If multiple guests in room, show the selector
                if (guestCount > 1 && this.state.roomGuests.length > 1) {
                    // Find the matching guest based on customer name
                    const customerName = `${customer.first_name || ''} ${customer.last_name || ''}`.trim().toUpperCase();
                    let matchingGuest = this.state.roomGuests.find(g =>
                        g.guest_name.toUpperCase() === customerName
                    );

                    // If no exact match, use main guest or first guest
                    if (!matchingGuest) {
                        matchingGuest = this.state.roomGuests.find(g => g.is_main_guest) || this.state.roomGuests[0];
                    }

                    this.state.selectedGuest = matchingGuest;
                    this.showGuestSelector(matchingGuest, guestCount);

                    // Update display with hotel guest data (arrival/departure)
                    if (matchingGuest) {
                        this.showCustomerDisplay({
                            ...customer,
                            arrival_date: matchingGuest.arrival_date,
                            departure_date: matchingGuest.departure_date,
                            booking_reference: matchingGuest.booking_reference,
                            vip_code: matchingGuest.vip_code
                        });
                    }
                } else if (this.state.roomGuests.length === 1) {
                    // Single guest - update display with hotel data
                    const guest = this.state.roomGuests[0];
                    this.state.selectedGuest = guest;
                    this.hideGuestSelector();
                    this.showCustomerDisplay({
                        ...customer,
                        arrival_date: guest.arrival_date,
                        departure_date: guest.departure_date,
                        booking_reference: guest.booking_reference,
                        vip_code: guest.vip_code
                    });
                } else {
                    this.hideGuestSelector();
                    this.state.selectedGuest = null;
                }

                // Auto-set num_people based on guest count
                const capacity = this.calculateCapacity();
                if (this.numPeopleInput && guestCount > 0) {
                    this.numPeopleInput.value = guestCount;
                }

                // Check capacity warning
                if (guestCount > capacity) {
                    this.showCapacityWarning(guestCount, capacity);
                } else {
                    this.hideCapacityWarning();
                }

            } catch (error) {
                console.error('Error fetching room guests for customer:', error);
                this.hideGuestSelector();
                this.state.selectedGuest = null;
            }
        } else {
            // External customer - no guest selector
            this.hideGuestSelector();
            this.state.selectedGuest = null;
        }
    }

    /**
     * Show customer display with expanded details
     */
    showCustomerDisplay(customer) {
        // Hide search wrapper, show customer display
        if (this.customerSearchWrapper) this.customerSearchWrapper.style.display = 'none';
        if (this.customerDisplay) this.customerDisplay.style.display = 'block';
        if (this.customerClearBtn) this.customerClearBtn.style.display = 'flex';

        // Initials
        const firstName = customer.first_name || customer.guest_name?.split(' ')[0] || '';
        const lastName = customer.last_name || customer.guest_name?.split(' ').slice(1).join(' ') || '';
        const initials = (firstName.charAt(0) + lastName.charAt(0)).toUpperCase() || '--';
        if (this.customerInitials) this.customerInitials.textContent = initials;

        // Avatar class
        if (this.customerAvatar) {
            this.customerAvatar.className = 'customer-avatar';
            if (customer.vip_status || customer.vip_code) {
                this.customerAvatar.classList.add('vip');
            } else if (customer.customer_type === 'interno' || customer.source === 'hotel_guest') {
                this.customerAvatar.classList.add('interno');
            }
        }

        // Name
        const fullName = customer.display_name || customer.full_name ||
            `${customer.first_name || ''} ${customer.last_name || ''}`.trim() ||
            customer.guest_name || 'Sin nombre';
        if (this.customerNameEl) this.customerNameEl.textContent = fullName;

        // Meta (type badge, VIP, phone)
        let meta = [];
        if (customer.customer_type === 'interno' || customer.source === 'hotel_guest') {
            meta.push('<span class="badge bg-info">Interno</span>');
        } else {
            meta.push('<span class="badge bg-secondary">Externo</span>');
        }
        if (customer.vip_status || customer.vip_code) {
            meta.push('<i class="fas fa-star vip-badge"></i> VIP');
        }
        if (customer.phone) {
            meta.push(`<i class="fas fa-phone"></i> ${customer.phone}`);
        }
        if (this.customerMeta) {
            this.customerMeta.innerHTML = meta.join(' <span class="mx-1">•</span> ');
        }

        // Details grid
        this.renderCustomerDetailsGrid(customer);
    }

    /**
     * Render customer details inline (room, check-in, check-out, booking ref)
     */
    renderCustomerDetailsGrid(customer) {
        // Room
        if (this.customerRoom) {
            const room = customer.room_number;
            if (room) {
                this.customerRoom.textContent = `Hab. ${room}`;
                if (this.customerRoomItem) this.customerRoomItem.style.display = 'inline-flex';
            } else {
                if (this.customerRoomItem) this.customerRoomItem.style.display = 'none';
            }
        }

        // Check-in date
        if (this.customerCheckin) {
            const arrivalDate = customer.arrival_date;
            if (arrivalDate) {
                this.customerCheckin.textContent = this.formatDateShort(arrivalDate);
                if (this.customerCheckinItem) this.customerCheckinItem.style.display = 'inline-flex';
            } else {
                if (this.customerCheckinItem) this.customerCheckinItem.style.display = 'none';
            }
        }

        // Check-out date
        if (this.customerCheckout) {
            const departureDate = customer.departure_date;
            if (departureDate) {
                this.customerCheckout.textContent = this.formatDateShort(departureDate);
                if (this.customerCheckoutItem) this.customerCheckoutItem.style.display = 'inline-flex';
            } else {
                if (this.customerCheckoutItem) this.customerCheckoutItem.style.display = 'none';
            }
        }

        // Booking reference
        if (this.customerBookingRef) {
            const bookingRef = customer.booking_reference;
            if (bookingRef) {
                this.customerBookingRef.textContent = bookingRef;
                if (this.customerBookingItem) this.customerBookingItem.style.display = 'inline-flex';
            } else {
                if (this.customerBookingItem) this.customerBookingItem.style.display = 'none';
            }
        }

        // Hide details row if no details (external customer without hotel info)
        if (this.customerDetailsGrid) {
            const hasDetails = customer.room_number || customer.arrival_date ||
                               customer.departure_date || customer.booking_reference;
            this.customerDetailsGrid.style.display = hasDetails ? 'flex' : 'none';
        }
    }

    /**
     * Format date for display (short format: DD/MM)
     */
    formatDateShort(dateStr) {
        if (!dateStr) return '-';
        try {
            const date = new Date(dateStr);
            const day = date.getDate().toString().padStart(2, '0');
            const month = (date.getMonth() + 1).toString().padStart(2, '0');
            return `${day}/${month}`;
        } catch (e) {
            return dateStr;
        }
    }

    /**
     * Clear customer selection and show search again
     */
    clearCustomerSelection() {
        // Clear state
        this.customerIdInput.value = '';
        this.customerSourceInput.value = 'customer';
        this.state.selectedCustomer = null;
        this.state.selectedGuest = null;

        // Hide customer display, show search wrapper
        if (this.customerDisplay) this.customerDisplay.style.display = 'none';
        if (this.customerSearchWrapper) this.customerSearchWrapper.style.display = 'block';
        if (this.customerClearBtn) this.customerClearBtn.style.display = 'none';

        // Clear and reset search
        if (this.customerSearch) {
            this.customerSearch.clear();
        }

        // Hide guest selector
        this.hideGuestSelector();

        // SG-06: Hide charge_to_room when no customer selected
        this.updateChargeToRoomVisibility(null, false);

        // Clear notes
        if (this.notesInput) this.notesInput.value = '';

        // Clear preferences
        this.clearPreferences();

        // Focus on search input
        this.customerSearchInput?.focus();
    }

    /**
     * Clear all preferences
     */
    clearPreferences() {
        this.preferenceChips?.forEach(chip => chip.classList.remove('active'));
        this.state.preferences = [];
        if (this.preferencesInput) {
            this.preferencesInput.value = '';
        }
    }

    /**
     * SG-06: Update charge_to_room visibility based on customer type
     * Only hotel guests (internos) can charge to room
     * @param {string} customerType - 'interno' or 'externo'
     * @param {boolean} isHotelGuest - True if selected from hotel guest list
     */
    updateChargeToRoomVisibility(customerType, isHotelGuest = false) {
        if (!this.chargeToRoomWrapper) return;

        // Show charge_to_room only for internal customers (hotel guests)
        const canChargeToRoom = customerType === 'interno' || isHotelGuest;

        if (canChargeToRoom) {
            this.chargeToRoomWrapper.style.display = 'block';
            // Default to checked for hotel guests
            if (this.chargeToRoomCheckbox && isHotelGuest) {
                this.chargeToRoomCheckbox.checked = true;
            }
        } else {
            this.chargeToRoomWrapper.style.display = 'none';
            // Ensure unchecked when hidden
            if (this.chargeToRoomCheckbox) {
                this.chargeToRoomCheckbox.checked = false;
            }
        }
    }

    /**
     * Handle hotel guest selection - fetch room guests and populate selector
     */
    async handleHotelGuestSelect(guest) {
        this.customerIdInput.value = guest.id;
        this.customerSourceInput.value = 'hotel_guest';
        this.state.selectedGuest = guest;

        // Show customer display with guest details
        this.showCustomerDisplay(guest);

        // SG-06: Show charge_to_room option for hotel guests
        this.updateChargeToRoomVisibility('interno', true);

        // Hotel guests don't have preferences yet, clear them
        this.clearPreferences();

        // But they may have notes from the PMS
        if (guest.notes && this.notesInput) {
            this.notesInput.value = guest.notes;
        }

        // Fetch all guests in the room
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/hotel-guests/lookup?room=${encodeURIComponent(guest.room_number)}`
            );
            const data = await response.json();

            this.state.roomGuests = data.guests || [];
            const guestCount = data.guest_count || 1;

            // If multiple guests, show the selector
            if (guestCount > 1 && this.state.roomGuests.length > 1) {
                this.showGuestSelector(guest, guestCount);
            } else {
                this.hideGuestSelector();
            }

            // Auto-set num_people based on guest count
            const capacity = this.calculateCapacity();
            if (this.numPeopleInput) {
                this.numPeopleInput.value = guestCount;
            }

            // Check if we need more furniture for all guests
            if (guestCount > capacity) {
                this.showCapacityWarning(guestCount, capacity);
            } else {
                this.hideCapacityWarning();
            }

        } catch (error) {
            console.error('Error fetching room guests:', error);
            this.hideGuestSelector();
            // Set default num_people to 1 if fetch fails
            if (this.numPeopleInput) {
                this.numPeopleInput.value = 1;
            }
        }
    }

    /**
     * Show capacity warning when guest count exceeds furniture capacity
     */
    showCapacityWarning(guestCount, capacity) {
        // Find or create warning element in furniture section
        let warningEl = document.getElementById('newPanelCapacityWarning');
        if (!warningEl) {
            warningEl = document.createElement('div');
            warningEl.id = 'newPanelCapacityWarning';
            warningEl.className = 'capacity-warning';
            this.furnitureSummary?.parentElement?.appendChild(warningEl);
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
        // Minimize the panel and hide backdrop to allow map interaction
        this.panel.classList.add('minimized');
        this.backdrop.classList.remove('show');

        // Dispatch event to tell the map to enter furniture addition mode
        document.dispatchEvent(new CustomEvent('reservation:addMoreFurniture', {
            detail: {
                currentFurniture: this.state.selectedFurniture.map(f => f.id),
                neededCapacity: neededCapacity,
                currentDate: this.state.currentDate
            }
        }));
    }

    /**
     * Add furniture to the current selection (called from map)
     */
    addFurniture(furniture) {
        // Add to selected furniture
        furniture.forEach(f => {
            if (!this.state.selectedFurniture.find(sf => sf.id === f.id)) {
                this.state.selectedFurniture.push(f);
            }
        });

        // Re-render furniture chips
        this.renderFurnitureChips();

        // Check capacity again
        const capacity = this.calculateCapacity();
        const guestCount = this.state.roomGuests.length || parseInt(this.numPeopleInput?.value) || 2;

        if (guestCount > capacity) {
            this.showCapacityWarning(guestCount, capacity);
        } else {
            this.hideCapacityWarning();
        }

        // Restore panel and backdrop
        this.panel.classList.remove('minimized');
        this.backdrop.classList.add('show');
    }

    /**
     * Show the guest selector dropdown
     */
    showGuestSelector(selectedGuest, guestCount) {
        if (!this.guestSelectorWrapper || !this.guestSelector) return;

        // Update guest count display
        if (this.guestCountDisplay) {
            this.guestCountDisplay.textContent = guestCount;
        }

        // Populate the selector with all room guests
        this.guestSelector.innerHTML = this.state.roomGuests.map(g => {
            const isSelected = g.id === selectedGuest.id;
            const mainBadge = g.is_main_guest ? ' (Principal)' : '';
            return `<option value="${g.id}" ${isSelected ? 'selected' : ''}>${g.guest_name}${mainBadge}</option>`;
        }).join('');

        // Show the wrapper
        this.guestSelectorWrapper.style.display = 'block';
    }

    /**
     * Hide the guest selector
     */
    hideGuestSelector() {
        if (this.guestSelectorWrapper) {
            this.guestSelectorWrapper.style.display = 'none';
        }
        this.state.roomGuests = [];
    }

    /**
     * Handle guest selector change
     */
    onGuestSelectorChange() {
        const selectedId = parseInt(this.guestSelector.value);
        const guest = this.state.roomGuests.find(g => g.id === selectedId);

        if (guest) {
            this.customerIdInput.value = guest.id;
            this.state.selectedGuest = guest;

            // Update customer display with new guest info
            this.showCustomerDisplay(guest);

            // Update notes if the guest has any
            if (this.notesInput) {
                this.notesInput.value = guest.notes || '';
            }
        }
    }

    setupEventListeners() {
        // Close buttons
        this.closeBtn?.addEventListener('click', () => this.close());
        this.cancelBtn?.addEventListener('click', () => this.close());
        this.backdrop?.addEventListener('click', () => this.close());

        // Create button
        this.createBtn?.addEventListener('click', () => this.createReservation());

        // Customer clear button
        this.customerClearBtn?.addEventListener('click', () => this.clearCustomerSelection());

        // Guest selector change
        this.guestSelector?.addEventListener('change', () => this.onGuestSelectorChange());

        // Preference chips
        this.preferenceChips?.forEach(chip => {
            chip.addEventListener('click', () => this.togglePreference(chip));
        });

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.state.isOpen) {
                this.close();
            }
        });

        // Auto-update num_people based on furniture capacity
        this.numPeopleInput?.addEventListener('change', () => {
            const capacity = this.calculateCapacity();
            if (parseInt(this.numPeopleInput.value) > capacity) {
                this.numPeopleInput.value = capacity;
            }
        });
    }

    /**
     * Open the panel with selected furniture
     * @param {Array} furniture - Array of furniture objects [{id, number, type_name, capacity}]
     * @param {string} date - Current date (YYYY-MM-DD)
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

        // Reset form
        this.resetForm();

        // Populate furniture chips
        this.renderFurnitureChips();

        // Set date display
        this.dateDisplay.textContent = this.formatDateDisplay(date);

        // Initialize or reset DatePicker with current date
        if (this.datePicker) {
            this.datePicker.destroy();
        }
        this.datePicker = new DatePicker({
            container: this.datePickerContainer,
            initialDates: [date],
            onDateChange: (dates) => {
                // SG-02: Real-time availability check when dates change
                this.checkAvailabilityRealtime(dates);
            }
        });

        // Set default num_people based on capacity
        const capacity = this.calculateCapacity();
        this.numPeopleInput.value = Math.min(2, capacity);

        // Show panel
        this.panel.classList.add('open');
        this.backdrop.classList.add('show');

        // Focus on customer search
        setTimeout(() => {
            this.customerSearchInput?.focus();
        }, 300);
    }

    /**
     * Close the panel
     */
    close() {
        this.state.isOpen = false;
        this.state.conflictResolutionMode = false;
        this.state.savedCustomerForRetry = null;  // Clear saved data when closing
        this.panel.classList.remove('open');
        this.panel.classList.remove('minimized');
        this.backdrop.classList.remove('show');

        // Notify callback
        if (this.options.onCancel) {
            this.options.onCancel();
        }
    }

    /**
     * Reset the form to initial state
     */
    resetForm() {
        // Clear customer search
        if (this.customerSearch) {
            this.customerSearch.clear();
        }
        this.customerIdInput.value = '';
        this.customerSourceInput.value = 'customer';

        // Hide customer display, show search wrapper
        if (this.customerDisplay) this.customerDisplay.style.display = 'none';
        if (this.customerSearchWrapper) this.customerSearchWrapper.style.display = 'block';
        if (this.customerClearBtn) this.customerClearBtn.style.display = 'none';

        // Hide guest selector and clear room guests state
        this.hideGuestSelector();
        this.state.selectedGuest = null;
        this.state.selectedCustomer = null;

        // SG-06: Hide charge_to_room on form reset
        this.updateChargeToRoomVisibility(null, false);

        // Reset inputs
        if (this.notesInput) this.notesInput.value = '';

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
     * Create the reservation
     */
    async createReservation() {
        // Validate customer
        const customerId = this.customerIdInput.value;
        const customerSource = this.customerSourceInput.value;

        if (!customerId) {
            this.showToast('Selecciona un cliente', 'warning');
            this.customerSearchInput?.focus();
            return;
        }

        // Get selected dates from DatePicker
        const selectedDates = this.datePicker ? this.datePicker.getSelectedDates() : [];
        if (selectedDates.length === 0) {
            this.showToast('Selecciona al menos una fecha', 'warning');
            return;
        }

        // Run safeguard checks before proceeding
        const safeguardResult = await this.runSafeguardChecks(customerId, customerSource, selectedDates);
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

            // Create reservation using map quick-reservation endpoint
            const payload = {
                customer_id: finalCustomerId,
                furniture_ids: this.state.selectedFurniture.map(f => f.id),
                dates: selectedDates,
                num_people: parseInt(this.numPeopleInput.value) || 2,
                time_slot: 'all_day',
                notes: this.notesInput.value.trim(),
                preferences: this.state.preferences,
                // SG-06: Include charge_to_room (only for hotel guests)
                charge_to_room: this.chargeToRoomCheckbox?.checked || false
            };

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
                this.close();

                // Notify callback
                if (this.options.onSave) {
                    this.options.onSave(result.reservation);
                }
            } else {
                // Check if this is a conflict error (multi-day with unavailable furniture)
                if (result.unavailable && result.unavailable.length > 0) {
                    this.handleConflictError(result, selectedDates);
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
     * SG-02: Real-time availability check (called when dates change)
     * Uses debouncing to avoid excessive API calls
     * @param {Array} dates - Selected dates from DatePicker
     */
    checkAvailabilityRealtime(dates) {
        // Clear any pending check
        if (this._availabilityCheckTimeout) {
            clearTimeout(this._availabilityCheckTimeout);
        }

        // Debounce: wait 300ms before checking
        this._availabilityCheckTimeout = setTimeout(async () => {
            if (!dates || dates.length === 0) return;

            const furnitureIds = this.state.selectedFurniture.map(f => f.id);
            if (furnitureIds.length === 0) return;

            try {
                const response = await fetch(`${this.options.apiBaseUrl}/reservations/check-availability`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
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
     * @param {Array} conflicts - List of conflicts
     * @param {Array} selectedDates - All selected dates
     */
    showAvailabilityWarning(conflicts, selectedDates) {
        // Find or create warning element
        let warningEl = this.furnitureChips?.parentElement?.querySelector('.availability-warning');
        if (!warningEl) {
            warningEl = document.createElement('div');
            warningEl.className = 'availability-warning';
            this.furnitureChips?.parentElement?.appendChild(warningEl);
        }

        // Get furniture numbers for display
        const furnitureMap = {};
        this.state.selectedFurniture.forEach(f => {
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
        const warningEl = this.furnitureChips?.parentElement?.querySelector('.availability-warning');
        if (warningEl) {
            warningEl.style.display = 'none';
        }
    }

    // =========================================================================
    // CONFLICT RESOLUTION
    // =========================================================================

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
                this.state.conflictResolutionMode = false;
                this.panel.classList.remove('minimized');
            },
            onRemoveDate: (date) => {
                // Update the DatePicker when a date is removed from conflict modal
                if (this.datePicker) {
                    this.datePicker.removeDate(date);
                }
            }
        });
    }

    /**
     * Handle conflict error from API - show the conflict modal
     * @param {Object} result - API response with unavailable array
     * @param {Array} selectedDates - All selected dates
     */
    handleConflictError(result, selectedDates) {
        this.initConflictModal();

        const originalFurniture = this.state.selectedFurniture.map(f => f.id);

        // Save customer data for retry - the DOM might get reset during conflict resolution
        this.state.savedCustomerForRetry = {
            customerId: this.customerIdInput.value,
            customerSource: this.customerSourceInput.value,
            selectedGuest: this.state.selectedGuest,
            selectedCustomer: this.state.selectedCustomer,
            chargeToRoom: this.chargeToRoomCheckbox?.checked || false,
            numPeople: parseInt(this.numPeopleInput.value) || 2,
            notes: this.notesInput?.value || '',
            preferences: [...this.state.preferences]
        };

        this.conflictModal.show(
            result.unavailable,
            selectedDates,
            originalFurniture
        );

        this.state.conflictResolutionMode = true;
    }

    /**
     * Handle navigation to a conflict day - minimize panel and navigate map
     * @param {string} date - Date to navigate to
     * @param {Array} conflicts - Conflicts for this date
     */
    handleNavigateToConflictDay(date, conflicts) {
        // Minimize the panel
        this.panel.classList.add('minimized');

        // Get original selection for this date (or all furniture if not set)
        const originalSelection = this.state.furnitureByDate[date] ||
                                  this.state.selectedFurniture.map(f => f.id);

        // Build furniture number map for display
        const furnitureMap = {};
        this.state.selectedFurniture.forEach(f => {
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
     * @param {Object} furnitureByDate - {date: [furniture_ids]}
     */
    async retryWithPerDayFurniture(furnitureByDate) {
        const selectedDates = Object.keys(furnitureByDate).sort();

        if (selectedDates.length === 0) {
            this.showToast('No hay fechas seleccionadas', 'warning');
            return;
        }

        // Validate all dates have furniture selections
        const missingDates = selectedDates.filter(d => !furnitureByDate[d]?.length);
        if (missingDates.length > 0) {
            this.showToast('Selecciona mobiliario para todas las fechas', 'warning');
            return;
        }

        // Show loading state
        this.createBtn.disabled = true;
        this.createBtn.querySelector('.save-text').style.display = 'none';
        this.createBtn.querySelector('.save-loading').style.display = 'flex';

        try {
            // Use saved customer data from conflict resolution - PRIORITIZE saved values
            // because DOM might have been reset during conflict resolution flow
            const saved = this.state.savedCustomerForRetry || {};

            // In conflict resolution, always use saved data if available
            const customerId = saved.customerId || this.customerIdInput.value;
            const customerSource = saved.customerSource || this.customerSourceInput.value || 'customer';

            console.log('[RetryReservation] Customer data:', {
                savedCustomerId: saved.customerId,
                domCustomerId: this.customerIdInput.value,
                finalCustomerId: customerId,
                savedSource: saved.customerSource,
                domSource: this.customerSourceInput.value,
                finalSource: customerSource
            });

            if (!customerId) {
                throw new Error('Cliente requerido');
            }

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

            // Build payload with furniture_by_date, using saved values as fallback
            const numPeople = parseInt(this.numPeopleInput.value) || saved.numPeople || 2;
            const notes = this.notesInput?.value?.trim() || saved.notes || '';
            const preferences = this.state.preferences?.length > 0 ? this.state.preferences : (saved.preferences || []);
            const chargeToRoom = this.chargeToRoomCheckbox?.checked ?? saved.chargeToRoom ?? false;

            const payload = {
                customer_id: finalCustomerId,
                dates: selectedDates,
                furniture_by_date: furnitureByDate,  // Per-day furniture selections
                num_people: numPeople,
                time_slot: 'all_day',
                notes: notes,
                preferences: preferences,
                // SG-06: Include charge_to_room (only for hotel guests)
                charge_to_room: chargeToRoom
            };

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
                this.state.conflictResolutionMode = false;
                this.state.savedCustomerForRetry = null;  // Clear saved data after success
                this.panel.classList.remove('minimized');
                this.close();

                // Notify callback
                if (this.options.onSave) {
                    this.options.onSave(result.reservation);
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
            this.showToast(error.message, 'error');
        } finally {
            // Reset button state
            this.createBtn.disabled = false;
            this.createBtn.querySelector('.save-text').style.display = 'inline';
            this.createBtn.querySelector('.save-loading').style.display = 'none';
        }
    }

    // =========================================================================
    // SAFEGUARD CHECKS
    // =========================================================================

    /**
     * Run all safeguard checks before creating reservation
     * @param {string} customerId - Customer or hotel guest ID
     * @param {string} customerSource - 'customer' or 'hotel_guest'
     * @param {Array} selectedDates - Array of date strings (YYYY-MM-DD)
     * @returns {Object} { proceed: boolean, viewExisting: number|null }
     */
    async runSafeguardChecks(customerId, customerSource, selectedDates) {
        // SG-05: Check for past dates
        const pastDateResult = await this.checkPastDates(selectedDates);
        if (!pastDateResult.proceed) {
            return { proceed: false };
        }

        // SG-03: Check hotel stay dates (only for hotel guests)
        if (customerSource === 'hotel_guest' && this.state.selectedGuest) {
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
        if (this.state.selectedFurniture.length > 1) {
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
        const guest = this.state.selectedGuest;
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
        const numPeople = parseInt(this.numPeopleInput?.value) || 2;
        const capacity = this.calculateCapacity();

        // SG-04: More people than furniture capacity
        if (numPeople > capacity) {
            const action = await SafeguardModal.showCapacityWarning(numPeople, capacity);

            if (action === 'adjust') {
                this.numPeopleInput.value = capacity;
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
     * @param {Array} selectedDates - Array of date strings (YYYY-MM-DD)
     * @returns {Object} { proceed: boolean }
     */
    async checkFurnitureAvailability(selectedDates) {
        try {
            const furnitureIds = this.state.selectedFurniture.map(f => f.id);

            if (furnitureIds.length === 0 || selectedDates.length === 0) {
                return { proceed: true };
            }

            const response = await fetch(`${this.options.apiBaseUrl}/reservations/check-availability`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    furniture_ids: furnitureIds,
                    dates: selectedDates
                })
            });

            if (!response.ok) {
                console.error('Availability check failed:', response.status);
                return { proceed: true }; // Fail open
            }

            const result = await response.json();

            if (!result.all_available && result.unavailable && result.unavailable.length > 0) {
                console.log('[Safeguard] Furniture conflicts found:', result.unavailable);

                // Get furniture numbers for display
                const furnitureMap = {};
                this.state.selectedFurniture.forEach(f => {
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
                    this.handleConflictError({ unavailable: conflicts }, selectedDates);
                    return { proceed: false, conflictResolution: true };
                }

                // For single-day reservations, show simple error modal
                await SafeguardModal.showFurnitureConflictError(conflicts);
                return { proceed: false };
            }

            return { proceed: true };

        } catch (error) {
            console.error('Furniture availability check error:', error);
            // On error, allow to proceed (fail open)
            return { proceed: true };
        }
    }

    /**
     * SG-07: Check if selected furniture is contiguous (no gaps with occupied furniture)
     * Only checks if more than 1 furniture is selected
     * @param {string} date - Date to check contiguity for (uses first selected date)
     * @returns {Object} { proceed: boolean }
     */
    async checkFurnitureContiguity(date) {
        try {
            const furnitureIds = this.state.selectedFurniture.map(f => f.id);

            // Only check contiguity when multiple furniture selected
            if (furnitureIds.length <= 1) {
                return { proceed: true };
            }

            const response = await fetch(`${this.options.apiBaseUrl}/reservations/validate-contiguity`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    furniture_ids: furnitureIds,
                    date: date
                })
            });

            if (!response.ok) {
                console.error('Contiguity check failed:', response.status);
                return { proceed: true }; // Fail open
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
            // On error, allow to proceed (fail open)
            return { proceed: true };
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
                    `${this.options.apiBaseUrl}/reservations/check-duplicate?${params.toString()}`
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
                        this.close();
                        return { proceed: false, viewExisting: result.existing_reservation.id };
                    }
                    console.log('[Safeguard] User cancelled duplicate creation');
                    return { proceed: false };
                }
            }

            return { proceed: true };

        } catch (error) {
            console.error('Duplicate check error:', error);
            // On error, allow to proceed (fail open)
            return { proceed: true };
        }
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NewReservationPanel;
}
