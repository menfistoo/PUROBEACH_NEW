/**
 * Waitlist API Module
 * Centralizes all API calls for the WaitlistManager
 *
 * All functions are pure and take their dependencies as parameters,
 * making them easy to test and reuse.
 */

// =============================================================================
// PENDING & HISTORY ENTRIES
// =============================================================================

/**
 * Load pending waitlist entries for a specific date
 * @param {string} apiBaseUrl - Base API URL (e.g., '/beach/api')
 * @param {string} date - Date in YYYY-MM-DD format
 * @returns {Promise<{success: boolean, entries: Array, count: number, error?: string}>}
 */
export async function loadPendingEntries(apiBaseUrl, date) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist?date=${date}`);
        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                entries: data.entries || [],
                count: data.count || 0
            };
        } else {
            return {
                success: false,
                entries: [],
                count: 0,
                error: data.error || 'Error al cargar lista'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error loading pending entries', error);
        return {
            success: false,
            entries: [],
            count: 0,
            error: 'Error de conexion'
        };
    }
}

/**
 * Load waitlist history entries for a specific date
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} date - Date in YYYY-MM-DD format
 * @returns {Promise<{success: boolean, entries: Array, error?: string}>}
 */
export async function loadHistoryEntries(apiBaseUrl, date) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist/history?date=${date}`);
        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                entries: data.entries || []
            };
        } else {
            return {
                success: false,
                entries: [],
                error: data.error || 'Error al cargar historial'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error loading history entries', error);
        return {
            success: false,
            entries: [],
            error: 'Error de conexion'
        };
    }
}

// =============================================================================
// DROPDOWN OPTIONS
// =============================================================================

/**
 * Load zones for dropdown selection
 * @param {string} apiBaseUrl - Base API URL
 * @returns {Promise<Array>} Array of zone objects with id and name
 */
export async function loadZones(apiBaseUrl) {
    try {
        const response = await fetch(`${apiBaseUrl}/zones`);
        const data = await response.json();

        if (data.success && data.zones) {
            return data.zones;
        }
        return [];
    } catch (error) {
        console.error('WaitlistAPI: Error loading zones', error);
        return [];
    }
}

/**
 * Load furniture types for dropdown selection
 * @param {string} apiBaseUrl - Base API URL
 * @returns {Promise<Array>} Array of furniture type objects
 */
export async function loadFurnitureTypes(apiBaseUrl) {
    try {
        const response = await fetch(`${apiBaseUrl}/furniture-types`);
        const data = await response.json();

        if (data.success && data.furniture_types) {
            return data.furniture_types;
        }
        return [];
    } catch (error) {
        console.error('WaitlistAPI: Error loading furniture types', error);
        return [];
    }
}

/**
 * Load all dropdown options (zones and furniture types) in parallel
 * @param {string} apiBaseUrl - Base API URL
 * @returns {Promise<{zones: Array, furnitureTypes: Array}>}
 */
export async function loadDropdownOptions(apiBaseUrl) {
    const [zones, furnitureTypes] = await Promise.all([
        loadZones(apiBaseUrl),
        loadFurnitureTypes(apiBaseUrl)
    ]);

    return { zones, furnitureTypes };
}

/**
 * Load available packages
 * @param {string} apiBaseUrl - Base API URL
 * @returns {Promise<Array>} Array of package objects
 */
export async function loadPackages(apiBaseUrl) {
    try {
        const response = await fetch(`${apiBaseUrl}/packages`);
        const data = await response.json();

        if (data.success && data.packages) {
            return data.packages;
        }
        return [];
    } catch (error) {
        console.error('WaitlistAPI: Error loading packages', error);
        return [];
    }
}

// =============================================================================
// ENTRY STATUS UPDATES
// =============================================================================

/**
 * Update a waitlist entry's status
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {number} entryId - Waitlist entry ID
 * @param {string} newStatus - New status value (contacted, declined, no_answer)
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function updateEntryStatus(apiBaseUrl, csrfToken, entryId, newStatus) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist/${entryId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ status: newStatus })
        });

        const data = await response.json();

        if (data.success) {
            return { success: true };
        } else {
            return {
                success: false,
                error: data.error || 'Error al actualizar'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error updating entry status', error);
        return {
            success: false,
            error: 'Error de conexion'
        };
    }
}

/**
 * Mark a waitlist entry as converted to a reservation
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {number} entryId - Waitlist entry ID
 * @param {number} reservationId - Created reservation ID
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function markEntryAsConverted(apiBaseUrl, csrfToken, entryId, reservationId) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist/${entryId}/convert`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ reservation_id: reservationId })
        });

        const data = await response.json();

        if (data.success) {
            return { success: true };
        } else {
            return {
                success: false,
                error: data.error || 'Error al convertir'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error marking as converted', error);
        return {
            success: false,
            error: 'Error de conexion'
        };
    }
}

// =============================================================================
// ENTRY CREATION & UPDATE
// =============================================================================

/**
 * Create a new waitlist entry
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {Object} payload - Entry data
 * @returns {Promise<{success: boolean, entry?: Object, message?: string, error?: string}>}
 */
export async function createEntry(apiBaseUrl, csrfToken, payload) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                entry: data.entry,
                message: data.message || 'Agregado a lista de espera'
            };
        } else {
            return {
                success: false,
                error: data.error || 'Error al crear entrada'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error creating entry', error);
        return {
            success: false,
            error: error.message || 'Error de conexion'
        };
    }
}

/**
 * Update an existing waitlist entry
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {number} entryId - Entry ID to update
 * @param {Object} payload - Updated entry data
 * @returns {Promise<{success: boolean, entry?: Object, error?: string}>}
 */
export async function updateEntry(apiBaseUrl, csrfToken, entryId, payload) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist/${entryId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                entry: data.entry
            };
        } else {
            return {
                success: false,
                error: data.error || 'Error al actualizar entrada'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error updating entry', error);
        return {
            success: false,
            error: error.message || 'Error de conexion'
        };
    }
}

// =============================================================================
// SEARCH FUNCTIONS
// =============================================================================

/**
 * Search for hotel guests by room number or name
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} query - Search query (room number or name)
 * @returns {Promise<{success: boolean, guests: Array}>}
 */
export async function searchHotelGuests(apiBaseUrl, query) {
    try {
        const response = await fetch(
            `${apiBaseUrl}/hotel-guests/search?q=${encodeURIComponent(query)}`
        );
        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                guests: data.guests || []
            };
        }
        return { success: false, guests: [] };
    } catch (error) {
        console.error('WaitlistAPI: Error searching hotel guests', error);
        return { success: false, guests: [] };
    }
}

/**
 * Search for external customers
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} query - Search query (name or phone)
 * @returns {Promise<{success: boolean, customers: Array}>}
 */
export async function searchCustomers(apiBaseUrl, query) {
    try {
        const response = await fetch(
            `${apiBaseUrl}/customers/search?q=${encodeURIComponent(query)}&type=externo`
        );
        const data = await response.json();

        if (data.success || data.customers) {
            return {
                success: true,
                customers: data.customers || []
            };
        }
        return { success: false, customers: [] };
    } catch (error) {
        console.error('WaitlistAPI: Error searching customers', error);
        return { success: false, customers: [] };
    }
}

// =============================================================================
// CUSTOMER CONVERSION
// =============================================================================

/**
 * Convert a hotel guest to a customer record
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {number} hotelGuestId - Hotel guest ID to convert
 * @returns {Promise<{success: boolean, customer?: Object, error?: string}>}
 */
export async function convertHotelGuestToCustomer(apiBaseUrl, csrfToken, hotelGuestId) {
    try {
        const response = await fetch(`${apiBaseUrl}/customers/from-hotel-guest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ hotel_guest_id: parseInt(hotelGuestId) })
        });

        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                customer: data.customer
            };
        } else {
            return {
                success: false,
                error: data.error || 'Error al convertir huesped'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error converting hotel guest', error);
        return {
            success: false,
            error: error.message || 'Error de conexion'
        };
    }
}

// =============================================================================
// COMPOSITE OPERATIONS
// =============================================================================

/**
 * Submit a waitlist entry (handles both create and edit modes)
 * Automatically converts hotel guest to customer if needed
 *
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {Object} options - Submission options
 * @param {string} options.customerType - 'interno' or 'externo'
 * @param {number|null} options.customerId - Existing customer ID
 * @param {number|null} options.hotelGuestId - Hotel guest ID (for interno)
 * @param {Object} options.payload - Entry data payload
 * @param {number|null} options.editingEntryId - Entry ID if editing, null if creating
 * @returns {Promise<{success: boolean, message?: string, error?: string}>}
 */
export async function submitEntry(apiBaseUrl, csrfToken, options) {
    const { customerType, customerId, hotelGuestId, payload, editingEntryId } = options;

    try {
        let finalCustomerId = customerId;

        // If interno (hotel guest), convert to customer first
        if (customerType === 'interno' && hotelGuestId && !customerId) {
            const convertResult = await convertHotelGuestToCustomer(
                apiBaseUrl,
                csrfToken,
                hotelGuestId
            );

            if (!convertResult.success) {
                return {
                    success: false,
                    error: convertResult.error
                };
            }
            finalCustomerId = convertResult.customer.id;
        }

        // Add customer ID to payload if we have one
        if (finalCustomerId) {
            payload.customer_id = parseInt(finalCustomerId);
        }

        // Determine if this is an edit or create
        if (editingEntryId) {
            const result = await updateEntry(apiBaseUrl, csrfToken, editingEntryId, payload);
            return {
                success: result.success,
                message: result.success ? 'Entrada actualizada' : undefined,
                error: result.error
            };
        } else {
            const result = await createEntry(apiBaseUrl, csrfToken, payload);
            return {
                success: result.success,
                message: result.message,
                error: result.error
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error submitting entry', error);
        return {
            success: false,
            error: error.message || 'Error de conexion'
        };
    }
}
