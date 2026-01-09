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

    console.log('PuroBeach initialized successfully');
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

/**
 * Confirm dialog for delete actions
 * @param {string} message - Confirmation message
 * @returns {boolean} - User confirmation
 */
function confirmDelete(message = '¿Está seguro de eliminar este registro?') {
    return confirm(message);
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
    console.log('DataTables will be initialized in Phase 2');
}

/**
 * AJAX helper function
 * @param {string} url - URL to fetch
 * @param {object} options - Fetch options
 * @returns {Promise} - Fetch promise
 */
async function fetchJSON(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
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

// Export functions for global use
window.PuroBeach = {
    showToast,
    dismissToast,
    confirmDelete,
    formatDate,
    formatDateTime,
    debounce,
    copyToClipboard,
    fetchJSON,
    toggleSidebar
};
