/**
 * CustomerHandler - Manages customer selection, creation, and display
 * Handles customer search, inline creation form, hotel guest integration
 */
class CustomerHandler {
    constructor(panel) {
        this.panel = panel;
        this.state = {
            selectedCustomer: null,
            selectedGuest: null,
            roomGuests: []
        };

        // Initialize create customer form handlers
        this.initCreateCustomerForm();
    }

    /**
     * Initialize create customer form event handlers
     */
    initCreateCustomerForm() {
        const cancelBtn = document.getElementById('newPanelCancelCreateBtn');
        const saveBtn = document.getElementById('newPanelSaveCustomerBtn');

        cancelBtn?.addEventListener('click', () => this.hideCreateCustomerForm());
        saveBtn?.addEventListener('click', () => this.saveNewCustomer());
    }

    /**
     * Show the inline create customer form
     * @param {Object} prefillData - Data to pre-fill the form with
     * @param {string} prefillData.first_name - First name
     * @param {string} prefillData.last_name - Last name
     * @param {string} prefillData.phone - Phone number
     * @param {string} prefillData.email - Email address
     * @param {string} prefillData.language - Language code
     */
    showCreateCustomerForm(prefillData = {}) {
        const createForm = document.getElementById('newPanelCreateCustomerForm');
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const firstNameInput = document.getElementById('newCustFirstName');
        const lastNameInput = document.getElementById('newCustLastName');
        const phoneInput = document.getElementById('newCustPhone');
        const emailInput = document.getElementById('newCustEmail');
        const languageSelect = document.getElementById('newCustLanguage');

        if (!createForm) return;

        // Hide search wrapper
        searchWrapper.style.display = 'none';

        // Pre-fill fields if provided
        if (prefillData.first_name) {
            firstNameInput.value = prefillData.first_name;
        }
        if (prefillData.last_name) {
            lastNameInput.value = prefillData.last_name;
        }
        if (prefillData.phone && phoneInput) {
            phoneInput.value = prefillData.phone;
        }
        if (prefillData.email && emailInput) {
            emailInput.value = prefillData.email;
        }
        if (prefillData.language && languageSelect) {
            languageSelect.value = prefillData.language;
        }

        // Show create form
        createForm.style.display = 'block';
        firstNameInput?.focus();
    }

    /**
     * Hide the inline create customer form
     */
    hideCreateCustomerForm() {
        const createForm = document.getElementById('newPanelCreateCustomerForm');
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const errorEl = document.getElementById('newCustError');

        if (!createForm) return;

        // Clear form
        document.getElementById('newCustFirstName').value = '';
        document.getElementById('newCustLastName').value = '';
        document.getElementById('newCustPhone').value = '';
        document.getElementById('newCustEmail').value = '';
        document.getElementById('newCustLanguage').value = '';
        if (errorEl) errorEl.style.display = 'none';

        // Hide form, show search
        createForm.style.display = 'none';
        searchWrapper.style.display = 'block';
        document.getElementById('newPanelCustomerSearch').value = '';
    }

    /**
     * Save the new customer from the inline form
     */
    async saveNewCustomer() {
        const firstName = document.getElementById('newCustFirstName')?.value.trim() || '';
        const lastName = document.getElementById('newCustLastName')?.value.trim() || '';
        const phone = document.getElementById('newCustPhone')?.value.trim() || '';
        const email = document.getElementById('newCustEmail')?.value.trim() || '';
        const language = document.getElementById('newCustLanguage')?.value || '';
        const saveBtn = document.getElementById('newPanelSaveCustomerBtn');

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
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando...';

        try {
            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/customers/create`, {
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
                this.hideCreateCustomerForm();
                this.handleNewCustomerCreated(result.customer);
            } else {
                this.showCreateError(result.error || 'Error al crear cliente');
            }
        } catch (error) {
            console.error('Error creating customer:', error);
            this.showCreateError('Error de conexion');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-check"></i> Crear Cliente';
        }
    }

    /**
     * Show error in create form
     */
    showCreateError(message) {
        const errorEl = document.getElementById('newCustError');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
            setTimeout(() => {
                errorEl.style.display = 'none';
            }, 3000);
        }
    }

    /**
     * Handle newly created customer from inline form
     */
    handleNewCustomerCreated(customer) {
        document.getElementById('newPanelCustomerId').value = customer.id;
        document.getElementById('newPanelCustomerSource').value = 'customer';
        this.state.selectedCustomer = customer;
        this.state.selectedGuest = null;

        // Show customer display
        this.showCustomerDisplay(customer);

        // Hide guest selector (external customers don't have room guests)
        this.hideGuestSelector();

        // Set num_people from the form if provided (only if not manually edited)
        const numPeopleInput = document.getElementById('newPanelNumPeople');
        if (customer.num_people && numPeopleInput && !this.panel.numPeopleManuallyEdited) {
            numPeopleInput.value = customer.num_people;
        }

        // Clear preferences (new customer has no preferences yet)
        this.panel.clearPreferences();

        // Calculate pricing after customer creation
        this.panel.pricingCalculator.calculateAndDisplayPricing();
    }

    /**
     * Auto-fill preferences and notes from customer record
     */
    async autoFillCustomerData(customer) {
        this.state.selectedCustomer = customer;

        // Show customer display with details
        this.showCustomerDisplay(customer);

        // Clear current preferences first
        this.panel.clearPreferences();

        // If customer has preferences, activate matching chips
        if (customer.preferences && customer.preferences.length > 0) {
            customer.preferences.forEach(prefCode => {
                const chip = document.querySelector(`#newPanelPreferenceChips .pref-chip[data-pref="${prefCode}"]`);
                if (chip) {
                    chip.classList.add('active');
                    if (!this.panel.state.preferences.includes(prefCode)) {
                        this.panel.state.preferences.push(prefCode);
                    }
                }
            });
            // Update hidden input
            const prefsInput = document.getElementById('newPanelPreferences');
            if (prefsInput) {
                prefsInput.value = this.panel.state.preferences.join(',');
            }
        }

        // If customer has tags, activate matching tag chips
        if (customer.tags && customer.tags.length > 0) {
            customer.tags.forEach(tagId => {
                const chip = this.panel.tagChipsContainer?.querySelector(`.tag-chip[data-tag-id="${tagId}"]`);
                if (chip) {
                    chip.classList.add('active');
                    if (!this.panel.state.selectedTags.includes(tagId)) {
                        this.panel.state.selectedTags.push(tagId);
                    }
                }
            });
        }

        // Auto-fill notes from customer record
        const notesInput = document.getElementById('newPanelNotes');
        if (customer.notes && notesInput) {
            let notes = customer.notes;
            // If showing dates in UI, remove date patterns from notes (legacy data cleanup)
            if (isInterno && customer.room_number) {
                notes = notes
                    .replace(/huesped\s+hotel\s*\([^)]*llegada[^)]*salida[^)]*\)/gi, '')
                    .replace(/check[- ]?in:?\s*[\d\-\/]+/gi, '')
                    .replace(/check[- ]?out:?\s*[\d\-\/]+/gi, '')
                    .replace(/entrada:?\s*[\d\-\/]+/gi, '')
                    .replace(/salida:?\s*[\d\-\/]+/gi, '')
                    .replace(/llegada:?\s*[\d\-\/]+/gi, '')
                    .replace(/\d{1,4}[\/\-]\d{1,2}[\/\-]\d{1,4}\s*[-–]\s*\d{1,4}[\/\-]\d{1,2}[\/\-]\d{1,4}/g, '')
                    .replace(/\s*[,;]\s*[,;]\s*/g, ', ')
                    .replace(/^\s*[,;]\s*/g, '')
                    .replace(/\s*[,;]\s*$/g, '')
                    .trim();
            }
            notesInput.value = notes;
        }

        // Calculate pricing after customer selection
        this.panel.pricingCalculator.calculateAndDisplayPricing();

        // For internal customers with a room number, fetch room guests
        if (isInterno && customer.room_number) {
            await this.fetchRoomGuests(customer);
        } else {
            // External customer - no guest selector
            this.hideGuestSelector();
            this.state.selectedGuest = null;
        }
    }

    /**
     * Fetch room guests for internal customer or hotel guest
     */
    async fetchRoomGuests(customer) {
        try {
            const response = await fetch(
                `${this.panel.options.apiBaseUrl}/hotel-guests/lookup?room=${encodeURIComponent(customer.room_number)}`
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

            // Auto-set num_people based on guest count (only if not manually edited)
            const capacity = this.panel.calculateCapacity();
            const numPeopleInput = document.getElementById('newPanelNumPeople');
            if (numPeopleInput && guestCount > 0 && !this.panel.numPeopleManuallyEdited) {
                numPeopleInput.value = guestCount;
            }

            // Check capacity warning
            if (guestCount > capacity) {
                this.panel.showCapacityWarning(guestCount, capacity);
            } else {
                this.panel.hideCapacityWarning();
            }

        } catch (error) {
            console.error('Error fetching room guests for customer:', error);
            this.hideGuestSelector();
            this.state.selectedGuest = null;
        }
    }

    /**
     * Show customer display with expanded details
     */
    showCustomerDisplay(customer) {
        // Hide search wrapper, show customer display
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const customerDisplay = document.getElementById('newPanelCustomerDisplay');
        const clearBtn = document.getElementById('newPanelCustomerClearBtn');

        if (searchWrapper) searchWrapper.style.display = 'none';
        if (customerDisplay) customerDisplay.style.display = 'block';
        if (clearBtn) clearBtn.style.display = 'flex';

        // Initials
        const firstName = customer.first_name || customer.guest_name?.split(' ')[0] || '';
        const lastName = customer.last_name || customer.guest_name?.split(' ').slice(1).join(' ') || '';
        const initials = (firstName.charAt(0) + lastName.charAt(0)).toUpperCase() || '--';
        const initialsEl = document.getElementById('newPanelCustomerInitials');
        if (initialsEl) initialsEl.textContent = initials;

        // Avatar class
        const avatarEl = document.getElementById('newPanelCustomerAvatar');
        if (avatarEl) {
            avatarEl.className = 'customer-avatar';
            if (customer.vip_status || customer.vip_code) {
                avatarEl.classList.add('vip');
            } else if (customer.customer_type === 'interno' || customer.source === 'hotel_guest') {
                avatarEl.classList.add('interno');
            }
        }

        // Name
        const fullName = customer.display_name || customer.full_name ||
            `${customer.first_name || ''} ${customer.last_name || ''}`.trim() ||
            customer.guest_name || 'Sin nombre';
        const nameEl = document.getElementById('newPanelCustomerName');
        if (nameEl) nameEl.textContent = fullName;

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
            const span = document.createElement('span');
            span.textContent = customer.phone;
            meta.push(`<i class="fas fa-phone"></i> ${span.innerHTML}`);
        }
        const metaEl = document.getElementById('newPanelCustomerMeta');
        if (metaEl) {
            metaEl.innerHTML = meta.join(' <span class="mx-1">•</span> ');
        }

        // Details grid
        this.renderCustomerDetailsGrid(customer);
    }

    /**
     * Render customer details inline (room, check-in, check-out, booking ref)
     */
    renderCustomerDetailsGrid(customer) {
        // Room
        const roomEl = document.getElementById('newPanelCustomerRoom');
        const roomItem = document.getElementById('newPanelRoomItem');
        if (roomEl) {
            const room = customer.room_number;
            if (room) {
                roomEl.textContent = `Hab. ${room}`;
                if (roomItem) roomItem.style.display = 'inline-flex';
            } else {
                if (roomItem) roomItem.style.display = 'none';
            }
        }

        // Check-in date
        const checkinEl = document.getElementById('newPanelCustomerCheckin');
        const checkinItem = document.getElementById('newPanelCheckinItem');
        if (checkinEl) {
            const arrivalDate = customer.arrival_date;
            if (arrivalDate) {
                checkinEl.textContent = this.formatDateShort(arrivalDate);
                if (checkinItem) checkinItem.style.display = 'inline-flex';
            } else {
                if (checkinItem) checkinItem.style.display = 'none';
            }
        }

        // Check-out date
        const checkoutEl = document.getElementById('newPanelCustomerCheckout');
        const checkoutItem = document.getElementById('newPanelCheckoutItem');
        if (checkoutEl) {
            const departureDate = customer.departure_date;
            if (departureDate) {
                checkoutEl.textContent = this.formatDateShort(departureDate);
                if (checkoutItem) checkoutItem.style.display = 'inline-flex';
            } else {
                if (checkoutItem) checkoutItem.style.display = 'none';
            }
        }

        // Booking reference
        const bookingEl = document.getElementById('newPanelCustomerBookingRef');
        const bookingItem = document.getElementById('newPanelBookingItem');
        if (bookingEl) {
            const bookingRef = customer.booking_reference;
            if (bookingRef) {
                bookingEl.textContent = bookingRef;
                if (bookingItem) bookingItem.style.display = 'inline-flex';
            } else {
                if (bookingItem) bookingItem.style.display = 'none';
            }
        }

        // Hide details row if no details (external customer without hotel info)
        const detailsGrid = document.getElementById('newPanelCustomerDetailsGrid');
        if (detailsGrid) {
            const hasDetails = customer.room_number || customer.arrival_date ||
                               customer.departure_date || customer.booking_reference;
            detailsGrid.style.display = hasDetails ? 'flex' : 'none';
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
        document.getElementById('newPanelCustomerId').value = '';
        document.getElementById('newPanelCustomerSource').value = 'customer';
        this.state.selectedCustomer = null;
        this.state.selectedGuest = null;

        // Hide customer display, show search wrapper
        const customerDisplay = document.getElementById('newPanelCustomerDisplay');
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const clearBtn = document.getElementById('newPanelCustomerClearBtn');

        if (customerDisplay) customerDisplay.style.display = 'none';
        if (searchWrapper) searchWrapper.style.display = 'block';
        if (clearBtn) clearBtn.style.display = 'none';

        // Clear and reset search
        if (this.panel.customerSearch) {
            this.panel.customerSearch.clear();
        }

        // Hide guest selector
        this.hideGuestSelector();

        // Clear notes
        const notesInput = document.getElementById('newPanelNotes');
        if (notesInput) notesInput.value = '';

        // Clear preferences
        this.panel.clearPreferences();

        // Focus on search input
        document.getElementById('newPanelCustomerSearch')?.focus();
    }

    /**
     * Handle hotel guest selection - fetch room guests and populate selector
     */
    async handleHotelGuestSelect(guest) {
        document.getElementById('newPanelCustomerId').value = guest.id;
        document.getElementById('newPanelCustomerSource').value = 'hotel_guest';
        this.state.selectedGuest = guest;

        // Show customer display with guest details
        this.showCustomerDisplay(guest);

        // Hotel guests don't have preferences yet, clear them
        this.panel.clearPreferences();

        // But they may have notes from the PMS
        const notesInput = document.getElementById('newPanelNotes');
        if (guest.notes && notesInput) {
            notesInput.value = guest.notes;
        }

        // Calculate pricing after hotel guest selection
        this.panel.pricingCalculator.calculateAndDisplayPricing();

        // Fetch all guests in the room
        await this.fetchRoomGuestsForGuest(guest);
    }

    /**
     * Fetch all room guests (for hotel guest selection)
     */
    async fetchRoomGuestsForGuest(guest) {
        try {
            const response = await fetch(
                `${this.panel.options.apiBaseUrl}/hotel-guests/lookup?room=${encodeURIComponent(guest.room_number)}`
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

            // Auto-set num_people based on guest count (only if not manually edited)
            const capacity = this.panel.calculateCapacity();
            const numPeopleInput = document.getElementById('newPanelNumPeople');
            if (numPeopleInput && !this.panel.numPeopleManuallyEdited) {
                numPeopleInput.value = guestCount;
            }

            // Check if we need more furniture for all guests
            if (guestCount > capacity) {
                this.panel.showCapacityWarning(guestCount, capacity);
            } else {
                this.panel.hideCapacityWarning();
            }

        } catch (error) {
            console.error('Error fetching room guests:', error);
            this.hideGuestSelector();
            // Set default num_people to 1 if fetch fails (only if not manually edited)
            const numPeopleInput = document.getElementById('newPanelNumPeople');
            if (numPeopleInput && !this.panel.numPeopleManuallyEdited) {
                numPeopleInput.value = 1;
            }
        }
    }

    /**
     * Show the guest selector dropdown
     */
    showGuestSelector(selectedGuest, guestCount) {
        const selectorWrapper = document.getElementById('newPanelGuestSelectorWrapper');
        const guestSelector = document.getElementById('newPanelGuestSelector');
        const guestCountDisplay = document.getElementById('newPanelGuestCount');

        if (!selectorWrapper || !guestSelector) return;

        // Update guest count display
        if (guestCountDisplay) {
            guestCountDisplay.textContent = guestCount;
        }

        // Populate the selector with all room guests
        guestSelector.innerHTML = this.state.roomGuests.map(g => {
            const isSelected = g.id === selectedGuest.id;
            const mainBadge = g.is_main_guest ? ' (Principal)' : '';
            return `<option value="${g.id}" ${isSelected ? 'selected' : ''}>${g.guest_name}${mainBadge}</option>`;
        }).join('');

        // Show the wrapper
        selectorWrapper.style.display = 'block';
    }

    /**
     * Hide the guest selector
     */
    hideGuestSelector() {
        const selectorWrapper = document.getElementById('newPanelGuestSelectorWrapper');
        if (selectorWrapper) {
            selectorWrapper.style.display = 'none';
        }
        this.state.roomGuests = [];
    }

    /**
     * Handle guest selector change
     */
    onGuestSelectorChange() {
        const guestSelector = document.getElementById('newPanelGuestSelector');
        const selectedId = parseInt(guestSelector.value);
        const guest = this.state.roomGuests.find(g => g.id === selectedId);

        if (guest) {
            document.getElementById('newPanelCustomerId').value = guest.id;
            this.state.selectedGuest = guest;

            // Update customer display with new guest info
            this.showCustomerDisplay(guest);

            // Update notes if the guest has any
            const notesInput = document.getElementById('newPanelNotes');
            if (notesInput) {
                notesInput.value = guest.notes || '';
            }
        }
    }
}
