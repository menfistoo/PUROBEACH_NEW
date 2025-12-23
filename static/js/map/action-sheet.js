/**
 * Action Sheet Module
 * A mobile-friendly bottom sheet component for the beach map.
 * Used to show reservation details and quick actions.
 */
class ActionSheet {
    constructor(options = {}) {
        this.options = {
            maxHeight: options.maxHeight || '85vh',
            animationDuration: options.animationDuration || 300,
            backdropClose: options.backdropClose !== false,
            ...options
        };

        this.isOpen = false;
        this.sheet = null;
        this.backdrop = null;
        this.content = null;
        this.startY = 0;
        this.currentY = 0;
        this.isDragging = false;

        // Callbacks
        this.callbacks = {
            onOpen: null,
            onClose: null
        };

        // Create elements
        this.createElement();
        this.attachListeners();
    }

    createElement() {
        // Backdrop
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'action-sheet-backdrop';
        this.backdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1040;
            opacity: 0;
            visibility: hidden;
            transition: opacity ${this.options.animationDuration}ms ease, visibility ${this.options.animationDuration}ms ease;
        `;

        // Sheet container
        this.sheet = document.createElement('div');
        this.sheet.className = 'action-sheet';
        this.sheet.style.cssText = `
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            max-height: ${this.options.maxHeight};
            background: white;
            border-radius: 20px 20px 0 0;
            z-index: 1050;
            transform: translateY(100%);
            transition: transform ${this.options.animationDuration}ms ease;
            box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        `;

        // Drag handle
        const handle = document.createElement('div');
        handle.className = 'action-sheet-handle';
        handle.style.cssText = `
            width: 40px;
            height: 4px;
            background: #DDD;
            border-radius: 2px;
            margin: 12px auto 8px;
            cursor: grab;
        `;

        // Header
        this.header = document.createElement('div');
        this.header.className = 'action-sheet-header';
        this.header.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px 12px;
            border-bottom: 1px solid #EEE;
        `;

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'action-sheet-close btn btn-link p-0';
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.style.cssText = `
            font-size: 18px;
            color: #666;
            background: none;
            border: none;
            cursor: pointer;
        `;
        closeBtn.addEventListener('click', () => this.close());

        // Title
        this.titleEl = document.createElement('span');
        this.titleEl.className = 'action-sheet-title';
        this.titleEl.style.cssText = `
            font-weight: 600;
            font-size: 16px;
            color: #1A3A5C;
        `;

        // Header actions (optional buttons)
        this.headerActions = document.createElement('div');
        this.headerActions.className = 'action-sheet-header-actions';

        this.header.appendChild(closeBtn);
        this.header.appendChild(this.titleEl);
        this.header.appendChild(this.headerActions);

        // Content area (scrollable)
        this.content = document.createElement('div');
        this.content.className = 'action-sheet-content';
        this.content.style.cssText = `
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            -webkit-overflow-scrolling: touch;
        `;

        // Footer (for action buttons)
        this.footer = document.createElement('div');
        this.footer.className = 'action-sheet-footer';
        this.footer.style.cssText = `
            padding: 12px 16px;
            padding-bottom: max(12px, env(safe-area-inset-bottom));
            border-top: 1px solid #EEE;
            background: #FAFAFA;
        `;

        // Assemble
        this.sheet.appendChild(handle);
        this.sheet.appendChild(this.header);
        this.sheet.appendChild(this.content);
        this.sheet.appendChild(this.footer);

        // Add to DOM
        document.body.appendChild(this.backdrop);
        document.body.appendChild(this.sheet);
    }

    attachListeners() {
        // Backdrop click to close
        if (this.options.backdropClose) {
            this.backdrop.addEventListener('click', () => this.close());
        }

        // Swipe down to close (touch)
        const handle = this.sheet.querySelector('.action-sheet-handle');
        handle.addEventListener('touchstart', (e) => this.handleDragStart(e));
        this.sheet.addEventListener('touchmove', (e) => this.handleDragMove(e));
        this.sheet.addEventListener('touchend', (e) => this.handleDragEnd(e));

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }

    handleDragStart(event) {
        this.isDragging = true;
        this.startY = event.touches[0].clientY;
        this.sheet.style.transition = 'none';
    }

    handleDragMove(event) {
        if (!this.isDragging) return;

        this.currentY = event.touches[0].clientY;
        const deltaY = this.currentY - this.startY;

        // Only allow dragging down
        if (deltaY > 0) {
            this.sheet.style.transform = `translateY(${deltaY}px)`;
        }
    }

    handleDragEnd() {
        if (!this.isDragging) return;

        this.isDragging = false;
        this.sheet.style.transition = `transform ${this.options.animationDuration}ms ease`;

        const deltaY = this.currentY - this.startY;

        // Close if dragged more than 100px
        if (deltaY > 100) {
            this.close();
        } else {
            this.sheet.style.transform = 'translateY(0)';
        }
    }

    // Public API
    setTitle(title) {
        this.titleEl.textContent = title;
        return this;
    }

    setContent(html) {
        if (typeof html === 'string') {
            this.content.innerHTML = html;
        } else if (html instanceof HTMLElement) {
            this.content.innerHTML = '';
            this.content.appendChild(html);
        }
        return this;
    }

    setFooter(html) {
        if (typeof html === 'string') {
            this.footer.innerHTML = html;
        } else if (html instanceof HTMLElement) {
            this.footer.innerHTML = '';
            this.footer.appendChild(html);
        }
        return this;
    }

    addHeaderAction(html) {
        if (typeof html === 'string') {
            this.headerActions.innerHTML += html;
        } else if (html instanceof HTMLElement) {
            this.headerActions.appendChild(html);
        }
        return this;
    }

    clearHeaderActions() {
        this.headerActions.innerHTML = '';
        return this;
    }

    open() {
        if (this.isOpen) return this;

        this.isOpen = true;

        // Show backdrop
        this.backdrop.style.visibility = 'visible';
        this.backdrop.style.opacity = '1';

        // Slide up sheet
        requestAnimationFrame(() => {
            this.sheet.style.transform = 'translateY(0)';
        });

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        if (this.callbacks.onOpen) {
            this.callbacks.onOpen();
        }

        return this;
    }

    close() {
        if (!this.isOpen) return this;

        this.isOpen = false;

        // Hide backdrop
        this.backdrop.style.opacity = '0';
        this.backdrop.style.visibility = 'hidden';

        // Slide down sheet
        this.sheet.style.transform = 'translateY(100%)';

        // Restore body scroll
        document.body.style.overflow = '';

        if (this.callbacks.onClose) {
            this.callbacks.onClose();
        }

        return this;
    }

    toggle() {
        return this.isOpen ? this.close() : this.open();
    }

    onOpen(callback) {
        this.callbacks.onOpen = callback;
        return this;
    }

    onClose(callback) {
        this.callbacks.onClose = callback;
        return this;
    }

    destroy() {
        this.close();
        if (this.backdrop && this.backdrop.parentNode) {
            this.backdrop.parentNode.removeChild(this.backdrop);
        }
        if (this.sheet && this.sheet.parentNode) {
            this.sheet.parentNode.removeChild(this.sheet);
        }
    }
}

// Export for use
window.ActionSheet = ActionSheet;
