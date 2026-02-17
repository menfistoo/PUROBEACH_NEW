/**
 * Pricing Mixin for ReservationPanel
 *
 * Handles pricing display and editing functionality, including:
 * - renderPricingSection() - Display pricing in view mode
 * - enterPricingEditMode() - Initialize pricing edit mode
 * - exitPricingEditMode() - Return to view mode
 * - fetchAvailablePackages() - Load available pricing packages
 * - updatePackageSelector() - Update package dropdown UI
 * - calculateAndUpdatePricing() - Calculate pricing based on selections
 *
 * Dependencies:
 * - parseDateToYMD from utils.js
 *
 * Expected instance properties:
 * - pricingSection, detailTotalPrice, detailPricingBreakdown
 * - pricingEditState: { originalPrice, isModified, selectedPackageId, availablePackages, calculatedPrice }
 * - panelFinalPriceInput, panelPriceOverride, panelCalculatedPrice, panelPriceResetBtn
 * - panelPricingTypeSelector, panelPricingTypeSelect, panelPricingDisplay
 * - panelSelectedPackageId, panelPricingBreakdown
 * - editNumPeople
 * - state: { data, currentDate }
 * - options: { apiBaseUrl }
 * - csrfToken
 */

import { escapeHtml, parseDateToYMD } from './utils.js';

// =============================================================================
// PRICING MIXIN
// =============================================================================

/**
 * Mixin that adds pricing functionality to ReservationPanel
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with pricing methods
 */
export const PricingMixin = (Base) => class extends Base {

    // =========================================================================
    // VIEW MODE RENDERING
    // =========================================================================

    /**
     * Render pricing section (view mode)
     *
     * Displays the current price, package name, and/or breakdown.
     * Updates both view mode display and pre-fills edit mode input.
     *
     * @param {Object} reservation - Reservation data with pricing info
     * @param {number} [reservation.final_price] - Final calculated price
     * @param {number} [reservation.total_price] - Total price (legacy)
     * @param {number} [reservation.price] - Base price (legacy fallback)
     * @param {string} [reservation.package_name] - Name of applied package
     * @param {string} [reservation.price_breakdown] - Price breakdown text
     */
    renderPricingSection(reservation) {
        if (!this.pricingSection) return;

        // Get price from reservation (API returns final_price, fallback to total_price/price for backward compat)
        const totalPrice = reservation.final_price || reservation.total_price || reservation.price || 0;
        const packageName = reservation.package_name || null;
        const priceBreakdown = reservation.price_breakdown || null;

        // Store original price for comparison
        this.pricingEditState.originalPrice = totalPrice;

        // Update view mode display
        if (this.detailTotalPrice) {
            this.detailTotalPrice.textContent = `€${parseFloat(totalPrice).toFixed(2)}`;
        }

        // Show package name if available, otherwise show breakdown
        if (this.detailPricingBreakdown) {
            if (packageName) {
                this.detailPricingBreakdown.innerHTML = `<span class="package-name">${escapeHtml(packageName)}</span>`;
                this.detailPricingBreakdown.style.display = 'block';
            } else if (priceBreakdown) {
                this.detailPricingBreakdown.textContent = priceBreakdown;
                this.detailPricingBreakdown.style.display = 'block';
            } else {
                this.detailPricingBreakdown.style.display = 'none';
            }
        }

        // Pre-fill edit mode with current price
        if (this.panelFinalPriceInput) {
            this.panelFinalPriceInput.value = parseFloat(totalPrice).toFixed(2);
        }
    }

    // =========================================================================
    // EDIT MODE MANAGEMENT
    // =========================================================================

    /**
     * Enter pricing edit mode - fetch packages and set up pricing
     *
     * Initializes pricing edit state:
     * - Resets modification flags
     * - Sets current price in input
     * - Clears override and calculated displays
     * - Fetches available packages for the reservation
     * - Fetches minimum consumption policies
     * - Stores calculated price for reference
     */
    async enterPricingEditMode() {
        if (!this.state.data?.reservation) return;

        const reservation = this.state.data.reservation;
        const customer = this.state.data.customer;

        // Reset pricing state
        this.pricingEditState.isModified = false;
        this.pricingEditState.selectedPackageId = reservation.package_id || null;
        this.pricingEditState.selectedPolicyId = reservation.minimum_consumption_policy_id || null;

        // Set current price in input (API returns final_price)
        const currentPrice = reservation.final_price || reservation.total_price || reservation.price || 0;
        if (this.panelFinalPriceInput) {
            this.panelFinalPriceInput.value = parseFloat(currentPrice).toFixed(2);
            this.panelFinalPriceInput.classList.remove('modified');
        }

        // Clear override input
        if (this.panelPriceOverride) {
            this.panelPriceOverride.value = '';
        }

        // Hide calculated price display initially
        if (this.panelCalculatedPrice) {
            this.panelCalculatedPrice.style.display = 'none';
        }

        // Hide reset button initially
        if (this.panelPriceResetBtn) {
            this.panelPriceResetBtn.style.display = 'none';
        }

        // Fetch available packages and policies
        await Promise.all([
            this.fetchAvailablePackages(),
            this.fetchMinConsumptionPolicies()
        ]);

        // Store calculated price for reference
        this.pricingEditState.calculatedPrice = currentPrice;
    }

    /**
     * Exit pricing edit mode
     *
     * Resets edit state and re-renders view mode with current reservation data.
     *
     * @param {boolean} [discard=false] - Whether changes are being discarded (unused but kept for API consistency)
     */
    exitPricingEditMode(discard = false) {
        // Reset state
        this.pricingEditState.isModified = false;

        // Re-render view mode with current reservation data
        const reservation = this.state.data?.reservation;
        if (reservation) {
            this.renderPricingSection(reservation);
        }
    }

    // =========================================================================
    // MINIMUM CONSUMPTION POLICY MANAGEMENT
    // =========================================================================

    /**
     * Fetch minimum consumption policies for dropdown (filtered by customer type)
     */
    async fetchMinConsumptionPolicies() {
        try {
            // Get customer type to filter policies
            const customer = this.state.data?.customer;
            const customerType = customer?.customer_type || 'externo';

            const url = new URL(`${window.location.origin}${this.options.apiBaseUrl}/pricing/minimum-consumption-policies`);
            url.searchParams.set('customer_type', customerType);

            const response = await fetch(url, {
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });

            const result = await response.json();

            if (result.success) {
                this.pricingEditState.availablePolicies = result.policies || [];
                this.updateMinConsumptionPolicySelector();
            }
        } catch (error) {
            console.error('[Pricing] Error fetching min consumption policies:', error);
        }
    }

    /**
     * Update minimum consumption policy selector UI
     */
    updateMinConsumptionPolicySelector() {
        if (!this.panelMinConsumptionSelect) return;

        const policies = this.pricingEditState.availablePolicies;
        const currentPolicyId = this.pricingEditState.selectedPolicyId;

        // Clear and rebuild options
        this.panelMinConsumptionSelect.innerHTML = '<option value="auto">Automático</option>';

        policies.forEach(policy => {
            const option = document.createElement('option');
            option.value = policy.id;

            // Build display text
            let displayText = policy.policy_name;
            if (policy.minimum_amount > 0) {
                const amountStr = policy.calculation_type === 'per_person'
                    ? `${policy.minimum_amount.toFixed(2)}€/pers`
                    : `${policy.minimum_amount.toFixed(2)}€`;
                displayText += ` - ${amountStr}`;
            } else {
                displayText += ' - Sin minimo';
            }

            option.textContent = displayText;
            this.panelMinConsumptionSelect.appendChild(option);
        });

        // Select current policy if any
        if (currentPolicyId) {
            this.panelMinConsumptionSelect.value = currentPolicyId.toString();
        } else {
            this.panelMinConsumptionSelect.value = 'auto';
        }
    }

    // =========================================================================
    // PACKAGE MANAGEMENT
    // =========================================================================

    /**
     * Fetch available packages for the current reservation
     *
     * Makes API call to get packages based on:
     * - Customer type (interno/externo)
     * - Furniture IDs for current date
     * - Reservation date
     * - Number of people
     *
     * Updates availablePackages in state and calls updatePackageSelector()
     */
    async fetchAvailablePackages() {
        if (!this.state.data?.reservation || !this.state.data?.customer) return;

        const reservation = this.state.data.reservation;
        const customer = this.state.data.customer;

        // Determine customer type
        const customerType = customer.customer_type || 'externo';

        // Get furniture IDs for this date
        const furniture = (reservation.furniture || []).filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === this.state.currentDate;
        });
        const furnitureIds = furniture.map(f => f.furniture_id || f.id);

        try {
            const response = await fetch(`${this.options.apiBaseUrl}/pricing/packages/available`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    customer_type: customerType,
                    furniture_ids: furnitureIds,
                    reservation_date: this.state.currentDate,
                    num_people: reservation.num_people || 1
                })
            });

            const result = await response.json();

            if (result.success) {
                this.pricingEditState.availablePackages = result.packages || [];
                this.updatePackageSelector();
            }
        } catch (error) {
            console.error('[Pricing] Error fetching packages:', error);
        }
    }

    /**
     * Update package selector UI with available options
     *
     * Rebuilds the package dropdown:
     * - Hides selector if no packages available
     * - Clears and rebuilds options with package name and price
     * - Selects current package if one is assigned
     * - Shows the selector
     */
    updatePackageSelector() {
        if (!this.panelPricingTypeSelector || !this.panelPricingTypeSelect) return;

        const packages = this.pricingEditState.availablePackages;
        const currentPackageId = this.pricingEditState.selectedPackageId;

        // Hide selector if no packages
        if (!packages || packages.length === 0) {
            this.panelPricingTypeSelector.style.display = 'none';
            return;
        }

        // Clear and rebuild options
        this.panelPricingTypeSelect.innerHTML = '<option value="">Consumo minimo</option>';

        packages.forEach(pkg => {
            const option = document.createElement('option');
            option.value = pkg.id;
            option.textContent = `${pkg.package_name} - €${pkg.calculated_price.toFixed(2)}`;
            this.panelPricingTypeSelect.appendChild(option);
        });

        // Select current package if any
        if (currentPackageId) {
            this.panelPricingTypeSelect.value = currentPackageId.toString();
        } else {
            this.panelPricingTypeSelect.value = '';
        }

        // Show selector
        this.panelPricingTypeSelector.style.display = 'block';
    }

    // =========================================================================
    // PRICE CALCULATION
    // =========================================================================

    /**
     * Calculate and update pricing based on current selections
     *
     * Makes API call to calculate pricing based on:
     * - Customer ID
     * - Furniture IDs for current date
     * - Reservation date
     * - Number of people
     * - Selected package (if any)
     *
     * Updates:
     * - Final price input (if not manually modified)
     * - Calculated price display
     * - Price breakdown text
     */
    async calculateAndUpdatePricing() {
        if (!this.state.data?.reservation || !this.state.data?.customer) return;

        const reservation = this.state.data.reservation;
        const customer = this.state.data.customer;

        // Get furniture IDs for current date
        const furniture = (reservation.furniture || []).filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === this.state.currentDate;
        });
        const furnitureIds = furniture.map(f => f.furniture_id || f.id);

        // Show loading state
        const loadingEl = this.panelPricingDisplay?.querySelector('.pricing-loading');
        const contentEl = this.panelPricingDisplay?.querySelector('.pricing-content');

        if (loadingEl && contentEl) {
            loadingEl.style.display = 'flex';
            contentEl.style.display = 'none';
        }

        try {
            const requestBody = {
                customer_id: customer.id,
                customer_source: 'customer',
                furniture_ids: furnitureIds,
                reservation_date: this.state.currentDate,
                num_people: parseInt(this.editNumPeople?.value) || reservation.num_people || 1
            };

            // Add package_id if selected
            const packageId = this.panelSelectedPackageId?.value;
            if (packageId) {
                requestBody.package_id = parseInt(packageId);
            }

            // Add minimum consumption policy if manually selected
            const policyId = this.pricingEditState.selectedPolicyId;
            if (policyId) {
                requestBody.minimum_consumption_policy_id = policyId;
            }

            const response = await fetch(`${this.options.apiBaseUrl}/pricing/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(requestBody)
            });

            const result = await response.json();

            if (result.success && result.pricing) {
                const calculatedPrice = result.pricing.calculated_price;
                this.pricingEditState.calculatedPrice = calculatedPrice;

                // Update display if not manually modified
                if (!this.pricingEditState.isModified) {
                    if (this.panelFinalPriceInput) {
                        this.panelFinalPriceInput.value = calculatedPrice.toFixed(2);
                    }
                }

                // Update calculated price display
                const calculatedAmountEl = this.panelCalculatedPrice?.querySelector('.calculated-amount');
                if (calculatedAmountEl) {
                    calculatedAmountEl.textContent = `€${calculatedPrice.toFixed(2)}`;
                }

                // Show breakdown if available
                if (this.panelPricingBreakdown && result.pricing.breakdown) {
                    this.panelPricingBreakdown.textContent = result.pricing.breakdown;
                    this.panelPricingBreakdown.style.display = 'block';
                }
            }
        } catch (error) {
            console.error('[Pricing] Calculation error:', error);
        } finally {
            // Hide loading state
            if (loadingEl && contentEl) {
                loadingEl.style.display = 'none';
                contentEl.style.display = 'flex';
            }
        }
    }
};
