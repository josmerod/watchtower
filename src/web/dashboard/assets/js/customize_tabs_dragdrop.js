/**
 * Drag and Drop functionality for Dashboard Tab Customization
 * Handles tab reordering within the customization modal using SortableJS
 */

class CustomizeTabsDragDrop {
    constructor(customizeTabsComponent) {
        this.customizeTabsComponent = customizeTabsComponent;
        this.sortableInstances = new Map();
        this.draggedElement = null;
        this.placeholderHeight = 60;
        this.dragStartTime = 0;
        this.isProcessing = false;

        this.init();
    }

    init() {
        // Initialize SortableJS when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initializeSortable();
            });
        } else {
            this.initializeSortable();
        }
    }

    /**
     * Initialize SortableJS for tab reordering
     */
    initializeSortable() {
        try {
            // Wait for tabs to be rendered in the modal
            const checkForTabs = () => {
                const container = document.getElementById(this.customizeTabsComponent.tabs_container_id);
                if (container && container.children.length > 0) {
                    this.createSortableInstance(container);
                } else {
                    // If tabs not loaded yet, check again after delay
                    setTimeout(checkForTabs, 500);
                }
            };

            // Trigger tab loading and then check for container
            const trigger = document.getElementById('customize-tabs-trigger');
            if (trigger) {
                trigger.innerHTML = Date.now();
            }

            setTimeout(checkForTabs, 1000);

        } catch (error) {
            console.error('Error initializing SortableJS:', error);
        }
    }

    /**
     * Create SortableJS instance for the tabs container
     */
    createSortableInstance(container) {
        try {
            // Destroy existing instance if present
            const existingInstance = this.sortableInstances.get(container.id);
            if (existingInstance) {
                existingInstance.destroy();
            }

            const sortableInstance = new Sortable(container, {
                group: 'tabs-reorder',
                animation: 200,
                ghostClass: 'tab-customization-ghost',
                chosenClass: 'tab-customization-chosen',
                dragClass: 'tab-customization-dragging',
                forceFallback: false,
                fallbackTolerance: 3,
                scroll: true,
                scrollSensitivity: 30,
                scrollSpeed: 20,
                bubbleScroll: true,
                dataIdAttr: 'data-tab-id',
                onStart: (evt) => this.handleDragStart(evt),
                onMove: (evt) => this.handleDragMove(evt),
                onEnd: (evt) => this.handleDragEnd(evt),
                onAdd: (evt) => this.handleDragAdd(evt),
                onRemove: (evt) => this.handleDragRemove(evt),
                onUpdate: (evt) => this.handleDragUpdate(evt),
                onSort: (evt) => this.handleDragSort(evt),
                onFilter: (evt) => this.handleDragFilter(evt),
                onUnchoose: (evt) => this.handleDragUnchoose(evt)
            });

            this.sortableInstances.set(container.id, sortableInstance);

            // Add visual indicators to tab items
            this.addDragIndicators(container);

            console.log(`SortableJS instance created for tabs container: ${container.id}`);

        } catch (error) {
            console.error('Error creating SortableJS instance:', error);
            this.showDragDropError('Failed to initialize drag and drop functionality');
        }
    }

    /**
     * Add visual indicators for draggable items
     */
    addDragIndicators(container) {
        const tabItems = container.querySelectorAll('.customize-tab-item');
        tabItems.forEach(item => {
            if (!item.querySelector('.drag-handle')) {
                const dragHandle = item.querySelector('.fa-grip-vertical');
                if (dragHandle) {
                    dragHandle.style.cursor = 'grab';
                    dragHandle.style.color = '#6c757d';
                    dragHandle.title = 'Drag to reorder tab';
                }
            }
        });
    }

    /**
     * Handle drag start event
     */
    handleDragStart(evt) {
        this.draggedElement = evt.item;
        this.dragStartTime = Date.now();
        this.isProcessing = true;

        // Add drag start styling
        evt.item.classList.add('tab-dragging');

        // Update cursor style
        const dragHandle = evt.item.querySelector('.fa-grip-vertical');
        if (dragHandle) {
            dragHandle.style.cursor = 'grabbing';
        }

        // Store original order for rollback if needed
        this.originalOrder = Array.from(evt.item.parentNode.children)
            .map(child => child.getAttribute('data-tab-id'));

        console.log('Started dragging tab:', evt.item.getAttribute('data-tab-id'));
    }

    /**
     * Handle drag move event
     */
    handleDragMove(evt) {
        // Add visual feedback for valid drop zones
        const targetTab = evt.related;
        if (targetTab && targetTab.classList.contains('customize-tab-item')) {
            targetTab.style.backgroundColor = 'rgba(0, 123, 255, 0.1)';
        }

        return true; // Allow move
    }

    /**
     * Handle drag end event
     */
    handleDragEnd(evt) {
        this.isProcessing = false;

        // Remove drag styling
        evt.item.classList.remove('tab-dragging');

        // Reset cursor style
        const dragHandle = evt.item.querySelector('.fa-grip-vertical');
        if (dragHandle) {
            dragHandle.style.cursor = 'grab';
        }

        // Clear all visual feedback
        const allTabs = evt.item.parentNode.querySelectorAll('.customize-tab-item');
        allTabs.forEach(tab => {
            tab.style.backgroundColor = '';
        });

        const dragDuration = Date.now() - this.dragStartTime;
        console.log(`Finished dragging tab in ${dragDuration}ms`);

        // Update stats to reflect new order
        this.updateTabStats();
    }

    /**
     * Handle drag add event (for multi-container scenarios)
     */
    handleDragAdd(evt) {
        console.log('Tab added to container:', evt.item.getAttribute('data-tab-id'));
    }

    /**
     * Handle drag remove event
     */
    handleDragRemove(evt) {
        console.log('Tab removed from container:', evt.item.getAttribute('data-tab-id'));
    }

    /**
     * Handle drag update event (main reordering logic)
     */
    handleDragUpdate(evt) {
        const tabId = evt.item.getAttribute('data-tab-id');
        const oldIndex = evt.oldIndex;
        const newIndex = evt.newIndex;

        console.log(`Tab reordered: ${tabId} from position ${oldIndex} to ${newIndex}`);

        // Update the tab preferences manager with new order
        this.updateTabOrderFromDOM();
    }

    /**
     * Handle drag sort event
     */
    handleDragSort(evt) {
        // This fires for any sorting within the same container
        console.log('Tabs sorted within container');
    }

    /**
     * Handle drag filter event
     */
    handleDragFilter(evt) {
        console.log('Drag filter event:', evt);
    }

    /**
     * Handle drag unchoose event
     */
    handleDragUnchoose(evt) {
        console.log('Drag unchoose event:', evt);
    }

    /**
     * Update tab order from DOM
     */
    updateTabOrderFromDOM() {
        try {
            const container = document.getElementById(this.customizeTabsComponent.tabs_container_id);
            if (!container) return;

            const newOrder = Array.from(container.children)
                .map(child => child.getAttribute('data-tab-id'))
                .filter(id => id); // Filter out null values

            // Get current visibility settings
            const tabManager = window.tabPreferencesManager;
            if (!tabManager) {
                console.error('TabPreferencesManager not available');
                return;
            }

            const currentPreferences = tabManager.getAllPreferences();
            const updatedPreferences = {
                ...currentPreferences,
                tab_order: newOrder
            };

            // Save updated preferences
            const success = tabManager.saveAllPreferences(updatedPreferences);

            if (success) {
                console.log('Tab order updated successfully:', newOrder);
                this.showDragDropSuccess('Tab order updated');
            } else {
                console.error('Failed to save updated tab order');
                this.showDragDropError('Failed to save tab order');
            }

        } catch (error) {
            console.error('Error updating tab order from DOM:', error);
            this.showDragDropError('Error updating tab order');
        }
    }

    /**
     * Update tab statistics in the modal
     */
    updateTabStats() {
        try {
            const statsElement = document.getElementById(this.customizeTabsComponent.stats_id);
            if (!statsElement) return;

            const tabManager = window.tabPreferencesManager;
            if (!tabManager) return;

            const totalTabs = tabManager.getAllAvailableTabs().length;
            const visibleCount = tabManager.getVisibleTabCount();

            statsElement.innerHTML = `
                <strong>${visibleCount}</strong> of ${totalTabs} tabs visible
            `;

        } catch (error) {
            console.error('Error updating tab stats:', error);
        }
    }

    /**
     * Show success message for drag drop operations
     */
    showDragDropSuccess(message) {
        this.showNotification(message, 'success');
    }

    /**
     * Show error message for drag drop operations
     */
    showDragDropError(message) {
        this.showNotification(message, 'danger');
    }

    /**
     * Show notification message
     */
    showNotification(message, type = 'info') {
        try {
            // Create notification element
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
            notification.style.cssText = `
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 300px;
                font-size: 0.875rem;
            `;

            notification.innerHTML = `
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            document.body.appendChild(notification);

            // Auto-remove after 3 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 3000);

        } catch (error) {
            console.error('Error showing notification:', error);
        }
    }

    /**
     * Destroy all SortableJS instances
     */
    destroy() {
        try {
            this.sortableInstances.forEach((instance, containerId) => {
                instance.destroy();
                console.log(`Destroyed SortableJS instance for container: ${containerId}`);
            });
            this.sortableInstances.clear();
        } catch (error) {
            console.error('Error destroying SortableJS instances:', error);
        }
    }

    /**
     * Refresh sortable instances (useful after dynamic content updates)
     */
    refresh() {
        try {
            // Destroy existing instances
            this.destroy();

            // Reinitialize after a short delay
            setTimeout(() => {
                this.initializeSortable();
            }, 100);

        } catch (error) {
            console.error('Error refreshing sortable instances:', error);
        }
    }

    /**
     * Get current drag statistics
     */
    getDragStats() {
        return {
            activeInstances: this.sortableInstances.size,
            isDragging: this.isProcessing,
            hasDraggedElement: this.draggedElement !== null
        };
    }

    /**
     * Check if drag and drop is supported
     */
    isSupported() {
        return typeof Sortable !== 'undefined';
    }
}

// Auto-initialize when CustomizrTabs component is available
document.addEventListener('DOMContentLoaded', () => {
    // Wait for customizeTabs component to be available
    const initializeDragDrop = () => {
        if (typeof customize_tabs !== 'undefined') {
            window.customizeTabsDragDrop = new CustomizeTabsDragDrop(customize_tabs);
            console.log('CustomizeTabs drag-and-drop initialized');
        } else {
            setTimeout(initializeDragDrop, 500);
        }
    };

    initializeDragDrop();
});

// Make available globally
window.CustomizeTabsDragDrop = CustomizeTabsDragDrop;
