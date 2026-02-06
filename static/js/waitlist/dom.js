/**
 * Waitlist DOM Caching Module
 * Cache all DOM element references for the WaitlistManager
 *
 * @module waitlist/dom
 */

/**
 * Cache all DOM elements used by WaitlistManager
 * @returns {Object|null} Object containing all DOM element references, or null if panel not found
 */
export function cacheElements() {
    // Panel elements (check panel first)
    const panel = document.getElementById('waitlistPanel');
    const backdrop = document.getElementById('waitlistPanelBackdrop');

    if (!panel) {
        console.warn('WaitlistManager: Panel element not found');
        return null;
    }

    return {
        // Panel
        panel,
        backdrop,

        // Header
        closeBtn: document.getElementById('waitlistPanelCloseBtn'),
        collapseBtn: document.getElementById('waitlistCollapseBtn'),
        collapseBtnHeader: document.getElementById('waitlistCollapseBtnHeader'),
        addBtn: document.getElementById('waitlistAddBtn'),
        dateDisplay: document.getElementById('waitlistPanelDate'),

        // Tabs
        tabPending: document.getElementById('waitlistTabPending'),
        tabHistory: document.getElementById('waitlistTabHistory'),
        pendingCount: document.getElementById('waitlistPendingCount'),

        // Content
        loadingEl: document.getElementById('waitlistPanelLoading'),
        contentPending: document.getElementById('waitlistContentPending'),
        contentHistory: document.getElementById('waitlistContentHistory'),
        entriesPending: document.getElementById('waitlistEntriesPending'),
        entriesHistory: document.getElementById('waitlistEntriesHistory'),
        emptyPending: document.getElementById('waitlistEmptyPending'),
        emptyHistory: document.getElementById('waitlistEmptyHistory'),

        // Footer
        footerAddBtn: document.getElementById('waitlistFooterAddBtn'),

        // Modal elements
        modal: document.getElementById('waitlistAddModal'),
        modalBackdrop: document.getElementById('waitlistModalBackdrop'),
        modalCloseBtn: document.getElementById('waitlistModalCloseBtn'),
        modalCancelBtn: document.getElementById('waitlistModalCancelBtn'),
        modalSaveBtn: document.getElementById('waitlistModalSaveBtn'),
        addForm: document.getElementById('waitlistAddForm'),

        // Customer type toggles
        typeInterno: document.getElementById('waitlistTypeInterno'),
        typeExterno: document.getElementById('waitlistTypeExterno'),

        // Room search (interno)
        roomSearchGroup: document.getElementById('waitlistRoomSearchGroup'),
        roomSearchInput: document.getElementById('waitlistRoomSearch'),
        roomResults: document.getElementById('waitlistRoomResults'),
        selectedGuestEl: document.getElementById('waitlistSelectedGuest'),
        guestNameEl: document.getElementById('waitlistGuestName'),
        guestRoomEl: document.getElementById('waitlistGuestRoom'),
        clearGuestBtn: document.getElementById('waitlistClearGuest'),

        // Customer search (externo)
        customerSearchGroup: document.getElementById('waitlistCustomerSearchGroup'),
        customerSearchInput: document.getElementById('waitlistCustomerSearch'),
        customerResults: document.getElementById('waitlistCustomerResults'),
        selectedCustomerEl: document.getElementById('waitlistSelectedCustomer'),
        customerNameEl: document.getElementById('waitlistCustomerName'),
        customerPhoneEl: document.getElementById('waitlistCustomerPhone'),
        clearCustomerBtn: document.getElementById('waitlistClearCustomer'),
        createCustomerBtn: document.getElementById('waitlistCreateCustomerBtn'),

        // Form fields
        dateInput: document.getElementById('waitlistDate'),
        numPeopleInput: document.getElementById('waitlistNumPeople'),
        timePreferenceSelect: document.getElementById('waitlistTimePreference'),
        zonePreferenceSelect: document.getElementById('waitlistZonePreference'),
        furnitureTypeSelect: document.getElementById('waitlistFurnitureType'),
        notesInput: document.getElementById('waitlistNotes'),
        reservationTypeRadios: document.querySelectorAll('input[name="reservationType"]'),
        packageGroup: document.getElementById('waitlistPackageGroup'),
        packageSelect: document.getElementById('waitlistPackageSelect'),

        // Hidden fields
        customerIdInput: document.getElementById('waitlistCustomerId'),
        customerTypeInput: document.getElementById('waitlistCustomerType'),
        hotelGuestIdInput: document.getElementById('waitlistHotelGuestId'),

        // CSRF Token
        csrfToken: document.getElementById('waitlistCsrfToken')?.value ||
                   document.querySelector('meta[name="csrf-token"]')?.content || ''
    };
}
