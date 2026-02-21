/**
 * PuroBeach - Main JavaScript
 * Global utilities and initialization
 */

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();

    // Auto-dismiss flash messages
    autoDismissAlerts();

    // Initialize form validation
    initializeFormValidation();

    // Initialize sidebar collapse functionality
    initializeSidebarCollapse();

    // Initialize mobile navigation
    initializeMobileNav();

    // Initialize confirmation modal for forms with data-confirm attribute
    initializeConfirmForms();

});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Auto-dismiss flash messages after 5 seconds
 */
function autoDismissAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');

    alerts.forEach(alert => {
        // Don't auto-dismiss error alerts
        if (!alert.classList.contains('alert-danger')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');

    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: success, error, warning, info
 * @param {number|boolean} duration - Duration in ms, 0 or false for persistent (default: 5000)
 * @param {string} toastId - Optional ID for programmatic dismissal
 * @returns {HTMLElement} The toast container element
 */
function showToast(message, type = 'info', duration = 5000, toastId = null) {
    const alertClass = type === 'error' ? 'danger' : type;
    const iconClass = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    }[type] || 'fa-info-circle';

    // If toastId provided, remove any existing toast with same ID
    if (toastId) {
        dismissToast(toastId);
    }

    const toastHTML = `
        <div class="alert alert-${alertClass} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3" role="alert" style="z-index: 9999;"${toastId ? ` data-toast-id="${toastId}"` : ''}>
            <i class="fas ${iconClass}"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    const container = document.createElement('div');
    if (toastId) {
        container.setAttribute('data-toast-container', toastId);
    }
    container.innerHTML = toastHTML;
    document.body.appendChild(container);

    // Auto-dismiss after duration (unless 0 or false for persistent)
    if (duration && duration > 0) {
        setTimeout(() => {
            const alert = container.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, duration);
    }

    return container;
}

/**
 * Dismiss a toast by its ID
 * @param {string} toastId - The toast ID to dismiss
 */
function dismissToast(toastId) {
    const container = document.querySelector(`[data-toast-container="${toastId}"]`);
    if (container) {
        const alert = container.querySelector('.alert');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
        // Remove container after animation
        setTimeout(() => container.remove(), 300);
    }
}

// =============================================================================
// CONFIRMATION MODAL SYSTEM
// =============================================================================

/**
 * Show a professional confirmation modal (replaces native confirm() dialogs).
 *
 * @param {object} options - Configuration options
 * @param {string} [options.title='¿Está seguro?'] - Modal title
 * @param {string} [options.message='Esta acción no se puede deshacer.'] - Modal body message (supports HTML)
 * @param {string} [options.confirmText='Confirmar'] - Text for the confirm button
 * @param {string} [options.cancelText='Cancelar'] - Text for the cancel button
 * @param {string} [options.confirmClass='btn-danger'] - CSS class for the confirm button
 * @param {string} [options.iconClass='fa-exclamation-triangle'] - FontAwesome icon class
 * @param {string} [options.iconColor=''] - CSS color override for the icon (defaults to match confirmClass)
 * @param {Function} [options.onConfirm] - Callback executed when user confirms
 * @param {Function} [options.onCancel] - Callback executed when user cancels
 * @returns {Promise<boolean>} - Resolves true if confirmed, false if cancelled
 */
function confirmAction(options = {}) {
    const defaults = {
        title: '¿Está seguro?',
        message: 'Esta acción no se puede deshacer.',
        confirmText: 'Confirmar',
        cancelText: 'Cancelar',
        confirmClass: 'btn-danger',
        iconClass: 'fa-exclamation-triangle',
        iconColor: '',
        onConfirm: null,
        onCancel: null
    };

    const config = { ...defaults, ...options };

    return new Promise((resolve) => {
        const modalEl = document.getElementById('confirmActionModal');
        if (!modalEl) {
            // Fallback to native confirm if modal is not in the DOM
            const result = confirm(config.message);
            if (result && config.onConfirm) config.onConfirm();
            if (!result && config.onCancel) config.onCancel();
            resolve(result);
            return;
        }

        // Set modal content
        const titleEl = document.getElementById('confirmActionModalLabel');
        const messageEl = document.getElementById('confirmActionMessage');
        const confirmBtn = document.getElementById('confirmActionConfirmBtn');
        const cancelBtn = document.getElementById('confirmActionCancelBtn');
        const iconContainer = document.getElementById('confirmActionIcon');

        titleEl.textContent = config.title;
        messageEl.innerHTML = config.message;

        // Update confirm button
        confirmBtn.className = 'btn ' + config.confirmClass;
        confirmBtn.innerHTML = '<i class="fas fa-check"></i> ' + config.confirmText;

        // Update cancel button
        cancelBtn.innerHTML = '<i class="fas fa-times"></i> ' + config.cancelText;

        // Update icon
        const iconColorMap = {
            'btn-danger': 'var(--color-error, #C1444F)',
            'btn-warning': 'var(--color-warning, #E5A33D)',
            'btn-primary': 'var(--color-primary, #D4AF37)',
            'btn-outline-danger': 'var(--color-error, #C1444F)',
            'btn-outline-warning': 'var(--color-warning, #E5A33D)'
        };
        const iconColor = config.iconColor || iconColorMap[config.confirmClass] || 'var(--color-warning, #E5A33D)';
        iconContainer.innerHTML = '<i class="fas ' + config.iconClass + '"></i>';
        iconContainer.style.color = iconColor;

        // Track whether we already resolved (prevent double-fire)
        let resolved = false;

        function cleanup() {
            confirmBtn.removeEventListener('click', handleConfirm);
            modalEl.removeEventListener('hidden.bs.modal', handleDismiss);
        }

        function handleConfirm() {
            if (resolved) return;
            resolved = true;
            cleanup();
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            if (config.onConfirm) config.onConfirm();
            resolve(true);
        }

        function handleDismiss() {
            if (resolved) return;
            resolved = true;
            cleanup();
            if (config.onCancel) config.onCancel();
            resolve(false);
        }

        confirmBtn.addEventListener('click', handleConfirm);
        modalEl.addEventListener('hidden.bs.modal', handleDismiss);

        // Show the modal
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    });
}

/**
 * Confirm dialog for delete actions (backward-compatible wrapper).
 * Now returns a Promise instead of a boolean, but supports both
 * callback and await patterns.
 *
 * @param {string} message - Confirmation message
 * @param {Function} [onConfirm] - Optional callback on confirm
 * @returns {Promise<boolean>} - Resolves true if confirmed
 */
function confirmDelete(message = '¿Está seguro de eliminar este registro?', onConfirm = null) {
    return confirmAction({
        title: 'Confirmar eliminación',
        message: message,
        confirmText: 'Eliminar',
        confirmClass: 'btn-danger',
        iconClass: 'fa-trash-alt',
        onConfirm: onConfirm
    });
}

/**
 * Initialize data-confirm attribute handling on forms.
 * Forms with data-confirm="message" will show the confirmation modal
 * instead of using native confirm() dialogs.
 *
 * Supported data attributes:
 *   data-confirm="message"           - The confirmation message (required)
 *   data-confirm-title="title"       - Custom title (optional)
 *   data-confirm-btn-text="text"     - Confirm button text (optional)
 *   data-confirm-btn-class="class"   - Confirm button CSS class (optional)
 *   data-confirm-icon="icon"         - FontAwesome icon class (optional)
 */
function initializeConfirmForms() {
    document.addEventListener('submit', function(e) {
        const form = e.target;
        const confirmMessage = form.getAttribute('data-confirm');

        // Only intercept forms with data-confirm attribute
        if (!confirmMessage) return;

        // Check if this submission was already confirmed
        if (form._pbConfirmed) {
            form._pbConfirmed = false;
            return; // Let it proceed
        }

        // Prevent the form from submitting
        e.preventDefault();

        const title = form.getAttribute('data-confirm-title') || '¿Está seguro?';
        const btnText = form.getAttribute('data-confirm-btn-text') || 'Confirmar';
        const btnClass = form.getAttribute('data-confirm-btn-class') || 'btn-danger';
        const iconClass = form.getAttribute('data-confirm-icon') || 'fa-exclamation-triangle';

        confirmAction({
            title: title,
            message: confirmMessage,
            confirmText: btnText,
            confirmClass: btnClass,
            iconClass: iconClass,
            onConfirm: function() {
                form._pbConfirmed = true;
                form.submit();
            }
        });
    });
}

/**
 * Format date to Spanish format (DD/MM/YYYY)
 * @param {string} dateString - Date string (YYYY-MM-DD)
 * @returns {string} - Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return '';

    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();

    return `${day}/${month}/${year}`;
}

/**
 * Format datetime to Spanish format (DD/MM/YYYY HH:MM)
 * @param {string} datetimeString - Datetime string
 * @returns {string} - Formatted datetime
 */
function formatDateTime(datetimeString) {
    if (!datetimeString) return '';

    const date = new Date(datetimeString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${day}/${month}/${year} ${hours}:${minutes}`;
}

/**
 * Debounce function for search inputs
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copiado al portapapeles', 'success');
    }).catch(err => {
        showToast('Error al copiar', 'error');
        console.error('Failed to copy:', err);
    });
}

/**
 * Initialize DataTables (if needed in future phases)
 * @param {string} selector - Table selector
 * @param {object} options - DataTables options
 */
function initializeDataTable(selector, options = {}) {
    // Placeholder for Phase 2+ when we add advanced table features
}

/**
 * AJAX helper function
 * @param {string} url - URL to fetch
 * @param {object} options - Fetch options
 * @returns {Promise} - Fetch promise
 */
async function fetchJSON(url, options = {}) {
    try {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.content : '';
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        showToast('Error en la conexión con el servidor', 'error');
        throw error;
    }
}

/**
 * Initialize sidebar collapse/expand functionality
 * Persists user preference in localStorage
 */
function initializeSidebarCollapse() {
    const sidebar = document.getElementById('mainSidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    const STORAGE_KEY = 'purobeach_sidebar_collapsed';

    if (!sidebar || !toggleBtn) {
        return; // Exit if elements don't exist (e.g., login page)
    }

    // Sync sidebar class with html class (set by inline script for instant load)
    const isInitiallyCollapsed = document.documentElement.classList.contains('sidebar-collapsed');
    if (isInitiallyCollapsed) {
        sidebar.classList.add('collapsed');
        updateToggleButton(toggleBtn, true);
    }

    // Toggle button click handler
    toggleBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        const isCollapsed = sidebar.classList.toggle('collapsed');

        // Sync html class for CSS consistency
        document.documentElement.classList.toggle('sidebar-collapsed', isCollapsed);

        // Save preference to localStorage
        localStorage.setItem(STORAGE_KEY, isCollapsed.toString());

        // Update button tooltip and aria-label
        updateToggleButton(toggleBtn, isCollapsed);

        // Close any open Bootstrap collapse menus when collapsing
        if (isCollapsed) {
            closeAllCollapseMenus(sidebar);
        }
    });

    // Handle hover behavior for collapsed state child menus
    setupCollapsedHoverBehavior(sidebar);

    // Handle click on parent menu when collapsed - expand sidebar and menu
    setupCollapsedClickBehavior(sidebar, toggleBtn, STORAGE_KEY);
}

/**
 * Update toggle button state (tooltip, aria-label)
 * @param {HTMLElement} button - Toggle button element
 * @param {boolean} isCollapsed - Current collapsed state
 */
function updateToggleButton(button, isCollapsed) {
    const expandText = 'Expandir menu';
    const collapseText = 'Colapsar menu';

    button.setAttribute('title', isCollapsed ? expandText : collapseText);
    button.setAttribute('aria-label', isCollapsed ? expandText : collapseText);
}

/**
 * Close all Bootstrap collapse elements in sidebar
 * @param {HTMLElement} sidebar - Sidebar element
 */
function closeAllCollapseMenus(sidebar) {
    const openCollapses = sidebar.querySelectorAll('.collapse.show');
    openCollapses.forEach(collapse => {
        const bsCollapse = bootstrap.Collapse.getInstance(collapse);
        if (bsCollapse) {
            bsCollapse.hide();
        }
    });
}

/**
 * Setup hover behavior for showing child menus in collapsed state
 * @param {HTMLElement} sidebar - Sidebar element
 */
function setupCollapsedHoverBehavior(sidebar) {
    const navSections = sidebar.querySelectorAll('.nav-section');

    navSections.forEach(section => {
        const collapseEl = section.querySelector('.collapse');
        if (!collapseEl) return;

        let hoverTimeout;

        // Show submenu on hover (only when collapsed)
        section.addEventListener('mouseenter', function() {
            if (!sidebar.classList.contains('collapsed')) return;

            clearTimeout(hoverTimeout);
            // Force display the collapse element
            collapseEl.style.display = 'block';
            collapseEl.classList.add('show');
        });

        // Hide submenu on mouse leave (with small delay)
        section.addEventListener('mouseleave', function() {
            if (!sidebar.classList.contains('collapsed')) return;

            hoverTimeout = setTimeout(() => {
                collapseEl.style.display = '';
                collapseEl.classList.remove('show');
            }, 150); // Small delay to allow moving to submenu
        });
    });
}

/**
 * Setup click behavior for parent menus when sidebar is collapsed
 * Clicking a parent menu expands the sidebar and opens that menu
 * @param {HTMLElement} sidebar - Sidebar element
 * @param {HTMLElement} toggleBtn - Toggle button element
 * @param {string} storageKey - localStorage key for persistence
 */
function setupCollapsedClickBehavior(sidebar, toggleBtn, storageKey) {
    const navParents = sidebar.querySelectorAll('.nav-parent');

    navParents.forEach(parent => {
        parent.addEventListener('click', function(e) {
            // Only intercept when sidebar is collapsed
            if (!sidebar.classList.contains('collapsed')) return;

            // Prevent Bootstrap collapse from toggling
            e.preventDefault();
            e.stopPropagation();

            // Get the target collapse element
            const targetId = parent.getAttribute('href');
            const collapseEl = document.querySelector(targetId);

            // Expand sidebar
            sidebar.classList.remove('collapsed');
            document.documentElement.classList.remove('sidebar-collapsed');
            localStorage.setItem(storageKey, 'false');
            updateToggleButton(toggleBtn, false);

            // Reset any hover-induced display styles
            sidebar.querySelectorAll('.collapse').forEach(el => {
                el.style.display = '';
            });

            // Close all menus first, then open the clicked one
            closeAllCollapseMenus(sidebar);

            // Open the clicked menu after a brief delay for smooth animation
            if (collapseEl) {
                setTimeout(() => {
                    const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseEl);
                    bsCollapse.show();
                }, 50);
            }
        });
    });
}

/**
 * Toggle sidebar programmatically
 */
function toggleSidebar() {
    const toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn) {
        toggleBtn.click();
    }
}

/**
 * Initialize mobile offcanvas navigation.
 * Closes the offcanvas when a nav link is clicked.
 */
function initializeMobileNav() {
    const mobileSidebar = document.getElementById('mobileSidebar');
    if (!mobileSidebar) return;

    const navLinks = mobileSidebar.querySelectorAll('.mobile-nav-child');
    navLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            const offcanvasInstance = bootstrap.Offcanvas.getInstance(mobileSidebar);
            if (offcanvasInstance) {
                offcanvasInstance.hide();
            }
        });
    });
}

/**
 * Set a button to loading or normal state.
 * Prevents double-clicks during AJAX operations by disabling the button and
 * showing a spinner with a configurable loading message.
 *
 * Supports two modes:
 * 1. Auto mode: pass a button element. Original innerHTML is saved/restored.
 * 2. data-loading-text: if the button has this attribute, it is used as the
 *    loading label (e.g. data-loading-text="Guardando...").
 *
 * @param {HTMLElement} button - The button element to modify
 * @param {boolean} loading - true to enter loading state, false to restore
 * @param {string} [loadingText] - Optional override for the loading message
 */
function setButtonLoading(button, loading, loadingText) {
    if (!button) return;

    if (loading) {
        // Save original state only once (avoid overwriting on repeated calls)
        if (!button.dataset.pbOriginalHtml) {
            button.dataset.pbOriginalHtml = button.innerHTML;
        }
        button.disabled = true;
        button.classList.add('btn-loading');

        const text = loadingText
            || button.dataset.loadingText
            || 'Procesando...';
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + text;
    } else {
        button.disabled = false;
        button.classList.remove('btn-loading');

        if (button.dataset.pbOriginalHtml) {
            button.innerHTML = button.dataset.pbOriginalHtml;
            delete button.dataset.pbOriginalHtml;
        }
    }
}

// Export functions for global use
window.PuroBeach = {
    showToast,
    dismissToast,
    confirmAction,
    confirmDelete,
    formatDate,
    formatDateTime,
    debounce,
    copyToClipboard,
    fetchJSON,
    toggleSidebar,
    setButtonLoading
};
