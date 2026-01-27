/**
 * Reservation Form Pricing - Real-time pricing calculations and UI updates
 */

(function() {
    'use strict';

    // State management
    let currentPricing = null;
    let availablePackages = [];
    let availablePolicies = [];

    // DOM element references (initialized on DOM ready)
    let elements = {};

    /**
     * Initialize pricing functionality
     */
    function initPricingModule() {
        // Cache DOM elements
        cacheElements();

        // Attach event listeners
        attachEventListeners();

        // Load minimum consumption policies
        loadMinConsumptionPolicies();

        // Initial load if form has data
        if (elements.customerSelect && elements.customerSelect.value) {
            loadAvailablePackages();
            calculatePricing();
        }
    }

    /**
     * Cache DOM element references
     */
    function cacheElements() {
        elements = {
            // Form inputs
            customerSelect: document.getElementById('customerSelect'),
            furnitureSelect: document.getElementById('furnitureSelect'),
            dateInput: document.getElementById('dateInput') || document.getElementById('reservationDate'),
            numPeopleInput: document.getElementById('numPeople'),
            packageSelect: document.getElementById('packageSelect'),
            minConsumptionPolicySelect: document.getElementById('minConsumptionPolicySelect'),
            finalPriceInput: document.getElementById('finalPrice'),
            paidCheckbox: document.getElementById('paid'),
            paymentTicketInput: document.getElementById('payment_ticket_number'),

            // Display elements
            minConsumptionAmount: document.getElementById('minConsumptionAmount'),
            minConsumptionPolicy: document.getElementById('minConsumptionPolicy'),
            calculatedPriceDisplay: document.getElementById('calculatedPriceDisplay'),
            priceBreakdown: document.getElementById('priceBreakdown'),
            ticketRequired: document.getElementById('ticketRequired'),

            // Hidden fields
            calculatedPriceField: document.getElementById('calculatedPrice'),
            minConsumptionAmountField: document.getElementById('minConsumptionAmountField'),
            minConsumptionPolicyIdField: document.getElementById('minConsumptionPolicyId'),

            // Summary sidebar elements (if present)
            summaryPrice: document.querySelector('.summary-price'),
            summaryPackage: document.querySelector('.summary-package'),
            summaryMinConsumption: document.querySelector('.summary-min-consumption')
        };
    }

    /**
     * Attach event listeners to form elements
     */
    function attachEventListeners() {
        // Customer change → reload packages and recalculate
        if (elements.customerSelect) {
            elements.customerSelect.addEventListener('change', function() {
                loadAvailablePackages();
                calculatePricing();
            });
        }

        // Furniture selection change → recalculate
        if (elements.furnitureSelect) {
            elements.furnitureSelect.addEventListener('change', calculatePricing);
        }

        // Date change → reload packages (validity) and recalculate
        if (elements.dateInput) {
            elements.dateInput.addEventListener('change', function() {
                loadAvailablePackages();
                calculatePricing();
            });
        }

        // People count change → recalculate
        if (elements.numPeopleInput) {
            elements.numPeopleInput.addEventListener('change', calculatePricing);
            elements.numPeopleInput.addEventListener('input', calculatePricing);
        }

        // Package selection change → recalculate
        if (elements.packageSelect) {
            elements.packageSelect.addEventListener('change', calculatePricing);
        }

        // Minimum consumption policy selection change → recalculate
        if (elements.minConsumptionPolicySelect) {
            elements.minConsumptionPolicySelect.addEventListener('change', calculatePricing);
        }

        // Paid checkbox → validate ticket requirement
        if (elements.paidCheckbox) {
            elements.paidCheckbox.addEventListener('change', validatePaymentTicket);
        }

        // Payment ticket → auto-check paid if entered
        if (elements.paymentTicketInput) {
            elements.paymentTicketInput.addEventListener('blur', validatePaymentTicket);
        }
    }

    /**
     * Load minimum consumption policies for dropdown
     */
    async function loadMinConsumptionPolicies() {
        if (!elements.minConsumptionPolicySelect) return;

        try {
            const response = await fetch('/beach/api/pricing/minimum-consumption-policies');
            const data = await response.json();

            if (data.success) {
                availablePolicies = data.policies;
                updateMinConsumptionPolicyDropdown(data.policies);
            } else {
                console.error('Error loading min consumption policies:', data.error);
            }
        } catch (error) {
            console.error('Error loading min consumption policies:', error);
        }
    }

    /**
     * Update minimum consumption policy dropdown
     */
    function updateMinConsumptionPolicyDropdown(policies) {
        if (!elements.minConsumptionPolicySelect) return;

        const currentSelection = elements.minConsumptionPolicySelect.value;

        // Reset dropdown with auto option
        elements.minConsumptionPolicySelect.innerHTML = '<option value="auto">Automático (según tipo cliente/mobiliario)</option>';

        policies.forEach(policy => {
            const option = document.createElement('option');
            option.value = policy.id;

            // Build display text
            let displayText = policy.policy_name;
            if (policy.minimum_amount > 0) {
                const amountStr = policy.calculation_type === 'per_person'
                    ? `${policy.minimum_amount.toFixed(2)}€/persona`
                    : `${policy.minimum_amount.toFixed(2)}€`;
                displayText += ` - ${amountStr}`;
            } else {
                displayText += ' - Sin minimo';
            }

            option.textContent = displayText;
            option.dataset.amount = policy.minimum_amount;
            option.dataset.calculationType = policy.calculation_type;

            // Restore previous selection if valid
            if (currentSelection && parseInt(currentSelection) === policy.id) {
                option.selected = true;
            }

            elements.minConsumptionPolicySelect.appendChild(option);
        });
    }

    /**
     * Load available packages based on current form state
     */
    async function loadAvailablePackages() {
        const customerId = elements.customerSelect ? elements.customerSelect.value : null;
        const furnitureIds = getSelectedFurnitureIds();
        const reservationDate = elements.dateInput ? elements.dateInput.value : null;
        const numPeople = elements.numPeopleInput ? parseInt(elements.numPeopleInput.value) || 1 : 1;

        // Validation
        if (!customerId || furnitureIds.length === 0 || !reservationDate) {
            // Clear package dropdown
            if (elements.packageSelect) {
                elements.packageSelect.innerHTML = '<option value="">Sin paquete - Consumo mínimo</option>';
                elements.packageSelect.disabled = true;
            }
            return;
        }

        // Get customer type
        const customerType = getCustomerType(customerId);
        if (!customerType) return;

        try {
            const response = await fetch('/beach/api/pricing/packages/available', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    customer_type: customerType,
                    furniture_ids: furnitureIds,
                    reservation_date: reservationDate,
                    num_people: numPeople
                })
            });

            const data = await response.json();

            if (data.success) {
                availablePackages = data.packages;
                updatePackageDropdown(data.packages);
            } else {
                console.error('Error loading packages:', data.error);
                showError(data.error);
            }
        } catch (error) {
            console.error('Error loading packages:', error);
            showError('Error al cargar los paquetes disponibles');
        }
    }

    /**
     * Update package dropdown with available packages
     */
    function updatePackageDropdown(packages) {
        if (!elements.packageSelect) return;

        const currentSelection = elements.packageSelect.value;

        elements.packageSelect.innerHTML = '<option value="">Sin paquete - Consumo mínimo</option>';

        packages.forEach(package => {
            const option = document.createElement('option');
            option.value = package.id;
            option.textContent = `${package.package_name} - €${package.calculated_price.toFixed(2)}`;
            option.dataset.price = package.calculated_price;
            option.dataset.breakdown = package.price_breakdown;

            // Restore previous selection if valid
            if (currentSelection && parseInt(currentSelection) === package.id) {
                option.selected = true;
            }

            elements.packageSelect.appendChild(option);
        });

        elements.packageSelect.disabled = packages.length === 0;
    }

    /**
     * Calculate pricing for current form state
     */
    async function calculatePricing() {
        const customerId = elements.customerSelect ? elements.customerSelect.value : null;
        const furnitureIds = getSelectedFurnitureIds();
        const reservationDate = elements.dateInput ? elements.dateInput.value : null;
        const numPeople = elements.numPeopleInput ? parseInt(elements.numPeopleInput.value) || 1 : 1;
        const packageId = elements.packageSelect ? elements.packageSelect.value : null;
        const minConsumptionPolicyId = elements.minConsumptionPolicySelect
            ? elements.minConsumptionPolicySelect.value
            : 'auto';

        // Validation
        if (!customerId || furnitureIds.length === 0 || !reservationDate) {
            clearPricingDisplay();
            return;
        }

        try {
            const requestBody = {
                customer_id: parseInt(customerId),
                furniture_ids: furnitureIds,
                reservation_date: reservationDate,
                num_people: numPeople,
                package_id: packageId ? parseInt(packageId) : null
            };

            // Add manual policy selection if not auto
            if (minConsumptionPolicyId && minConsumptionPolicyId !== 'auto') {
                requestBody.minimum_consumption_policy_id = parseInt(minConsumptionPolicyId);
            }

            const response = await fetch('/beach/api/pricing/calculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (data.success) {
                currentPricing = data.pricing;
                updatePricingDisplay(data.pricing);
            } else {
                console.error('Error calculating pricing:', data.error);
                showError(data.error);
            }
        } catch (error) {
            console.error('Error calculating pricing:', error);
            showError('Error al calcular el precio');
        }
    }

    /**
     * Update UI with calculated pricing
     */
    function updatePricingDisplay(pricing) {
        // Update minimum consumption display
        if (elements.minConsumptionAmount) {
            if (pricing.has_minimum_consumption && !pricing.has_package) {
                elements.minConsumptionAmount.textContent = pricing.minimum_consumption_amount.toFixed(2);
                if (elements.minConsumptionPolicy && pricing.minimum_consumption) {
                    elements.minConsumptionPolicy.textContent = pricing.minimum_consumption.policy_name;
                }
            } else {
                elements.minConsumptionAmount.textContent = '0.00';
                if (elements.minConsumptionPolicy) {
                    elements.minConsumptionPolicy.textContent = pricing.has_package ? 'Incluido en paquete' : 'No aplica';
                }
            }
        }

        // Update calculated price display
        if (elements.calculatedPriceDisplay) {
            elements.calculatedPriceDisplay.textContent = pricing.calculated_price.toFixed(2);
        }

        // Update price breakdown
        if (elements.priceBreakdown) {
            elements.priceBreakdown.textContent = pricing.breakdown;
        }

        // Update hidden fields
        if (elements.calculatedPriceField) {
            elements.calculatedPriceField.value = pricing.calculated_price.toFixed(2);
        }

        if (elements.minConsumptionAmountField) {
            elements.minConsumptionAmountField.value = pricing.minimum_consumption_amount.toFixed(2);
        }

        if (elements.minConsumptionPolicyIdField) {
            elements.minConsumptionPolicyIdField.value = pricing.has_minimum_consumption && pricing.minimum_consumption
                ? pricing.minimum_consumption.policy_id
                : '';
        }

        // Set final price to calculated price if empty
        if (elements.finalPriceInput && !elements.finalPriceInput.value) {
            elements.finalPriceInput.value = pricing.calculated_price.toFixed(2);
        }

        // Update summary sidebar if present
        updateSummary(pricing);
    }

    /**
     * Update summary sidebar with pricing info
     */
    function updateSummary(pricing) {
        if (elements.summaryPrice) {
            elements.summaryPrice.textContent = `€${pricing.calculated_price.toFixed(2)}`;
        }

        if (elements.summaryPackage) {
            elements.summaryPackage.textContent = pricing.has_package && pricing.package
                ? pricing.package.package_name
                : '-';
        }

        if (elements.summaryMinConsumption) {
            elements.summaryMinConsumption.textContent = pricing.has_minimum_consumption && pricing.minimum_consumption
                ? `€${pricing.minimum_consumption_amount.toFixed(2)}`
                : '-';
        }
    }

    /**
     * Clear pricing display
     */
    function clearPricingDisplay() {
        if (elements.minConsumptionAmount) elements.minConsumptionAmount.textContent = '0.00';
        if (elements.minConsumptionPolicy) elements.minConsumptionPolicy.textContent = '';
        if (elements.calculatedPriceDisplay) elements.calculatedPriceDisplay.textContent = '0.00';
        if (elements.priceBreakdown) elements.priceBreakdown.textContent = '';
        if (elements.calculatedPriceField) elements.calculatedPriceField.value = '0';
        if (elements.minConsumptionAmountField) elements.minConsumptionAmountField.value = '0';
        if (elements.minConsumptionPolicyIdField) elements.minConsumptionPolicyIdField.value = '';
    }

    /**
     * Validate payment ticket requirement
     */
    function validatePaymentTicket() {
        const isPaid = elements.paidCheckbox ? elements.paidCheckbox.checked : false;
        const hasTicket = elements.paymentTicketInput ? elements.paymentTicketInput.value.trim() !== '' : false;

        if (elements.ticketRequired) {
            if (isPaid) {
                elements.ticketRequired.style.display = 'inline';
                elements.ticketRequired.classList.add('text-danger');
                if (elements.paymentTicketInput) {
                    elements.paymentTicketInput.required = true;
                }
            } else {
                elements.ticketRequired.style.display = 'none';
                if (elements.paymentTicketInput) {
                    elements.paymentTicketInput.required = false;
                }
            }
        }

        // Auto-check paid if ticket entered
        if (hasTicket && elements.paidCheckbox && !elements.paidCheckbox.checked) {
            elements.paidCheckbox.checked = true;
            if (elements.ticketRequired) {
                elements.ticketRequired.style.display = 'inline';
            }
        }
    }

    /**
     * Get selected furniture IDs from form
     */
    function getSelectedFurnitureIds() {
        if (!elements.furnitureSelect) return [];

        // Check if it's a multi-select
        const options = elements.furnitureSelect.selectedOptions;
        if (options && options.length > 0) {
            return Array.from(options).map(opt => parseInt(opt.value));
        }

        // Single select
        const value = elements.furnitureSelect.value;
        return value ? [parseInt(value)] : [];
    }

    /**
     * Get customer type from customer select
     */
    function getCustomerType(customerId) {
        if (!elements.customerSelect || !customerId) return null;

        // Get customer type from selected option's data attribute
        const selectedOption = elements.customerSelect.querySelector(`option[value="${customerId}"]`);
        if (selectedOption) {
            return selectedOption.dataset.customerType || selectedOption.dataset.type;
        }

        return null;
    }

    /**
     * Show error message
     */
    function showError(message) {
        // Try to use existing error display mechanism
        if (window.showToast) {
            window.showToast(message, 'error');
        } else {
            console.error(message);
            alert(message);
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPricingModule);
    } else {
        initPricingModule();
    }

    // Expose functions for external access if needed
    window.ReservationPricing = {
        recalculate: calculatePricing,
        reload: loadAvailablePackages,
        validate: validatePaymentTicket
    };

})();
