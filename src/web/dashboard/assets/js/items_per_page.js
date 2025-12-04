/**
 * Items Per Page Manager for Dashboard Tabs
 * Handles localStorage operations for items-per-page preferences across all tabs
 */

class ItemsPerPageManager {
    constructor() {
        this.storageKey = 'watchtower_items_per_page';
        this.defaultValues = {
            'videos': 48,
            'arxiv': 24,
            'news': 24,
            'deals': 48,
            'courses': 24,
            'games': 48,
            'github': 24,
            'giveaways': 48,
            'anime': 24,
            'fourchan': 48,
            'intelligence': 24,
            'scavenging': 48,
            'shortcuts': 24,
            'metrics': 24,
            'knowledge-garden': 24
        };
        this.allowedValues = [12, 24, 48, 96];
    }

    /**
     * Get all items-per-page preferences from localStorage
     */
    getAllPreferences() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            const preferences = stored ? JSON.parse(stored) : {};
            // Merge with defaults for any missing tabs
            return { ...this.defaultValues, ...preferences };
        } catch (error) {
            console.warn('Error reading items-per-page preferences from localStorage:', error);
            return this.defaultValues;
        }
    }

    /**
     * Save all preferences to localStorage
     */
    saveAllPreferences(preferences) {
        try {
            // Validate all values before saving
            const validPreferences = {};
            for (const [tab, value] of Object.entries(preferences)) {
                if (this.allowedValues.includes(value)) {
                    validPreferences[tab] = value;
                } else {
                    console.warn(`Invalid items-per-page value for ${tab}: ${value}, using default`);
                    validPreferences[tab] = this.defaultValues[tab] || 48;
                }
            }

            localStorage.setItem(this.storageKey, JSON.stringify(validPreferences));
            return true;
        } catch (error) {
            console.error('Error saving items-per-page preferences to localStorage:', error);
            return false;
        }
    }

    /**
     * Get preference for a specific tab
     */
    getPreference(tabName) {
        const preferences = this.getAllPreferences();
        return preferences[tabName] || this.defaultValues[tabName] || 48;
    }

    /**
     * Save preference for a specific tab
     */
    savePreference(tabName, itemsPerPage) {
        if (!this.allowedValues.includes(itemsPerPage)) {
            console.error(`Invalid items-per-page value: ${itemsPerPage}. Allowed values: ${this.allowedValues.join(', ')}`);
            return false;
        }

        const preferences = this.getAllPreferences();
        preferences[tabName] = itemsPerPage;

        return this.saveAllPreferences(preferences);
    }

    /**
     * Get default value for a tab
     */
    getDefaultValue(tabName) {
        return this.defaultValues[tabName] || 48;
    }

    /**
     * Get allowed values as options for dropdown
     */
    getOptions() {
        return this.allowedValues.map(value => ({
            'label': `${value} items`,
            'value': value
        }));
    }

    /**
     * Get allowed values
     */
    getAllowedValues() {
        return [...this.allowedValues];
    }

    /**
     * Validate items-per-page value
     */
    validateValue(value) {
        if (typeof value !== 'number' || !this.allowedValues.includes(value)) {
            return {
                valid: false,
                error: `Invalid items-per-page value: ${value}. Allowed values: ${this.allowedValues.join(', ')}`
            };
        }
        return { valid: true, error: null };
    }

    /**
     * Reset preference to default for a tab
     */
    resetPreference(tabName) {
        const defaultValue = this.getDefaultValue(tabName);
        return this.savePreference(tabName, defaultValue);
    }

    /**
     * Reset all preferences to defaults
     */
    resetAllPreferences() {
        return this.saveAllPreferences(this.defaultValues);
    }

    /**
     * Clear all preferences (remove from localStorage)
     */
    clearAllPreferences() {
        try {
            localStorage.removeItem(this.storageKey);
            return true;
        } catch (error) {
            console.error('Error clearing items-per-page preferences:', error);
            return false;
        }
    }

    /**
     * Get storage statistics
     */
    getStorageStats() {
        const preferences = this.getAllPreferences();
        const stats = {
            totalTabs: Object.keys(preferences).length,
            tabsWithCustomValues: 0,
            storageUsed: 0
        };

        // Count how many tabs have custom (non-default) values
        for (const [tabName, value] of Object.entries(preferences)) {
            if (this.defaultValues[tabName] && value !== this.defaultValues[tabName]) {
                stats.tabsWithCustomValues++;
            }
        }

        try {
            const stored = localStorage.getItem(this.storageKey);
            stats.storageUsed = stored ? stored.length : 0;
        } catch (error) {
            stats.storageUsed = -1; // Error calculating size
        }

        return stats;
    }

    /**
     * Apply preference immediately with performance tracking
     */
    applyPreference(tabName, itemsPerPage, callback) {
        const startTime = performance.now();

        try {
            // Save the preference first
            const saved = this.savePreference(tabName, itemsPerPage);

            if (saved) {
                // Call the provided callback to update the UI
                if (typeof callback === 'function') {
                    callback(tabName, itemsPerPage);
                }

                const endTime = performance.now();
                const duration = endTime - startTime;

                // Log performance for debugging
                if (duration > 200) {
                    console.warn(`Slow items-per-page preference application: ${duration.toFixed(2)}ms for ${tabName}`);
                } else {
                    console.log(`Items-per-page preference applied: ${itemsPerPage} for ${tabName} (${duration.toFixed(2)}ms)`);
                }

                return true;
            }

            return false;
        } catch (error) {
            console.error(`Error applying items-per-page preference for ${tabName}:`, error);
            return false;
        }
    }
}

// Create global instance
window.itemsPerPageManager = new ItemsPerPageManager();

// Make available for Dash callbacks
window.getItemsPerPage = function(tabName) {
    return window.itemsPerPageManager.getPreference(tabName);
};

window.saveItemsPerPage = function(tabName, itemsPerPage) {
    return window.itemsPerPageManager.savePreference(tabName, itemsPerPage);
};

window.getItemsPerPageOptions = function() {
    return window.itemsPerPageManager.getOptions();
};

window.resetItemsPerPage = function(tabName) {
    return window.itemsPerPageManager.resetPreference(tabName);
};

// Initialize preferences on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('ItemsPerPageManager initialized with defaults:', window.itemsPerPageManager.defaultValues);

    // Pre-warm localStorage with defaults if empty
    const existingPrefs = window.itemsPerPageManager.getAllPreferences();
    const hasCustomValues = Object.entries(existingPrefs).some(([tab, value]) =>
        value !== window.itemsPerPageManager.defaultValues[tab]
    );

    if (!hasCustomValues) {
        window.itemsPerPageManager.saveAllPreferences(existingPrefs);
    }
});
