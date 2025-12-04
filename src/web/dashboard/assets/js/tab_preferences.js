/**
 * Tab Preferences Manager for Dashboard Tab Customization
 * Handles localStorage operations for dashboard tab visibility and ordering
 */

class TabPreferencesManager {
    constructor() {
        this.storageKey = 'watchtower_tab_preferences';
        this.defaultTabs = [
            { id: 'tab-shortcuts', label: 'Shortcuts', icon: 'fa-star', default_visible: true },
            { id: 'tab-news', label: 'News', icon: 'fa-newspaper', default_visible: true },
            { id: 'tab-notifications', label: '🔔 Notifications', icon: 'fa-bell', default_visible: true },
            { id: 'tab-knowledge-garden', label: '🌱 Knowledge Garden', icon: 'fa-seedling', default_visible: true },
            { id: 'tab-github-trending', label: 'GitHub Trending', icon: 'fa-github', default_visible: true },
            { id: 'tab-videos', label: 'Videos', icon: 'fa-video', default_visible: true },
            { id: 'tab-games', label: 'Games', icon: 'fa-gamepad', default_visible: true },
            { id: 'tab-intelligence', label: 'Intelligence', icon: 'fa-brain', default_visible: true },
            { id: 'tab-courses', label: 'Courses', icon: 'fa-graduation-cap', default_visible: true },
            { id: 'tab-anime', label: 'Anime', icon: 'fa-play-circle', default_visible: true },
            { id: 'tab-fourchan', label: '4chan', icon: 'fa-comment-dots', default_visible: true },
            { id: 'tab-scavenging', label: 'Scavenging', icon: 'fa-search', default_visible: true },
            { id: 'tab-valencia-events', label: 'Valencia Events', icon: 'fa-calendar', default_visible: true },
            { id: 'tab-giveaways', label: '🎁 Giveaways', icon: 'fa-gift', default_visible: true },
            { id: 'tab-spanish-aid', label: '🏛️ Ayudas Públicas', icon: 'fa-building', default_visible: true },
            { id: 'tab-arxiv-research', label: '📄 ArXiv Research', icon: 'fa-graduation-cap', default_visible: true },
            { id: 'tab-deals', label: '💰 Deals & Offers', icon: 'fa-tags', default_visible: true },
            { id: 'tab-metrics', label: '📊 Metrics', icon: 'fa-chart-bar', default_visible: true }
        ];
    }

    /**
     * Get all tab preferences from localStorage
     */
    getAllPreferences() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            const data = stored ? JSON.parse(stored) : {};

            // Ensure proper structure
            if (!data.tab_visibility) {
                data.tab_visibility = {};
            }
            if (!data.tab_order || !Array.isArray(data.tab_order)) {
                data.tab_order = [];
            }

            // Initialize missing tabs with defaults
            this.defaultTabs.forEach(tab => {
                if (data.tab_visibility[tab.id] === undefined) {
                    data.tab_visibility[tab.id] = tab.default_visible;
                }
                if (!data.tab_order.includes(tab.id)) {
                    data.tab_order.push(tab.id);
                }
            });

            // Remove tabs that no longer exist from order (but keep visibility settings)
            data.tab_order = data.tab_order.filter(tabId =>
                this.defaultTabs.some(tab => tab.id === tabId)
            );

            return data;
        } catch (error) {
            console.warn('Error reading tab preferences from localStorage:', error);
            return this.getDefaultPreferences();
        }
    }

    /**
     * Get default tab preferences
     */
    getDefaultPreferences() {
        const visibility = {};
        const order = [];

        // Create alphabetical order for default tabs
        const sortedTabs = [...this.defaultTabs].sort((a, b) => a.label.localeCompare(b.label));

        sortedTabs.forEach(tab => {
            visibility[tab.id] = tab.default_visible;
            if (tab.default_visible) {
                order.push(tab.id);
            }
        });

        return {
            tab_visibility: visibility,
            tab_order: order
        };
    }

    /**
     * Save tab preferences to localStorage
     */
    saveAllPreferences(preferences) {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(preferences));
            return true;
        } catch (error) {
            console.error('Error saving tab preferences to localStorage:', error);
            return false;
        }
    }

    /**
     * Save both visibility and order preferences
     */
    savePreferences(visibility, order) {
        const preferences = {
            tab_visibility: visibility,
            tab_order: order
        };

        return this.saveAllPreferences(preferences);
    }

    /**
     * Get visibility for all tabs
     */
    getVisibility() {
        const preferences = this.getAllPreferences();
        return preferences.tab_visibility;
    }

    /**
     * Get tab order
     */
    getOrder() {
        const preferences = this.getAllPreferences();
        return preferences.tab_order;
    }

    /**
     * Update visibility for a specific tab
     */
    updateTabVisibility(tabId, isVisible) {
        const preferences = this.getAllPreferences();
        preferences.tab_visibility[tabId] = isVisible;

        return this.saveAllPreferences(preferences);
    }

    /**
     * Update tab order
     */
    updateTabOrder(newOrder) {
        const preferences = this.getAllPreferences();

        // Validate new order
        if (!Array.isArray(newOrder)) {
            throw new Error('Tab order must be an array');
        }

        // Ensure all tabs exist and are unique
        const seenTabs = new Set();
        for (const tabId of newOrder) {
            if (!this.defaultTabs.some(tab => tab.id === tabId)) {
                throw new Error(`Unknown tab: ${tabId}`);
            }
            if (seenTabs.has(tabId)) {
                throw new Error(`Duplicate tab in order: ${tabId}`);
            }
            seenTabs.add(tabId);
        }

        preferences.tab_order = newOrder;
        return this.saveAllPreferences(preferences);
    }

    /**
     * Get visible tabs in correct order
     */
    getVisibleTabs() {
        const preferences = this.getAllPreferences();
        const visibility = preferences.tab_visibility;
        const order = preferences.tab_order;

        // Filter to only visible tabs and sort by order
        return this.defaultTabs
            .filter(tab => visibility[tab.id] && order.includes(tab.id))
            .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
    }

    /**
     * Get tab info by ID
     */
    getTabInfo(tabId) {
        return this.defaultTabs.find(tab => tab.id === tabId);
    }

    /**
     * Get all available tabs
     */
    getAllAvailableTabs() {
        return [...this.defaultTabs];
    }

    /**
     * Reset to default configuration
     */
    resetToDefault() {
        const defaultPrefs = this.getDefaultPreferences();
        return this.saveAllPreferences(defaultPrefs);
    }

    /**
     * Validate preferences structure
     */
    validatePreferences(preferences) {
        const errors = [];

        // Check tab_visibility
        if (!preferences.tab_visibility || typeof preferences.tab_visibility !== 'object') {
            errors.push('Invalid tab_visibility format');
        } else {
            // Check for unknown tabs
            Object.keys(preferences.tab_visibility).forEach(tabId => {
                if (!this.defaultTabs.some(tab => tab.id === tabId)) {
                    errors.push(`Unknown tab in visibility: ${tabId}`);
                }
            });
        }

        // Check tab_order
        if (!preferences.tab_order || !Array.isArray(preferences.tab_order)) {
            errors.push('Invalid tab_order format');
        } else {
            // Check for unknown or duplicate tabs
            const seenTabs = new Set();
            preferences.tab_order.forEach((tabId, index) => {
                if (!this.defaultTabs.some(tab => tab.id === tabId)) {
                    errors.push(`Unknown tab in order at position ${index}: ${tabId}`);
                }
                if (seenTabs.has(tabId)) {
                    errors.push(`Duplicate tab in order at position ${index}: ${tabId}`);
                }
                seenTabs.add(tabId);
            });
        }

        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    /**
     * Get storage statistics
     */
    getStorageStats() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            const size = stored ? stored.length : 0;
            const preferences = this.getAllPreferences();

            const visibleTabs = this.getVisibleTabs();
            const hiddenTabs = this.defaultTabs.filter(tab => !visibleTabs.includes(tab));

            return {
                storageSize: size,
                totalTabs: this.defaultTabs.length,
                visibleTabs: visibleTabs.length,
                hiddenTabs: hiddenTabs.length,
                lastUpdated: preferences.last_updated || null
            };
        } catch (error) {
            console.error('Error getting storage stats:', error);
            return {
                storageSize: -1,
                totalTabs: this.defaultTabs.length,
                visibleTabs: 0,
                hiddenTabs: 0,
                lastUpdated: null
            };
        }
    }

    /**
     * Export preferences for backup
     */
    exportPreferences() {
        const preferences = this.getAllPreferences();
        return {
            version: '1.0',
            exported_at: new Date().toISOString(),
            preferences: preferences
        };
    }

    /**
     * Import preferences from backup
     */
    importPreferences(exportData) {
        if (!exportData || !exportData.preferences) {
            throw new Error('Invalid export data format');
        }

        const validation = this.validatePreferences(exportData.preferences);
        if (!validation.isValid) {
            throw new Error(`Invalid preferences data: ${validation.errors.join(', ')}`);
        }

        // Add timestamp to track when preferences were last updated
        exportData.preferences.last_updated = new Date().toISOString();

        return this.saveAllPreferences(exportData.preferences);
    }

    /**
     * Check if a tab is visible
     */
    isTabVisible(tabId) {
        const visibility = this.getVisibility();
        return visibility[tabId] === true;
    }

    /**
     * Get the next visible tab ID in order
     */
    getNextVisibleTab(currentTabId) {
        const order = this.getOrder();
        const visibleTabs = this.getVisibleTabs();

        const currentVisibleIndex = visibleTabs.findIndex(tab => tab.id === currentTabId);
        if (currentVisibleIndex === -1 || currentVisibleIndex === visibleTabs.length - 1) {
            return null; // No next visible tab
        }

        return visibleTabs[currentVisibleIndex + 1].id;
    }

    /**
     * Get the previous visible tab ID in order
     */
    getPreviousVisibleTab(currentTabId) {
        const order = this.getOrder();
        const visibleTabs = this.getVisibleTabs();

        const currentVisibleIndex = visibleTabs.findIndex(tab => tab.id === currentTabId);
        if (currentVisibleIndex <= 0) {
            return null; // No previous visible tab
        }

        return visibleTabs[currentVisibleIndex - 1].id;
    }

    /**
     * Count visible tabs
     */
    getVisibleTabCount() {
        return this.getVisibleTabs().length;
    }

    /**
     * Count hidden tabs
     */
    getHiddenTabCount() {
        const visibility = this.getVisibility();
        return Object.values(visibility).filter(visible => !visible).length;
    }

    /**
     * Clear all preferences (reset to empty state)
     */
    clearAllPreferences() {
        try {
            localStorage.removeItem(this.storageKey);
            return true;
        } catch (error) {
            console.error('Error clearing tab preferences:', error);
            return false;
        }
    }
}

// Create global instance
window.tabPreferencesManager = new TabPreferencesManager();

// Make available for Dash callbacks
window.getTabPreferences = function() {
    return window.tabPreferencesManager.getAllPreferences();
};

window.saveTabPreferences = function(visibility, order) {
    return window.tabPreferencesManager.savePreferences(visibility, order);
};

window.updateTabVisibility = function(tabId, isVisible) {
    return window.tabPreferencesManager.updateTabVisibility(tabId, isVisible);
};

window.updateTabOrder = function(newOrder) {
    return window.tabPreferencesManager.updateTabOrder(newOrder);
};

window.getVisibleTabs = function() {
    return window.tabPreferencesManager.getVisibleTabs();
};

window.resetTabPreferences = function() {
    return window.tabPreferencesManager.resetToDefault();
};

window.isTabVisible = function(tabId) {
    return window.tabPreferencesManager.isTabVisible(tabId);
};
