/**
 * PricingCalculator - Manages pricing calculations and display
 * Handles package fetching, selection, price calculation, and manual editing
 */
class PricingCalculator {
    constructor(panel) {
        this.panel = panel;
        this._lastCalculatedPrice = 0;
        this._packageChangeHandler = null;

        // Initialize price editing handlers
        this.setupPriceEditing();
    }

    /**
     * Fetch available packages based on reservation details
     */
    async fetchAvailablePackages(customerType, furnitureIds, reservationDate, numPeople) {
        try {
            console.log('[Pricing] Fetching available packages:', {customerType, furnitureIds, reservationDate, numPeople});
            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/pricing/packages/available`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    customer_type: customerType,
                    furniture_ids: furnitureIds,
                    reservation_date: reservationDate,
                    num_people: numPeople
                })
            });

            const result = await response.json();
            console.log('[Pricing] Available packages:', result);

            if (result.success) {
                return result.packages || [];
            }
            return [];
        } catch (error) {
            console.error('[Pricing] Error fetching packages:', error);
            return [];
        }
    }

    /**
     * Update package selector UI with available options (compact dropdown)
     */
    updatePackageSelector(packages, customerType) {
        const pricingTypeSelector = document.getElementById('newPanelPricingTypeSelector');
        const pricingTypeSelect = document.getElementById('newPanelPricingTypeSelect');
        const selectedPackageIdInput = document.getElementById('newPanelSelectedPackageId');

        if (!pricingTypeSelector || !pricingTypeSelect) return;

        // Hide selector if no packages available
        if (!packages || packages.length === 0) {
            pricingTypeSelector.style.display = 'none';
            selectedPackageIdInput.value = '';
            return;
        }

        // Check if we need to rebuild (packages changed)
        const currentPackageIds = Array.from(pricingTypeSelect.options)
            .map(opt => opt.value)
            .filter(v => v !== '') // Exclude minimum consumption option
            .sort()
            .join(',');

        const newPackageIds = packages.map(p => p.id.toString()).sort().join(',');

        // If packages haven't changed, don't rebuild (preserve selection)
        if (currentPackageIds === newPackageIds && pricingTypeSelect.options.length > 1) {
            pricingTypeSelector.style.display = 'block';
            return;
        }

        // Save current selection before rebuilding
        const currentSelection = selectedPackageIdInput.value;

        // Clear previous options (keep the default minimum consumption)
        pricingTypeSelect.innerHTML = '<option value="">Consumo mínimo</option>';

        // Add package options to dropdown
        packages.forEach(pkg => {
            const option = document.createElement('option');
            option.value = pkg.id;
            option.textContent = `${pkg.package_name} - €${pkg.calculated_price.toFixed(2)}`;
            pricingTypeSelect.appendChild(option);
        });

        // Show selector
        pricingTypeSelector.style.display = 'block';

        // Add event listener for dropdown change
        pricingTypeSelect.removeEventListener('change', this._packageChangeHandler); // Remove old listener
        this._packageChangeHandler = () => {
            const selectedValue = pricingTypeSelect.value;
            selectedPackageIdInput.value = selectedValue;

            console.log('[Pricing] Package changed to:', selectedValue || 'Consumo mínimo');
            this.calculatePricingOnly();
        };
        pricingTypeSelect.addEventListener('change', this._packageChangeHandler);

        // Restore previous selection or default to minimum consumption
        if (currentSelection && pricingTypeSelect.querySelector(`option[value="${currentSelection}"]`)) {
            pricingTypeSelect.value = currentSelection;
            selectedPackageIdInput.value = currentSelection;
        } else {
            pricingTypeSelect.value = '';
            selectedPackageIdInput.value = '';
        }
    }

    /**
     * Calculate pricing only (without refetching packages)
     * Use when only the package selection changes
     */
    async calculatePricingOnly() {
        const customerId = document.getElementById('newPanelCustomerId').value;
        const furniture = this.panel.state.selectedFurniture.map(f => f.id);
        const dates = this.panel.datePicker ? this.panel.datePicker.getSelectedDates() : [];
        const numPeople = parseInt(document.getElementById('newPanelNumPeople')?.value) || 2;
        const selectedPackageIdInput = document.getElementById('newPanelSelectedPackageId');

        if (!customerId || furniture.length === 0 || dates.length === 0) {
            return;
        }

        // Show loading
        const pricingDisplay = document.getElementById('newPanelPricingDisplay');
        const loadingEl = pricingDisplay?.querySelector('.pricing-loading');
        const contentEl = pricingDisplay?.querySelector('.pricing-content');

        if (loadingEl && contentEl) {
            loadingEl.style.display = 'flex';
            contentEl.style.display = 'none';
        }

        try {
            const packageId = selectedPackageIdInput?.value || '';

            const requestBody = {
                customer_id: parseInt(customerId),
                furniture_ids: furniture,
                reservation_date: dates[0],
                num_people: numPeople
            };

            if (packageId) {
                requestBody.package_id = parseInt(packageId);
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/pricing/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(requestBody)
            });

            const result = await response.json();

            if (result.success) {
                this.updatePricingDisplay(result.pricing);
            } else {
                console.error('[Pricing] Calculation error:', result.error);
            }
        } catch (error) {
            console.error('[Pricing] API error:', error);
        } finally {
            if (loadingEl && contentEl) {
                loadingEl.style.display = 'none';
                contentEl.style.display = 'flex';
            }
        }
    }

    /**
     * Calculate and display pricing for current reservation
     */
    async calculateAndDisplayPricing() {
        const customerId = document.getElementById('newPanelCustomerId').value;
        const customerSource = document.getElementById('newPanelCustomerSource')?.value || 'customer';
        const furniture = this.panel.state.selectedFurniture.map(f => f.id);
        const dates = this.panel.datePicker ? this.panel.datePicker.getSelectedDates() : [];
        const numPeople = parseInt(document.getElementById('newPanelNumPeople')?.value) || 2;
        const selectedPackageIdInput = document.getElementById('newPanelSelectedPackageId');

        console.log('[Pricing] Calculating pricing:', {customerId, customerSource, furniture, dates, numPeople});

        // Clear if not enough data
        if (!customerId || furniture.length === 0 || dates.length === 0) {
            console.log('[Pricing] Not enough data, clearing display');
            this.updatePricingDisplay(null);
            this.updatePackageSelector([], customerSource);
            return;
        }

        // Show loading
        const pricingDisplay = document.getElementById('newPanelPricingDisplay');
        const loadingEl = pricingDisplay?.querySelector('.pricing-loading');
        const contentEl = pricingDisplay?.querySelector('.pricing-content');

        if (loadingEl && contentEl) {
            loadingEl.style.display = 'flex';
            contentEl.style.display = 'none';
        }

        try {
            // Determine customer type based on source
            // 'hotel_guest' = interno, 'customer' = externo
            const customerType = customerSource === 'hotel_guest' ? 'interno' : 'externo';

            // First, fetch available packages to populate the selector
            const packages = await this.fetchAvailablePackages(
                customerType,
                furniture,
                dates[0],
                numPeople
            );

            // Update package selector UI (only if packages list changed)
            this.updatePackageSelector(packages, customerType);

            // Get selected package_id (empty string for minimum consumption)
            const packageId = selectedPackageIdInput?.value || '';

            console.log('[Pricing] Calling API:', `${this.panel.options.apiBaseUrl}/pricing/calculate`);
            const requestBody = {
                customer_id: parseInt(customerId),
                furniture_ids: furniture,
                reservation_date: dates[0], // Use first date for pricing
                num_people: numPeople
            };

            // Add package_id only if selected
            if (packageId) {
                requestBody.package_id = parseInt(packageId);
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/pricing/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(requestBody)
            });

            console.log('[Pricing] Response status:', response.status);
            const result = await response.json();
            console.log('[Pricing] Response data:', result);

            if (result.success) {
                this.updatePricingDisplay(result.pricing);
            } else {
                console.error('[Pricing] Calculation error:', result.error);
                this.updatePricingDisplay(null);
            }
        } catch (error) {
            console.error('[Pricing] API error:', error);
            this.updatePricingDisplay(null);
        } finally {
            if (loadingEl && contentEl) {
                loadingEl.style.display = 'none';
                contentEl.style.display = 'flex';
            }
        }
    }

    /**
     * Update pricing display UI (with editable price)
     */
    updatePricingDisplay(pricing) {
        const priceInput = document.getElementById('newPanelFinalPriceInput');
        const calculatedPriceEl = document.getElementById('newPanelCalculatedPrice');
        const calculatedAmountEl = calculatedPriceEl?.querySelector('.calculated-amount');
        const breakdownEl = document.getElementById('newPanelPricingBreakdown');
        const priceOverrideInput = document.getElementById('newPanelPriceOverride');
        const resetBtn = document.getElementById('newPanelPriceResetBtn');

        if (!pricing) {
            if (priceInput) priceInput.value = '0.00';
            if (calculatedPriceEl) calculatedPriceEl.style.display = 'none';
            if (breakdownEl) breakdownEl.style.display = 'none';
            if (resetBtn) resetBtn.style.display = 'none';
            if (priceOverrideInput) priceOverrideInput.value = '';
            return;
        }

        const calculatedPrice = pricing.calculated_price.toFixed(2);

        // Store calculated price for reference
        this._lastCalculatedPrice = parseFloat(calculatedPrice);

        // Update calculated price display
        if (calculatedAmountEl) {
            calculatedAmountEl.textContent = `€${calculatedPrice}`;
        }

        // Only update input if user hasn't manually overridden it
        if (!priceOverrideInput?.value) {
            if (priceInput) {
                priceInput.value = calculatedPrice;
                priceInput.classList.remove('modified');
            }
            if (calculatedPriceEl) calculatedPriceEl.style.display = 'none';
            if (resetBtn) resetBtn.style.display = 'none';
        } else {
            // Show that price is modified
            if (priceInput) priceInput.classList.add('modified');
            if (calculatedPriceEl) calculatedPriceEl.style.display = 'block';
            if (resetBtn) resetBtn.style.display = 'block';
        }

        // Show breakdown
        if (breakdownEl && pricing.breakdown) {
            breakdownEl.textContent = pricing.breakdown;
            breakdownEl.style.display = 'block';
        } else if (breakdownEl) {
            breakdownEl.style.display = 'none';
        }
    }

    /**
     * Setup price editing handlers
     */
    setupPriceEditing() {
        const priceInput = document.getElementById('newPanelFinalPriceInput');
        const priceOverrideInput = document.getElementById('newPanelPriceOverride');
        const resetBtn = document.getElementById('newPanelPriceResetBtn');
        const calculatedPriceEl = document.getElementById('newPanelCalculatedPrice');

        if (!priceInput) return;

        // Handle manual price changes
        priceInput.addEventListener('input', () => {
            const manualPrice = parseFloat(priceInput.value) || 0;
            const calculatedPrice = this._lastCalculatedPrice || 0;

            if (Math.abs(manualPrice - calculatedPrice) > 0.01) {
                // Price has been manually modified
                priceInput.classList.add('modified');
                priceOverrideInput.value = manualPrice.toFixed(2);
                if (calculatedPriceEl) calculatedPriceEl.style.display = 'block';
                if (resetBtn) resetBtn.style.display = 'block';
            } else {
                // Price matches calculated, remove override
                priceInput.classList.remove('modified');
                priceOverrideInput.value = '';
                if (calculatedPriceEl) calculatedPriceEl.style.display = 'none';
                if (resetBtn) resetBtn.style.display = 'none';
            }
        });

        // Handle reset button
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                const calculatedPrice = this._lastCalculatedPrice || 0;
                priceInput.value = calculatedPrice.toFixed(2);
                priceInput.classList.remove('modified');
                priceOverrideInput.value = '';
                calculatedPriceEl.style.display = 'none';
                resetBtn.style.display = 'none';
            });
        }
    }
}
