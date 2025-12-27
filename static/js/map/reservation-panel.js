/**
 * Reservation Panel Module
 * A slide-in side panel for viewing/editing reservations from the beach map.
 * Works with the HTML template in _reservation_panel.html
 */
class ReservationPanel {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '/beach/api',
            animationDuration: 300,
            swipeThreshold: 100,
            onClose: null,
            onSave: null,
            onStateChange: null,
            onFurnitureReassign: null,
            onCustomerChange: null,
            ...options
        };

        // State
        this.state = {
            isOpen: false,
            isCollapsed: false,
            mode: 'view', // 'view', 'edit', or 'reassignment'
            reservationId: null,
            currentDate: null,
            data: null,           // Current reservation data
            originalData: null,   // Original data for dirty checking
            isDirty: false,
            isLoading: false,
            isSubmitting: false,
            numPeopleManuallyEdited: false  // Track if user manually edited num_people
        };

        // Reassignment state (separate for clarity)
        this.reassignmentState = {
            originalFurniture: [],    // Original furniture IDs for reference
            selectedFurniture: [],    // New selection (furniture IDs)
            maxAllowed: 2             // Max furniture = num_people
        };

        // Preferences editing state
        this.preferencesEditState = {
            isEditing: false,
            allPreferences: [],       // All available preferences from server
            selectedCodes: [],        // Currently selected preference codes
            originalCodes: []         // Original codes for dirty checking
        };

        // Touch gesture tracking
        this.swipe = {
            startX: 0,
            currentX: 0,
            isDragging: false
        };

        // Customer search debounce timer
        this.customerSearchTimer = null;

        // Map data reference (set by BeachMap)
        this.mapData = null;

        // Initialize
        this.cacheElements();
        this.attachListeners();
    }

    /**
     * Cache DOM element references
     */
    cacheElements() {
        this.panel = document.getElementById('reservationPanel');
        this.backdrop = document.getElementById('reservationPanelBackdrop');

        if (!this.panel || !this.backdrop) {
            console.warn('ReservationPanel: Required elements not found in DOM');
            return;
        }

        // Header elements
        this.toggleBtn = document.getElementById('panelToggleBtn');
        this.toggleIcon = document.getElementById('panelToggleIcon');
        this.closeBtn = document.getElementById('panelCloseBtn');
        this.editBtn = document.getElementById('panelEditBtn');
        this.editIcon = document.getElementById('panelEditIcon');
        this.ticketEl = document.getElementById('panelTicket');
        this.dateEl = document.getElementById('panelDate');

        // Loading/content containers
        this.loadingEl = document.getElementById('panelLoading');
        this.contentEl = document.getElementById('panelContent');

        // Customer section - Compact display
        this.customerSection = document.getElementById('customerSection');
        this.customerDisplay = document.getElementById('customerDisplay');
        this.customerName = document.getElementById('customerName');
        this.customerRoomBadge = document.getElementById('customerRoomBadge');
        this.customerRoom = document.getElementById('customerRoom');
        this.customerVipBadge = document.getElementById('customerVipBadge');
        this.customerHotelInfo = document.getElementById('customerHotelInfo');
        this.customerCheckin = document.getElementById('customerCheckin');
        this.customerCheckout = document.getElementById('customerCheckout');
        this.customerBookingRef = document.getElementById('customerBookingRef');
        this.customerBookingItem = document.getElementById('customerBookingItem');
        this.customerContact = document.getElementById('customerContact');
        this.customerPhone = document.getElementById('customerPhone');
        this.customerChangeBtn = document.getElementById('customerChangeBtn');
        this.customerSearchWrapper = document.getElementById('customerSearchWrapper');
        this.customerSearchInput = document.getElementById('panelCustomerSearch');
        this.customerSearchResults = document.getElementById('panelCustomerResults');

        // Preferences section
        this.preferencesSection = document.getElementById('preferencesSection');
        this.preferencesChipsContainer = document.getElementById('panelPreferencesChips');
        this.preferencesViewMode = document.getElementById('preferencesViewMode');
        this.preferencesEditMode = document.getElementById('preferencesEditMode');
        this.preferencesAllChips = document.getElementById('panelAllPreferencesChips');

        // State section
        this.stateChipsContainer = document.getElementById('panelStateChips');

        // Furniture section - View mode
        this.furnitureViewMode = document.getElementById('furnitureViewMode');
        this.furnitureChipsContainer = document.getElementById('panelFurnitureChips');
        this.furnitureChangeBtn = document.getElementById('panelChangeFurnitureBtn');
        this.furnitureSummary = document.getElementById('furnitureSummary');

        // Furniture section - Reassignment mode
        this.furnitureReassignmentMode = document.getElementById('furnitureReassignmentMode');
        this.reassignmentOriginalChips = document.getElementById('reassignmentOriginalChips');
        this.reassignmentNewChips = document.getElementById('reassignmentNewChips');
        this.reassignmentCounter = document.getElementById('reassignmentCounter');
        this.reassignmentCancelBtn = document.getElementById('reassignmentCancelBtn');
        this.reassignmentSaveBtn = document.getElementById('reassignmentSaveBtn');

        // Details section - View mode
        this.detailsViewMode = document.getElementById('detailsViewMode');
        this.detailNumPeople = document.getElementById('detailNumPeople');
        this.detailNotes = document.getElementById('detailNotes');

        // Details section - Edit mode
        this.detailsEditMode = document.getElementById('detailsEditMode');
        this.editNumPeople = document.getElementById('editNumPeople');
        this.editNotes = document.getElementById('editNotes');

        // View more link
        this.viewMoreLink = document.getElementById('viewMoreLink');

        // Footer
        this.footer = document.getElementById('panelFooter');
        this.cancelBtn = document.getElementById('panelCancelBtn');
        this.saveBtn = document.getElementById('panelSaveBtn');

        // CSRF token
        this.csrfToken = document.getElementById('panelCsrfToken')?.value ||
                         document.querySelector('meta[name="csrf-token"]')?.content || '';
    }

    /**
     * Attach event listeners
     */
    attachListeners() {
        if (!this.panel) return;

        // Toggle button (collapse/expand)
        this.toggleBtn?.addEventListener('click', () => this.toggleCollapse());

        // Close button
        this.closeBtn?.addEventListener('click', () => this.close());

        // Backdrop click
        this.backdrop?.addEventListener('click', () => this.close());

        // Edit button toggle
        this.editBtn?.addEventListener('click', () => this.toggleEditMode());

        // Cancel button
        this.cancelBtn?.addEventListener('click', () => this.exitEditMode(true));

        // Save button
        this.saveBtn?.addEventListener('click', () => this.saveChanges());

        // Customer change button
        this.customerChangeBtn?.addEventListener('click', () => this.showCustomerSearch());

        // Customer search input
        this.customerSearchInput?.addEventListener('input', (e) => this.handleCustomerSearch(e));

        // Furniture change button
        this.furnitureChangeBtn?.addEventListener('click', () => this.enterReassignmentMode());

        // Reassignment mode buttons
        this.reassignmentCancelBtn?.addEventListener('click', () => this.exitReassignmentMode(true));
        this.reassignmentSaveBtn?.addEventListener('click', () => this.saveReassignment());

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.state.isOpen) {
                if (this.state.mode === 'reassignment') {
                    this.exitReassignmentMode(true);
                } else if (this.state.mode === 'edit') {
                    this.exitEditMode(true);
                } else {
                    this.close();
                }
            }
        });

        // Swipe to close (mobile)
        this.setupSwipeGestures();

        // Track dirty state on edit inputs
        this.editNumPeople?.addEventListener('input', () => {
            this.state.numPeopleManuallyEdited = true;
            this.markDirty();
        });
        this.editNotes?.addEventListener('input', () => this.markDirty());
    }

    /**
     * Setup swipe-to-close gesture for mobile
     */
    setupSwipeGestures() {
        if (!this.panel) return;

        this.panel.addEventListener('touchstart', (e) => {
            // Only start swipe if touching the header or panel edge
            const touch = e.touches[0];
            const panelRect = this.panel.getBoundingClientRect();

            // Allow swipe from right edge (within 40px) or header
            const isRightEdge = touch.clientX > panelRect.right - 40;
            const isHeader = e.target.closest('.panel-header');

            if (isRightEdge || isHeader) {
                this.swipe.isDragging = true;
                this.swipe.startX = touch.clientX;
                this.panel.classList.add('dragging');
            }
        });

        this.panel.addEventListener('touchmove', (e) => {
            if (!this.swipe.isDragging) return;

            this.swipe.currentX = e.touches[0].clientX;
            const deltaX = this.swipe.currentX - this.swipe.startX;

            // Only allow dragging right (positive delta)
            if (deltaX > 0) {
                this.panel.style.transform = `translateX(${deltaX}px)`;
            }
        });

        this.panel.addEventListener('touchend', () => {
            if (!this.swipe.isDragging) return;

            this.swipe.isDragging = false;
            this.panel.classList.remove('dragging');

            const deltaX = this.swipe.currentX - this.swipe.startX;

            if (deltaX > this.options.swipeThreshold) {
                this.close();
            } else {
                // Snap back
                this.panel.style.transform = '';
            }
        });
    }

    /**
     * Set map data reference for states, colors, etc.
     */
    setMapData(data) {
        this.mapData = data;
    }

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

        this.state.reservationId = reservationId;
        this.state.currentDate = date;
        this.state.mode = mode;
        this.state.isOpen = true;
        this.state.isDirty = false;
        this.state.numPeopleManuallyEdited = false;  // Reset flag when opening new reservation

        // Show loading state
        this.showLoading(true);

        // Show panel
        this.backdrop.classList.add('show');
        this.panel.classList.add('open');
        document.body.style.overflow = 'hidden';

        // Adjust map canvas if on tablet/desktop
        const mapWrapper = document.querySelector('.map-canvas-wrapper');
        if (mapWrapper && window.innerWidth >= 768) {
            mapWrapper.classList.add('panel-open');
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

        this.state.isOpen = false;
        this.state.isCollapsed = false;
        this.state.mode = 'view';
        this.state.isDirty = false;

        // Hide panel
        this.backdrop.classList.remove('show');
        this.panel.classList.remove('open');
        this.panel.classList.remove('collapsed');
        this.panel.classList.remove('edit-mode');
        this.panel.style.transform = '';
        document.body.style.overflow = '';

        // Remove map canvas adjustment
        const mapWrapper = document.querySelector('.map-canvas-wrapper');
        if (mapWrapper) {
            mapWrapper.classList.remove('panel-open');
        }

        // Hide customer search
        this.hideCustomerSearch();

        // Callback
        if (this.options.onClose) {
            this.options.onClose();
        }
    }

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
     */
    async enterEditMode() {
        this.state.mode = 'edit';
        this.panel.classList.add('edit-mode');

        // Update edit button icon
        if (this.editIcon) {
            this.editIcon.className = 'fas fa-eye';
        }

        // Highlight furniture on map
        this.highlightReservationFurniture();

        // Show edit fields, hide view fields
        if (this.detailsViewMode) this.detailsViewMode.style.display = 'none';
        if (this.detailsEditMode) this.detailsEditMode.style.display = 'grid';

        // Pre-fill edit fields with current values (only if not manually edited)
        if (this.state.data) {
            const data = this.state.data;
            if (this.editNumPeople && !this.state.numPeopleManuallyEdited) {
                this.editNumPeople.value = data.reservation?.num_people || 1;
            }
            if (this.editNotes) {
                this.editNotes.value = data.reservation?.notes || '';
            }
        }

        // Store original data for dirty checking
        this.state.originalData = {
            num_people: this.editNumPeople?.value,
            notes: this.editNotes?.value
        };

        // Also enter preferences edit mode
        await this.enterPreferencesEditMode();
    }

    /**
     * Exit edit mode
     * @param {boolean} discard - Whether to discard changes
     */
    exitEditMode(discard = false) {
        if (discard && this.state.isDirty) {
            if (!confirm('Tienes cambios sin guardar. ¿Descartar cambios?')) {
                return;
            }
        }

        this.state.mode = 'view';
        this.state.isDirty = false;
        this.state.numPeopleManuallyEdited = false;  // Reset flag when exiting edit mode
        this.panel.classList.remove('edit-mode');

        // Update edit button icon
        if (this.editIcon) {
            this.editIcon.className = 'fas fa-pen';
        }

        // Remove furniture highlight
        this.unhighlightReservationFurniture();

        // Show view fields, hide edit fields
        if (this.detailsViewMode) this.detailsViewMode.style.display = 'grid';
        if (this.detailsEditMode) this.detailsEditMode.style.display = 'none';

        // Exit preferences edit mode
        this.exitPreferencesEditMode(discard);

        // Hide customer search
        this.hideCustomerSearch();
    }

    /**
     * Mark the form as dirty (has unsaved changes)
     */
    markDirty() {
        this.state.isDirty = true;
    }

    /**
     * Show/hide loading state
     */
    showLoading(show) {
        this.state.isLoading = show;
        if (this.loadingEl) this.loadingEl.style.display = show ? 'flex' : 'none';
        if (this.contentEl) this.contentEl.style.display = show ? 'none' : 'block';
    }

    /**
     * Load reservation data from API
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

    /**
     * Render all panel content
     */
    renderContent(data) {
        const res = data.reservation;
        const customer = data.customer;

        // Header
        this.ticketEl.textContent = `Reserva #${res.ticket_number || res.id}`;
        this.dateEl.textContent = this.formatDate(res.reservation_date || res.start_date);

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
    }

    /**
     * Render customer section (compact layout)
     */
    renderCustomerSection(customer) {
        if (!customer) {
            if (this.customerName) this.customerName.textContent = 'Cliente no encontrado';
            if (this.customerRoomBadge) this.customerRoomBadge.style.display = 'none';
            if (this.customerVipBadge) this.customerVipBadge.style.display = 'none';
            if (this.customerHotelInfo) this.customerHotelInfo.style.display = 'none';
            if (this.customerContact) this.customerContact.style.display = 'none';
            return;
        }

        // Customer name
        if (this.customerName) {
            this.customerName.textContent = customer.full_name ||
                `${customer.first_name || ''} ${customer.last_name || ''}`.trim() || 'Sin nombre';
        }

        // Room badge (next to name)
        if (this.customerRoomBadge && this.customerRoom) {
            if (customer.room_number) {
                this.customerRoom.textContent = customer.room_number;
                this.customerRoomBadge.style.display = 'inline-flex';
            } else {
                this.customerRoomBadge.style.display = 'none';
            }
        }

        // VIP badge
        if (this.customerVipBadge) {
            this.customerVipBadge.style.display = customer.vip_status ? 'inline-flex' : 'none';
        }

        // Hotel info (check-in, check-out, booking ref) - for hotel guests
        const isHotelGuest = customer.customer_type === 'interno' &&
            (customer.arrival_date || customer.departure_date);

        if (this.customerHotelInfo) {
            if (isHotelGuest) {
                this.customerHotelInfo.style.display = 'flex';

                // Check-in
                if (this.customerCheckin) {
                    this.customerCheckin.textContent = customer.arrival_date
                        ? this.formatDateShort(customer.arrival_date)
                        : '-';
                }

                // Check-out
                if (this.customerCheckout) {
                    this.customerCheckout.textContent = customer.departure_date
                        ? this.formatDateShort(customer.departure_date)
                        : '-';
                }

                // Booking reference
                if (this.customerBookingRef && this.customerBookingItem) {
                    if (customer.booking_reference) {
                        this.customerBookingRef.textContent = customer.booking_reference;
                        this.customerBookingItem.style.display = 'inline-flex';
                    } else {
                        this.customerBookingItem.style.display = 'none';
                    }
                }
            } else {
                this.customerHotelInfo.style.display = 'none';
            }
        }

        // Contact info (phone) - for external customers
        if (this.customerContact && this.customerPhone) {
            if (!isHotelGuest && customer.phone) {
                this.customerPhone.innerHTML = `<i class="fas fa-phone"></i> ${customer.phone}`;
                this.customerContact.style.display = 'block';
            } else {
                this.customerContact.style.display = 'none';
            }
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
     * Render preferences section with chips
     */
    renderPreferencesSection(customer) {
        if (!this.preferencesChipsContainer) return;

        const preferences = customer?.preferences || [];

        // Hide section if no preferences
        if (this.preferencesSection) {
            this.preferencesSection.style.display = preferences.length > 0 ? 'block' : 'none';
        }

        if (preferences.length === 0) {
            this.preferencesChipsContainer.innerHTML =
                '<span class="text-muted small">Sin preferencias registradas</span>';
            return;
        }

        const chipsHtml = preferences.map(pref => {
            // Icons are stored as 'fa-umbrella', need to add 'fas ' prefix
            let icon = pref.icon || 'fa-heart';
            if (icon && !icon.startsWith('fas ') && !icon.startsWith('far ') && !icon.startsWith('fab ')) {
                icon = 'fas ' + icon;
            }
            return `
                <span class="preference-chip" title="${pref.name}">
                    <i class="${icon}"></i>
                    <span>${pref.name}</span>
                </span>
            `;
        }).join('');

        this.preferencesChipsContainer.innerHTML = chipsHtml;
    }

    /**
     * Enter preferences edit mode
     */
    async enterPreferencesEditMode() {
        // Load all available preferences if not already loaded
        if (this.preferencesEditState.allPreferences.length === 0) {
            await this.loadAllPreferences();
        }

        // Get current customer preferences
        const customerPrefs = this.state.data?.customer?.preferences || [];
        this.preferencesEditState.selectedCodes = customerPrefs.map(p => p.code);
        this.preferencesEditState.originalCodes = [...this.preferencesEditState.selectedCodes];
        this.preferencesEditState.isEditing = true;

        // Render all preferences as toggleable chips
        this.renderAllPreferencesChips();

        // Show edit mode, hide view mode
        if (this.preferencesViewMode) this.preferencesViewMode.style.display = 'none';
        if (this.preferencesEditMode) this.preferencesEditMode.style.display = 'block';

        // Always show the section in edit mode
        if (this.preferencesSection) this.preferencesSection.style.display = 'block';
    }

    /**
     * Exit preferences edit mode
     */
    exitPreferencesEditMode(discard = false) {
        this.preferencesEditState.isEditing = false;

        // Show view mode, hide edit mode
        if (this.preferencesViewMode) this.preferencesViewMode.style.display = 'block';
        if (this.preferencesEditMode) this.preferencesEditMode.style.display = 'none';

        // Re-render view mode with current preferences
        const customer = this.state.data?.customer;
        if (customer) {
            this.renderPreferencesSection(customer);
        }
    }

    /**
     * Load all available preferences from server
     */
    async loadAllPreferences() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/preferences`);
            if (response.ok) {
                const result = await response.json();
                this.preferencesEditState.allPreferences = result.preferences || [];
            }
        } catch (error) {
            console.error('Failed to load preferences:', error);
        }
    }

    /**
     * Render all preferences as toggleable chips
     */
    renderAllPreferencesChips() {
        if (!this.preferencesAllChips) return;

        const allPrefs = this.preferencesEditState.allPreferences;
        const selectedCodes = this.preferencesEditState.selectedCodes;

        if (allPrefs.length === 0) {
            this.preferencesAllChips.innerHTML =
                '<span class="text-muted small">No hay preferencias disponibles</span>';
            return;
        }

        const chipsHtml = allPrefs.map(pref => {
            const isSelected = selectedCodes.includes(pref.code);
            let icon = pref.icon || 'fa-heart';
            if (icon && !icon.startsWith('fas ') && !icon.startsWith('far ') && !icon.startsWith('fab ')) {
                icon = 'fas ' + icon;
            }
            return `
                <span class="preference-chip toggleable ${isSelected ? 'selected' : ''}"
                      data-code="${pref.code}"
                      title="${pref.name}">
                    <i class="${icon}"></i>
                    <span>${pref.name}</span>
                </span>
            `;
        }).join('');

        this.preferencesAllChips.innerHTML = chipsHtml;

        // Attach click handlers
        this.preferencesAllChips.querySelectorAll('.preference-chip.toggleable').forEach(chip => {
            chip.addEventListener('click', () => this.togglePreference(chip.dataset.code));
        });
    }

    /**
     * Toggle a preference selection
     */
    togglePreference(code) {
        const index = this.preferencesEditState.selectedCodes.indexOf(code);
        if (index >= 0) {
            this.preferencesEditState.selectedCodes.splice(index, 1);
        } else {
            this.preferencesEditState.selectedCodes.push(code);
        }
        // Re-render chips to update selection state
        this.renderAllPreferencesChips();
    }

    /**
     * Render state section with chips
     */
    renderStateSection(reservation) {
        const currentState = reservation.current_state;
        const states = this.mapData?.states || [];
        const activeStates = states.filter(s => s.active);

        if (activeStates.length === 0) {
            this.stateChipsContainer.innerHTML = `
                <span class="state-chip active" style="background: ${reservation.display_color || '#6C757D'}; border-color: ${reservation.display_color || '#6C757D'};">
                    ${currentState || 'Sin estado'}
                </span>
            `;
            return;
        }

        const chipsHtml = activeStates.map(state => {
            const isActive = state.name === currentState;
            const bgColor = isActive ? state.color : 'transparent';
            const textColor = isActive ? '#FFFFFF' : 'var(--color-secondary)';

            return `
                <button type="button"
                        class="state-chip ${isActive ? 'active' : ''}"
                        data-state="${state.name}"
                        data-color="${state.color}"
                        style="background: ${bgColor}; border-color: ${state.color}; color: ${textColor};">
                    ${state.name}
                </button>
            `;
        }).join('');

        this.stateChipsContainer.innerHTML = chipsHtml;

        // Attach click handlers
        this.stateChipsContainer.querySelectorAll('.state-chip').forEach(chip => {
            chip.addEventListener('click', (e) => this.handleStateChange(e));
        });
    }

    /**
     * Render furniture section
     */
    renderFurnitureSection(reservation) {
        const furniture = reservation.furniture || [];
        const currentDate = this.state.currentDate;

        // Filter furniture for current date (if assignment_date exists) or show all
        let displayFurniture = furniture;
        if (furniture.length > 0 && furniture[0].assignment_date) {
            displayFurniture = furniture.filter(f => {
                // Parse any date format to YYYY-MM-DD for comparison
                const assignDate = this.parseDateToYMD(f.assignment_date);
                return assignDate === currentDate;
            });
        }

        if (displayFurniture.length === 0) {
            this.furnitureChipsContainer.innerHTML =
                '<span class="text-muted">Sin mobiliario asignado</span>';
            this.furnitureSummary.textContent = '';
            return;
        }

        const chipsHtml = displayFurniture.map(f => `
            <span class="furniture-chip">
                <span class="furniture-type-icon">${this.getFurnitureIcon(f.type_name || f.furniture_type)}</span>
                ${f.number || f.furniture_number || `#${f.furniture_id || f.id}`}
            </span>
        `).join('');

        this.furnitureChipsContainer.innerHTML = chipsHtml;

        // Summary
        const totalCapacity = displayFurniture.reduce((sum, f) => sum + (f.capacity || 2), 0);
        this.furnitureSummary.textContent =
            `${displayFurniture.length} ${displayFurniture.length === 1 ? 'item' : 'items'} • Capacidad: ${totalCapacity} personas`;
    }

    /**
     * Render details section
     */
    renderDetailsSection(reservation) {
        // Number of people
        this.detailNumPeople.textContent = reservation.num_people || 1;

        // Notes
        const notes = reservation.notes || reservation.observations;
        if (notes) {
            this.detailNotes.textContent = notes;
            this.detailNotes.classList.remove('empty');
        } else {
            this.detailNotes.textContent = 'Sin notas';
            this.detailNotes.classList.add('empty');
        }

        // Pre-fill edit fields (only if not manually edited)
        if (this.editNumPeople && !this.state.numPeopleManuallyEdited) {
            this.editNumPeople.value = reservation.num_people || 1;
        }
        if (this.editNotes) {
            this.editNotes.value = notes || '';
        }
    }

    /**
     * Handle state change click
     */
    async handleStateChange(event) {
        const chip = event.currentTarget;
        const newState = chip.dataset.state;
        const chipColor = chip.dataset.color;

        // Skip if already active
        if (chip.classList.contains('active')) return;

        // Visual feedback
        const prevActive = this.stateChipsContainer.querySelector('.state-chip.active');
        if (prevActive) {
            prevActive.classList.remove('active');
            prevActive.style.background = 'transparent';
            prevActive.style.color = 'var(--color-secondary)';
        }

        chip.classList.add('active', 'loading');
        chip.style.background = chipColor;
        chip.style.color = '#FFFFFF';

        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/reservations/${this.state.reservationId}/toggle-state`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ state: newState, action: 'set' })
                }
            );

            const result = await response.json();

            if (result.success) {
                // Update local data
                if (this.state.data?.reservation) {
                    this.state.data.reservation.current_state = newState;
                }

                // Callback
                if (this.options.onStateChange) {
                    this.options.onStateChange(this.state.reservationId, newState);
                }

                this.showToast(`Estado cambiado a ${newState}`, 'success');
            } else {
                throw new Error(result.error || 'Error al cambiar estado');
            }

        } catch (error) {
            console.error('State change error:', error);
            // Revert visual state
            chip.classList.remove('active');
            chip.style.background = 'transparent';
            chip.style.color = 'var(--color-secondary)';
            if (prevActive) {
                prevActive.classList.add('active');
                prevActive.style.background = prevActive.dataset.color;
                prevActive.style.color = '#FFFFFF';
            }
            this.showToast(error.message, 'error');
        } finally {
            chip.classList.remove('loading');
        }
    }

    /**
     * Enter reassignment mode (in-panel furniture selection)
     */
    enterReassignmentMode() {
        const reservation = this.state.data?.reservation;
        if (!reservation) return;

        // Get current furniture for this date
        const currentFurniture = (reservation.furniture || []).filter(f => {
            const assignDate = this.parseDateToYMD(f.assignment_date);
            return assignDate === this.state.currentDate;
        });

        // Set up reassignment state
        this.reassignmentState.originalFurniture = currentFurniture.map(f =>
            f.furniture_id || f.id
        );
        this.reassignmentState.selectedFurniture = []; // Start with empty selection
        this.reassignmentState.maxAllowed = reservation.num_people || 2;

        // Switch mode
        this.state.mode = 'reassignment';
        this.panel.classList.add('reassignment-mode');
        this.backdrop.classList.add('reassignment-mode');

        // Hide view mode, show reassignment mode
        if (this.furnitureViewMode) this.furnitureViewMode.style.display = 'none';
        if (this.furnitureReassignmentMode) this.furnitureReassignmentMode.style.display = 'flex';

        // Render original furniture chips
        this.renderOriginalFurnitureChips(currentFurniture);

        // Update counter and clear new chips
        this.updateReassignmentUI();

        // Show hint toast
        this.showToast(`Selecciona hasta ${this.reassignmentState.maxAllowed} mobiliarios en el mapa`, 'info');

        // Notify map to enter reassignment mode (for highlighting available furniture)
        if (this.options.onFurnitureReassign) {
            this.options.onFurnitureReassign(
                reservation.id,
                currentFurniture,
                reservation.num_people,
                'enter' // Signal entering mode, not closing
            );
        }
    }

    /**
     * Exit reassignment mode
     * @param {boolean} cancel - Whether to cancel without saving
     */
    exitReassignmentMode(cancel = false) {
        if (this.state.mode !== 'reassignment') return;

        // Switch back to view mode
        this.state.mode = 'view';
        this.panel.classList.remove('reassignment-mode');
        this.backdrop.classList.remove('reassignment-mode');

        // Show view mode, hide reassignment mode
        if (this.furnitureViewMode) this.furnitureViewMode.style.display = 'block';
        if (this.furnitureReassignmentMode) this.furnitureReassignmentMode.style.display = 'none';

        // Clear reassignment state
        this.reassignmentState.selectedFurniture = [];

        // Notify map to exit reassignment mode
        if (this.options.onFurnitureReassign) {
            this.options.onFurnitureReassign(
                this.state.reservationId,
                [],
                0,
                'exit' // Signal exiting mode
            );
        }

        if (cancel) {
            this.showToast('Cambio de mobiliario cancelado', 'info');
        }
    }

    /**
     * Toggle furniture selection (called from map when furniture is clicked)
     * @param {number} furnitureId - The furniture ID to toggle
     * @param {object} furnitureData - Full furniture data {id, number, type_name, capacity}
     * @returns {boolean} - Whether the toggle was successful
     */
    toggleFurnitureSelection(furnitureId, furnitureData = null) {
        if (this.state.mode !== 'reassignment') return false;

        const index = this.reassignmentState.selectedFurniture.findIndex(
            f => (f.id || f) === furnitureId
        );

        if (index >= 0) {
            // Remove from selection
            this.reassignmentState.selectedFurniture.splice(index, 1);
        } else {
            // Check max limit
            if (this.reassignmentState.selectedFurniture.length >= this.reassignmentState.maxAllowed) {
                this.showToast(`Maximo ${this.reassignmentState.maxAllowed} mobiliarios permitidos`, 'warning');
                return false;
            }
            // Add to selection
            const furnitureInfo = furnitureData || { id: furnitureId };
            this.reassignmentState.selectedFurniture.push(furnitureInfo);
        }

        // Update UI
        this.updateReassignmentUI();
        return true;
    }

    /**
     * Check if panel is in reassignment mode
     */
    isInReassignmentMode() {
        return this.state.mode === 'reassignment';
    }

    /**
     * Update reassignment UI (counter and chips)
     */
    updateReassignmentUI() {
        const selected = this.reassignmentState.selectedFurniture;
        const max = this.reassignmentState.maxAllowed;

        // Calculate total capacity
        const totalCapacity = selected.reduce((sum, f) => sum + (f.capacity || 2), 0);
        const numPeople = this.state.data?.reservation?.num_people || max;

        // Determine capacity status
        let capacityStatus = '';
        let capacityClass = '';
        if (selected.length > 0) {
            if (totalCapacity < numPeople) {
                capacityStatus = ` ⚠️ Capacidad insuficiente: ${totalCapacity}/${numPeople} personas`;
                capacityClass = 'capacity-insufficient';
            } else if (totalCapacity > numPeople) {
                capacityStatus = ` ℹ️ Capacidad excedente: ${totalCapacity}/${numPeople} personas`;
                capacityClass = 'capacity-excess';
            } else {
                capacityStatus = ` ✓ Capacidad correcta: ${totalCapacity}/${numPeople} personas`;
                capacityClass = 'capacity-correct';
            }
        }

        // Update counter with capacity info
        if (this.reassignmentCounter) {
            this.reassignmentCounter.innerHTML = `
                ${selected.length} / ${max} seleccionados
                <span class="${capacityClass}" style="display: block; font-size: 11px; margin-top: 4px;">
                    ${capacityStatus}
                </span>
            `;
        }

        // Update new chips
        if (this.reassignmentNewChips) {
            if (selected.length === 0) {
                this.reassignmentNewChips.innerHTML =
                    '<span class="text-muted" style="font-size: 12px;">Ninguno seleccionado</span>';
            } else {
                const chipsHtml = selected.map(f => `
                    <span class="furniture-chip">
                        <span class="furniture-type-icon">${this.getFurnitureIcon(f.type_name)}</span>
                        ${f.number || f.furniture_number || `#${f.id}`}
                        <span style="font-size: 10px; opacity: 0.7;">(${f.capacity || 2}p)</span>
                    </span>
                `).join('');
                this.reassignmentNewChips.innerHTML = chipsHtml;
            }
        }

        // Enable/disable save button based on selection and capacity
        if (this.reassignmentSaveBtn) {
            const hasSelection = selected.length > 0;
            const hasInsufficientCapacity = totalCapacity < numPeople;

            // Disable button if no selection OR insufficient capacity
            this.reassignmentSaveBtn.disabled = !hasSelection || hasInsufficientCapacity;

            // Update button text to indicate why it's disabled
            if (hasInsufficientCapacity) {
                const icon = this.reassignmentSaveBtn.querySelector('i');
                const iconHtml = icon ? `<i class="${icon.className}"></i> ` : '';
                this.reassignmentSaveBtn.innerHTML = `${iconHtml}Capacidad insuficiente`;
            } else {
                this.reassignmentSaveBtn.innerHTML = '<i class="fas fa-check"></i> Guardar cambios';
            }
        }
    }

    /**
     * Render original furniture chips (dimmed, for reference)
     */
    renderOriginalFurnitureChips(furniture) {
        if (!this.reassignmentOriginalChips) return;

        if (furniture.length === 0) {
            this.reassignmentOriginalChips.innerHTML =
                '<span class="text-muted" style="font-size: 12px;">Sin mobiliario</span>';
            return;
        }

        const chipsHtml = furniture.map(f => `
            <span class="furniture-chip">
                <span class="furniture-type-icon">${this.getFurnitureIcon(f.type_name || f.furniture_type)}</span>
                ${f.number || f.furniture_number || `#${f.furniture_id || f.id}`}
            </span>
        `).join('');

        this.reassignmentOriginalChips.innerHTML = chipsHtml;
    }

    /**
     * Save furniture reassignment
     */
    async saveReassignment() {
        if (this.state.mode !== 'reassignment') return;
        if (this.reassignmentState.selectedFurniture.length === 0) {
            this.showToast('Selecciona al menos un mobiliario', 'warning');
            return;
        }

        // Show loading state
        if (this.reassignmentSaveBtn) {
            this.reassignmentSaveBtn.disabled = true;
            this.reassignmentSaveBtn.innerHTML =
                '<span class="spinner-border spinner-border-sm"></span> Guardando...';
        }

        try {
            const furnitureIds = this.reassignmentState.selectedFurniture.map(
                f => f.id || f.furniture_id || f
            );

            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/reassign-furniture`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({
                        furniture_ids: furnitureIds,
                        date: this.state.currentDate
                    })
                }
            );

            const result = await response.json();

            if (result.success) {
                // Exit reassignment mode
                this.exitReassignmentMode(false);

                // Reload reservation data to get updated furniture
                await this.loadReservation(this.state.reservationId, this.state.currentDate);

                // Show success message
                let message = 'Mobiliario actualizado exitosamente';

                // Show capacity warning if present
                if (result.warning) {
                    this.showToast(result.warning, 'warning');
                    // Delay success message slightly so both toasts are visible
                    setTimeout(() => {
                        this.showToast(message, 'success');
                    }, 100);
                } else {
                    this.showToast(message, 'success');
                }

                // Notify map to refresh
                if (this.options.onSave) {
                    this.options.onSave(this.state.reservationId, { furniture_changed: true });
                }
            } else {
                // Handle error response (e.g., insufficient capacity)
                throw new Error(result.error || 'Error al guardar');
            }

        } catch (error) {
            console.error('Reassignment save error:', error);
            // Show error with more details if available
            const errorMsg = error.message || 'Error al actualizar mobiliario';
            this.showToast(errorMsg, 'error');
        } finally {
            // Reset button state
            if (this.reassignmentSaveBtn) {
                this.reassignmentSaveBtn.disabled = false;
                this.reassignmentSaveBtn.innerHTML =
                    '<i class="fas fa-check"></i> Guardar cambios';
            }
        }
    }

    /**
     * Legacy method for backwards compatibility
     * @deprecated Use enterReassignmentMode() instead
     */
    triggerFurnitureReassign() {
        this.enterReassignmentMode();
    }

    /**
     * Show customer search input
     */
    showCustomerSearch() {
        if (this.customerSearchWrapper) {
            this.customerSearchWrapper.style.display = 'block';
            this.customerSearchInput?.focus();
        }
    }

    /**
     * Hide customer search input
     */
    hideCustomerSearch() {
        if (this.customerSearchWrapper) {
            this.customerSearchWrapper.style.display = 'none';
            if (this.customerSearchInput) this.customerSearchInput.value = '';
            if (this.customerSearchResults) this.customerSearchResults.style.display = 'none';
        }
    }

    /**
     * Handle customer search input
     */
    handleCustomerSearch(event) {
        const query = event.target.value.trim();

        // Clear previous timer
        if (this.customerSearchTimer) {
            clearTimeout(this.customerSearchTimer);
        }

        if (query.length < 2) {
            this.customerSearchResults.style.display = 'none';
            return;
        }

        // Debounce search
        this.customerSearchTimer = setTimeout(() => {
            this.searchCustomers(query);
        }, 300);
    }

    /**
     * Search customers via API
     */
    async searchCustomers(query) {
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/customers/search?q=${encodeURIComponent(query)}`
            );

            if (!response.ok) throw new Error('Error en la busqueda');

            const result = await response.json();
            this.renderCustomerSearchResults(result);

        } catch (error) {
            console.error('Customer search error:', error);
        }
    }

    /**
     * Render customer search results
     */
    renderCustomerSearchResults(result) {
        const customers = result.customers || [];
        const hotelGuests = result.hotel_guests || [];

        if (customers.length === 0 && hotelGuests.length === 0) {
            this.customerSearchResults.innerHTML = `
                <div class="customer-search-item text-muted">
                    No se encontraron resultados
                </div>
            `;
            this.customerSearchResults.style.display = 'block';
            return;
        }

        let html = '';

        // Beach club customers
        customers.forEach(c => {
            html += `
                <div class="customer-search-item" data-customer-id="${c.id}">
                    <div class="fw-semibold">${c.first_name} ${c.last_name}</div>
                    <div class="small text-muted">
                        ${c.customer_type === 'interno' ? `Hab. ${c.room_number || '?'}` : 'Externo'}
                        ${c.vip_status ? '<i class="fas fa-star text-warning ms-1"></i>' : ''}
                    </div>
                </div>
            `;
        });

        // Hotel guests (that aren't already customers)
        hotelGuests.forEach(g => {
            html += `
                <div class="customer-search-item" data-hotel-guest-id="${g.id}">
                    <div class="fw-semibold">${g.first_name} ${g.last_name}</div>
                    <div class="small text-muted">
                        Huesped - Hab. ${g.room_number}
                    </div>
                </div>
            `;
        });

        this.customerSearchResults.innerHTML = html;
        this.customerSearchResults.style.display = 'block';

        // Attach click handlers
        this.customerSearchResults.querySelectorAll('.customer-search-item').forEach(item => {
            item.addEventListener('click', () => this.selectCustomer(item));
        });
    }

    /**
     * Select a customer from search results
     */
    async selectCustomer(item) {
        const customerId = item.dataset.customerId;
        const hotelGuestId = item.dataset.hotelGuestId;

        if (!customerId && !hotelGuestId) return;

        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/change-customer`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({
                        customer_id: customerId ? parseInt(customerId) : null,
                        hotel_guest_id: hotelGuestId ? parseInt(hotelGuestId) : null
                    })
                }
            );

            const result = await response.json();

            if (result.success) {
                // Update local data and re-render customer section
                if (this.state.data) {
                    this.state.data.customer = result.customer;
                }
                this.renderCustomerSection(result.customer);
                this.hideCustomerSearch();

                // Callback
                if (this.options.onCustomerChange) {
                    this.options.onCustomerChange(this.state.reservationId, result.customer);
                }

                this.showToast('Cliente actualizado', 'success');
            } else {
                throw new Error(result.error || 'Error al cambiar cliente');
            }

        } catch (error) {
            console.error('Customer change error:', error);
            this.showToast(error.message, 'error');
        }
    }

    /**
     * Save changes (edit mode)
     */
    async saveChanges() {
        if (this.state.isSubmitting) return;

        const updates = {};
        let hasChanges = false;
        let preferencesChanged = false;

        // Collect changed values
        if (this.editNumPeople && this.editNumPeople.value !== this.state.originalData?.num_people) {
            updates.num_people = parseInt(this.editNumPeople.value) || 1;
            hasChanges = true;
        }

        if (this.editNotes && this.editNotes.value !== this.state.originalData?.notes) {
            updates.observations = this.editNotes.value;
            hasChanges = true;
        }

        // Check if preferences have changed
        const originalCodes = this.preferencesEditState.originalCodes || [];
        const selectedCodes = this.preferencesEditState.selectedCodes || [];
        preferencesChanged = JSON.stringify(originalCodes.sort()) !== JSON.stringify(selectedCodes.sort());

        if (!hasChanges && !preferencesChanged) {
            this.exitEditMode(false);
            return;
        }

        // Show loading state
        this.state.isSubmitting = true;
        this.saveBtn.querySelector('.save-text').style.display = 'none';
        this.saveBtn.querySelector('.save-loading').style.display = 'inline-flex';
        this.saveBtn.disabled = true;

        try {
            // Save reservation updates if any
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

                // Re-render details with new data
                this.renderDetailsSection(this.state.data.reservation);
            }

            // Save preferences if changed
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

            // Exit edit mode
            this.state.isDirty = false;
            this.state.numPeopleManuallyEdited = false;  // Reset flag after successful save
            this.exitEditMode(false);

            // Callback
            if (this.options.onSave) {
                this.options.onSave(this.state.reservationId, {
                    ...updates,
                    preferences_changed: preferencesChanged
                });
            }

            this.showToast('Reserva actualizada', 'success');

        } catch (error) {
            console.error('Save error:', error);
            this.showToast(error.message, 'error');
        } finally {
            this.state.isSubmitting = false;
            this.saveBtn.querySelector('.save-text').style.display = 'inline-flex';
            this.saveBtn.querySelector('.save-loading').style.display = 'none';
            this.saveBtn.disabled = false;
        }
    }

    /**
     * Show error state in panel
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

    // =========================================================================
    // UTILITY METHODS
    // =========================================================================

    /**
     * Get initials from name
     */
    getInitials(firstName, lastName) {
        const first = (firstName || '')[0] || '';
        const last = (lastName || '')[0] || '';
        return (first + last).toUpperCase() || '?';
    }

    /**
     * Format date for display
     */
    formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            // Handle various date formats
            let date;
            if (dateStr.includes('T')) {
                date = new Date(dateStr);
            } else {
                date = new Date(dateStr + 'T00:00:00');
            }

            if (isNaN(date.getTime())) {
                return dateStr; // Return original if parsing fails
            }

            return date.toLocaleDateString('es-ES', {
                weekday: 'short',
                day: 'numeric',
                month: 'short'
            });
        } catch (e) {
            return dateStr;
        }
    }

    /**
     * Parse any date string to YYYY-MM-DD format for comparison
     */
    parseDateToYMD(dateStr) {
        if (!dateStr) return '';
        try {
            // If already in YYYY-MM-DD format
            if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                return dateStr;
            }
            // If ISO format (YYYY-MM-DDTHH:MM:SS)
            const isoMatch = dateStr.match(/^(\d{4}-\d{2}-\d{2})T/);
            if (isoMatch) {
                return isoMatch[1];
            }
            // Any other format - parse with Date and extract components
            const date = new Date(dateStr);
            if (!isNaN(date.getTime())) {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            }
            return dateStr;
        } catch (e) {
            return dateStr;
        }
    }

    /**
     * Get furniture type icon
     */
    getFurnitureIcon(typeName) {
        const icons = {
            'hamaca': '🛏️',
            'balinesa': '🛖',
            'sombrilla': '☂️',
            'mesa': '🪑'
        };
        const lowerType = (typeName || '').toLowerCase();
        for (const [key, icon] of Object.entries(icons)) {
            if (lowerType.includes(key)) return icon;
        }
        return '🪑';
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        if (window.PuroBeach?.showToast) {
            window.PuroBeach.showToast(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }

    /**
     * Highlight reservation's furniture on the map with red aura
     */
    highlightReservationFurniture() {
        if (!this.state.data?.furniture) return;

        // Get furniture IDs for this reservation
        const furnitureIds = this.state.data.furniture.map(f => f.id || f.furniture_id);

        // Find and highlight each furniture element on the map
        furnitureIds.forEach(id => {
            const furnitureEl = document.querySelector(`[data-furniture-id="${id}"]`);
            if (furnitureEl) {
                furnitureEl.classList.add('furniture-editing');
            }
        });
    }

    /**
     * Remove highlight from reservation's furniture
     */
    unhighlightReservationFurniture() {
        // Remove highlight from all furniture elements
        const highlightedElements = document.querySelectorAll('.furniture-editing');
        highlightedElements.forEach(el => {
            el.classList.remove('furniture-editing');
        });
    }

    /**
     * Destroy the panel instance
     */
    destroy() {
        this.close();
        // Remove any event listeners if needed
    }
}

// Export for use
window.ReservationPanel = ReservationPanel;
