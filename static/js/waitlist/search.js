/**
 * Waitlist Search
 * Room and customer search functionality
 */

import { searchHotelGuests, searchCustomers } from './api.js';
import { renderRoomResults, renderCustomerResults } from './renderers.js';
import { selectGuest, selectCustomer } from './modal.js';

/**
 * Handle room search input
 * @param {Object} context - Manager context
 * @param {Event} e - Input event
 */
export function onRoomSearch(context, e) {
    const query = e.target.value.trim();

    if (context.searchTimeout) {
        clearTimeout(context.searchTimeout);
    }

    if (query.length < 1) {
        if (context.elements.roomResults) {
            context.elements.roomResults.classList.remove('show');
        }
        return;
    }

    context.searchTimeout = setTimeout(
        () => performRoomSearch(context, query),
        context.options.debounceMs
    );
}

/**
 * Perform room search API call
 * @param {Object} context - Manager context
 * @param {string} query - Search query
 */
async function performRoomSearch(context, query) {
    const { elements, options } = context;

    try {
        // Unified search (same endpoint as the new-reservation panel) so the
        // interno results are identical: beach customers + hotel guests, with
        // badges, searchable by name / room / reservation number.
        const response = await fetch(
            `${options.apiBaseUrl}/customers/search?q=${encodeURIComponent(query)}`
        );
        const data = await response.json();
        renderRoomResults(
            elements.roomResults,
            data.customers || [],
            (item) => selectGuest(context, item)
        );
    } catch (error) {
        console.error('WaitlistManager: Error searching rooms', error);
    }
}

/**
 * Handle customer search input
 * @param {Object} context - Manager context
 * @param {Event} e - Input event
 */
export function onCustomerSearch(context, e) {
    const query = e.target.value.trim();

    if (context.searchTimeout) {
        clearTimeout(context.searchTimeout);
    }

    if (query.length < 2) {
        if (context.elements.customerResults) {
            context.elements.customerResults.classList.remove('show');
        }
        return;
    }

    context.searchTimeout = setTimeout(
        () => performCustomerSearch(context, query),
        context.options.debounceMs
    );
}

/**
 * Perform customer search API call
 * @param {Object} context - Manager context
 * @param {string} query - Search query
 */
async function performCustomerSearch(context, query) {
    const { elements, options } = context;

    try {
        const result = await searchCustomers(options.apiBaseUrl, query, 'externo');

        if (result.success || result.customers) {
            renderCustomerResults(
                elements.customerResults,
                result.customers || [],
                (item) => selectCustomer(context, item)
            );
        }
    } catch (error) {
        console.error('WaitlistManager: Error searching customers', error);
    }
}

/**
 * Create a debounced search function
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(fn, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
}
