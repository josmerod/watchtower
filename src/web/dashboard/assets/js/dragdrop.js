/**
 * Drag and Drop functionality for Shortcuts
 * Uses SortableJS for smooth drag-and-drop with visual feedback
 */

class ShortcutsDragDrop {
    constructor() {
        this.sortableInstances = new Map();
        this.isInitialized = false;
    }

    /**
     * Initialize drag-drop for shortcuts sidebar
     */
    initialize() {
        if (this.isInitialized) {
            return;
        }

        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupDragDrop());
        } else {
            this.setupDragDrop();
        }

        this.isInitialized = true;
    }

    /**
     * Setup drag-drop for shortcuts
     */
    setupDragDrop() {
        try {
            // Make sure SortableJS is available
            if (typeof Sortable === 'undefined') {
                console.warn('SortableJS not available, drag-drop disabled');
                return;
            }

            // Setup drag-drop for each domain container
            const domainContainers = document.querySelectorAll('[id^="shortcuts-domain-"]');

            domainContainers.forEach(container => {
                this.setupDomainContainer(container);
            });

            console.log('Drag-drop initialized for shortcuts');
        } catch (error) {
            console.error('Error setting up drag-drop:', error);
        }
    }

    /**
     * Setup drag-drop for a specific domain container
     */
    setupDomainContainer(container) {
        try {
            const domainId = container.id;

            // Destroy existing instance if any
            if (this.sortableInstances.has(domainId)) {
                this.sortableInstances.get(domainId).destroy();
            }

            // Create new Sortable instance
            const sortable = Sortable.create(container, {
                group: 'shortcuts', // Allows dragging between domains
                animation: 150,
                ghostClass: 'shortcut-ghost',
                chosenClass: 'shortcut-chosen',
                dragClass: 'shortcut-dragging',
                handle: '.shortcut-card', // Use the entire card as handle
                forceFallback: false,
                fallbackOnBody: true,
                swapThreshold: 0.65,
                onStart: (evt) => this.onDragStart(evt),
                onEnd: (evt) => this.onDragEnd(evt),
                onMove: (evt) => this.onDragMove(evt)
            });

            this.sortableInstances.set(domainId, sortable);

        } catch (error) {
            console.error(`Error setting up drag-drop for container ${container.id}:`, error);
        }
    }

    /**
     * Handle drag start
     */
    onDragStart(evt) {
        const item = evt.item;
        const shortcutId = item.getAttribute('data-shortcut-id');

        // Add visual feedback
        item.style.opacity = '0.8';
        item.classList.add('dragging');

        // Store original domain for potential reversion
        item.setAttribute('data-original-domain', item.getAttribute('data-domain'));

        console.log('Started dragging shortcut:', shortcutId);
    }

    /**
     * Handle drag move between domains
     */
    onDragMove(evt) {
        const toDomain = evt.to.closest('[id^="shortcuts-domain-"]');
        const fromDomain = evt.from.closest('[id^="shortcuts-domain-"]');

        if (toDomain && fromDomain && toDomain !== fromDomain) {
            // Extract domain name from container ID
            const newDomain = toDomain.id.replace('shortcuts-domain-', '').replace(/-/g, ' ');
            const formattedDomain = this.formatDomainName(newDomain);

            // Update visual feedback
            evt.item.setAttribute('data-temp-domain', formattedDomain);
        }

        return true; // Allow move
    }

    /**
     * Handle drag end
     */
    onDragEnd(evt) {
        const item = evt.item;
        const shortcutId = item.getAttribute('data-shortcut-id');
        const fromDomain = this.formatDomainName(evt.from.id.replace('shortcuts-domain-', '').replace(/-/g, ' '));
        const toDomain = evt.to ? this.formatDomainName(evt.to.id.replace('shortcuts-domain-', '').replace(/-/g, ' ')) : fromDomain;

        // Remove visual feedback
        item.style.opacity = '';
        item.classList.remove('dragging');

        // Update domain if moved to different domain
        if (fromDomain !== toDomain) {
            item.setAttribute('data-domain', toDomain);

            // Update the domain badge in the card
            const badge = item.querySelector('.badge');
            if (badge) {
                badge.textContent = toDomain;
                badge.className = `badge me-2 bg-${this.getDomainColor(toDomain)}`;
            }

            console.log(`Moved shortcut ${shortcutId} from ${fromDomain} to ${toDomain}`);
        }

        // Save the new order
        this.saveNewOrder();
    }

    /**
     * Format domain name from container ID
     */
    formatDomainName(domainId) {
        // Convert domain-id to Domain Name
        return domainId.split('-').map(word =>
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    /**
     * Get Bootstrap color for domain
     */
    getDomainColor(domain) {
        const colors = {
            'Papers': 'primary',
            'News': 'success',
            'Deals': 'danger',
            'Courses': 'info',
            'Videos': 'warning',
            'AI': 'dark',
            'Entertainment': 'secondary',
            'Other': 'light'
        };
        return colors[domain] || 'light';
    }

    /**
     * Save the new order of shortcuts
     */
    async saveNewOrder() {
        try {
            if (!window.shortcutsManager) {
                console.error('ShortcutsManager not available');
                return;
            }

            // Collect all shortcuts in their new order
            const allShortcuts = [];
            const domainContainers = document.querySelectorAll('[id^="shortcuts-domain-"]');

            domainContainers.forEach(container => {
                const domain = this.formatDomainName(container.id.replace('shortcuts-domain-', '').replace(/-/g, ' '));
                const cards = container.querySelectorAll('.shortcut-card');

                cards.forEach((card, index) => {
                    const shortcutId = card.getAttribute('data-shortcut-id');
                    const existingShortcut = window.shortcutsManager.getShortcut(shortcutId);

                    if (existingShortcut) {
                        // Update domain and order
                        const updatedShortcut = {
                            ...existingShortcut,
                            domain: domain,
                            order: allShortcuts.length
                        };
                        allShortcuts.push(updatedShortcut);
                    }
                });
            });

            // Update all shortcuts with new order and domain
            const updatePromises = allShortcuts.map(shortcut =>
                window.shortcutsManager.updateShortcut(shortcut.id, {
                    domain: shortcut.domain,
                    source_filter: shortcut.source_filter
                })
            );

            // Reorder shortcuts by new order
            const newOrder = allShortcuts.map(s => s.id);
            await window.shortcutsManager.reorderShortcuts(newOrder);

            console.log('Shortcuts order saved successfully');

            // Trigger UI refresh
            this.triggerRefresh();

        } catch (error) {
            console.error('Error saving shortcuts order:', error);
            // Optional: Show error message to user
            this.showError('Failed to save shortcuts order');
        }
    }

    /**
     * Trigger UI refresh
     */
    triggerRefresh() {
        const trigger = document.getElementById('shortcuts-updates-trigger');
        if (trigger) {
            trigger.innerHTML = Date.now();
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        // Simple error notification (could be enhanced with toast)
        const alert = document.createElement('div');
        alert.className = 'alert alert-warning alert-dismissible fade show position-fixed';
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alert);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }

    /**
     * Refresh drag-drop setup (call after DOM changes)
     */
    refresh() {
        this.setupDragDrop();
    }

    /**
     * Destroy all sortable instances
     */
    destroy() {
        this.sortableInstances.forEach(instance => {
            try {
                instance.destroy();
            } catch (error) {
                console.warn('Error destroying sortable instance:', error);
            }
        });
        this.sortableInstances.clear();
        this.isInitialized = false;
    }
}

// Create global instance
window.shortcutsDragDrop = new ShortcutsDragDrop();

// Auto-initialize when shortcuts sidebar is opened
document.addEventListener('shown.bs.offcanvas', function(e) {
    if (e.target && e.target.id && e.target.id.includes('shortcuts-sidebar')) {
        // Initialize drag-drop when sidebar opens
        setTimeout(() => {
            window.shortcutsDragDrop.refresh();
        }, 100);
    }
});

// Initialize on page load if shortcuts are visible
window.addEventListener('load', function() {
    window.shortcutsDragDrop.initialize();
});
