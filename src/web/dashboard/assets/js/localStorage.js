/**
 * LocalStorage Manager for Filter Presets
 * Handles localStorage operations for dashboard filter presets
 */

class LocalStorageManager {
    constructor() {
        this.storageKey = 'watchtower_filter_presets';
        this.maxPresetsPerTab = 10;
    }

    /**
     * Get all presets from localStorage
     */
    getAllPresets() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            return stored ? JSON.parse(stored) : {};
        } catch (error) {
            console.warn('Error reading filter presets from localStorage:', error);
            return {};
        }
    }

    /**
     * Save presets to localStorage
     */
    saveAllPresets(presets) {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(presets));
            return true;
        } catch (error) {
            console.error('Error saving filter presets to localStorage:', error);
            return false;
        }
    }

    /**
     * Get presets for a specific tab
     */
    getPresets(tabName) {
        const presets = this.getAllPresets();
        return presets[tabName] || [];
    }

    /**
     * Save a preset for a specific tab
     */
    savePreset(tabName, presetName, filters) {
        const presets = this.getAllPresets();

        // Initialize tab if not exists
        if (!presets[tabName]) {
            presets[tabName] = [];
        }

        // Check for duplicate names
        const existingIndex = presets[tabName].findIndex(p => p.name === presetName);

        if (existingIndex !== -1) {
            // Update existing preset
            presets[tabName][existingIndex] = {
                name: presetName,
                filters: filters,
                created_at: presets[tabName][existingIndex].created_at,
                updated_at: new Date().toISOString()
            };
        } else {
            // Check maximum presets limit
            if (presets[tabName].length >= this.maxPresetsPerTab) {
                throw new Error(`Maximum ${this.maxPresetsPerTab} presets allowed per tab`);
            }

            // Add new preset
            presets[tabName].push({
                name: presetName,
                filters: filters,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            });
        }

        return this.saveAllPresets(presets);
    }

    /**
     * Update an existing preset
     */
    updatePreset(tabName, presetName, filters) {
        const presets = this.getAllPresets();

        if (!presets[tabName]) {
            throw new Error(`No presets found for tab: ${tabName}`);
        }

        const presetIndex = presets[tabName].findIndex(p => p.name === presetName);

        if (presetIndex === -1) {
            throw new Error(`Preset '${presetName}' not found for tab: ${tabName}`);
        }

        presets[tabName][presetIndex] = {
            name: presetName,
            filters: filters,
            created_at: presets[tabName][presetIndex].created_at,
            updated_at: new Date().toISOString()
        };

        return this.saveAllPresets(presets);
    }

    /**
     * Delete a preset
     */
    deletePreset(tabName, presetName) {
        const presets = this.getAllPresets();

        if (!presets[tabName]) {
            return true; // Nothing to delete
        }

        presets[tabName] = presets[tabName].filter(p => p.name !== presetName);

        // Remove tab if no presets left
        if (presets[tabName].length === 0) {
            delete presets[tabName];
        }

        return this.saveAllPresets(presets);
    }

    /**
     * Get preset names as options for dropdown
     */
    getPresetOptions(tabName) {
        const presets = this.getPresets(tabName);
        return presets.map(preset => ({
            label: preset.name,
            value: preset.name
        }));
    }

    /**
     * Validate preset name
     */
    validatePresetName(tabName, presetName) {
        if (!presetName || presetName.trim().length === 0) {
            return { valid: false, error: 'Preset name cannot be empty' };
        }

        if (presetName.length > 50) {
            return { valid: false, error: 'Preset name must be 50 characters or less' };
        }

        if (/[<>:"/\\|?*]/.test(presetName)) {
            return { valid: false, error: 'Preset name contains invalid characters' };
        }

        const presets = this.getPresets(tabName);
        const duplicate = presets.find(p => p.name === presetName.trim());

        if (duplicate) {
            return { valid: false, error: 'Preset name already exists' };
        }

        return { valid: true, error: null };
    }

    /**
     * Clear all presets for a tab
     */
    clearTabPresets(tabName) {
        const presets = this.getAllPresets();
        delete presets[tabName];
        return this.saveAllPresets(presets);
    }

    /**
     * Clear all presets (reset)
     */
    clearAllPresets() {
        try {
            localStorage.removeItem(this.storageKey);
            return true;
        } catch (error) {
            console.error('Error clearing filter presets:', error);
            return false;
        }
    }

    /**
     * Get storage statistics
     */
    getStorageStats() {
        const presets = this.getAllPresets();
        const stats = {
            totalPresets: 0,
            tabsWithPresets: 0,
            storageUsed: 0
        };

        for (const [tabName, tabPresets] of Object.entries(presets)) {
            stats.tabsWithPresets++;
            stats.totalPresets += tabPresets.length;
        }

        try {
            const stored = localStorage.getItem(this.storageKey);
            stats.storageUsed = stored ? stored.length : 0;
        } catch (error) {
            stats.storageUsed = -1; // Error calculating size
        }

        return stats;
    }
}

// Create global instance
window.filterPresetsManager = new LocalStorageManager();

// Make available for Dash callbacks
window.getFilterPresets = function(tabName) {
    return window.filterPresetsManager.getPresets(tabName);
};

window.saveFilterPreset = function(tabName, presetName, filters) {
    return window.filterPresetsManager.savePreset(tabName, presetName, filters);
};

window.deleteFilterPreset = function(tabName, presetName) {
    return window.filterPresetsManager.deletePreset(tabName, presetName);
};

window.getFilterPresetOptions = function(tabName) {
    return window.filterPresetsManager.getPresetOptions(tabName);
};