/**
 * Shortcuts Manager for Personal Source Shortcuts
 * Handles localStorage operations for dashboard source shortcuts
 */

class ShortcutsManager {
    constructor() {
        this.storageKey = 'watchtower_source_shortcuts';
        this.maxShortcuts = 50; // Maximum total shortcuts
        this.domainGroups = {
            'Papers': ['arxiv', 'pubmed', 'research'],
            'News': ['hackernews', 'reddit', 'medium', 'news'],
            'Deals': ['steam', 'epic', 'humble', 'gog', 'deals'],
            'Courses': ['udemy', 'coursera', 'edx', 'learning'],
            'Videos': ['youtube', 'vimeo', 'video'],
            'AI': ['openai', 'anthropic', 'huggingface', 'ai'],
            'Entertainment': ['cinema', 'anime', 'games', 'entertainment'],
            'Other': []
        };
    }

    /**
     * Generate unique shortcut ID
     */
    generateId() {
        return `shortcut_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Determine domain group from source identifier
     */
    getDomainGroup(sourceIdentifier) {
        const identifier = sourceIdentifier.toLowerCase();

        for (const [group, keywords] of Object.entries(this.domainGroups)) {
            if (keywords.some(keyword => identifier.includes(keyword))) {
                return group;
            }
        }

        return 'Other';
    }

    /**
     * Get all shortcuts from localStorage
     */
    getAllShortcuts() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            const data = stored ? JSON.parse(stored) : { shortcuts: [] };

            // Validate and clean up data
            if (!Array.isArray(data.shortcuts)) {
                console.warn('Invalid shortcuts data format, resetting');
                return { shortcuts: [] };
            }

            // Filter out invalid shortcuts and sort by order
            const validShortcuts = data.shortcuts
                .filter(shortcut => this.isValidShortcut(shortcut))
                .sort((a, b) => (a.order || 0) - (b.order || 0));

            return { shortcuts: validShortcuts };
        } catch (error) {
            console.warn('Error reading shortcuts from localStorage:', error);
            return { shortcuts: [] };
        }
    }

    /**
     * Validate shortcut object structure
     */
    isValidShortcut(shortcut) {
        return shortcut &&
               typeof shortcut.id === 'string' &&
               typeof shortcut.name === 'string' &&
               typeof shortcut.domain === 'string' &&
               typeof shortcut.source_filter === 'object' &&
               typeof shortcut.order === 'number' &&
               shortcut.name.trim().length > 0;
    }

    /**
     * Save shortcuts to localStorage
     */
    saveAllShortcuts(data) {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('Error saving shortcuts to localStorage:', error);
            return false;
        }
    }

    /**
     * Add a new shortcut
     */
    addShortcut(name, domain, sourceFilter) {
        if (!name || name.trim().length === 0) {
            throw new Error('Shortcut name cannot be empty');
        }

        if (name.length > 100) {
            throw new Error('Shortcut name must be 100 characters or less');
        }

        const data = this.getAllShortcuts();

        // Check for duplicate names
        const existing = data.shortcuts.find(s => s.name.toLowerCase() === name.trim().toLowerCase());
        if (existing) {
            throw new Error(`Shortcut '${name}' already exists`);
        }

        // Check maximum shortcuts limit
        if (data.shortcuts.length >= this.maxShortcuts) {
            throw new Error(`Maximum ${this.maxShortcuts} shortcuts allowed`);
        }

        // Determine domain group if not provided
        const domainGroup = this.getDomainGroup(domain);

        const newShortcut = {
            id: this.generateId(),
            name: name.trim(),
            domain: domainGroup,
            source_filter: sourceFilter,
            order: data.shortcuts.length,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        data.shortcuts.push(newShortcut);

        if (this.saveAllShortcuts(data)) {
            return newShortcut;
        } else {
            throw new Error('Failed to save shortcut');
        }
    }

    /**
     * Update an existing shortcut
     */
    updateShortcut(id, updates) {
        const data = this.getAllShortcuts();
        const shortcutIndex = data.shortcuts.findIndex(s => s.id === id);

        if (shortcutIndex === -1) {
            throw new Error(`Shortcut with ID '${id}' not found`);
        }

        const shortcut = data.shortcuts[shortcutIndex];

        // Update allowed fields
        if (updates.name) {
            if (updates.name.trim().length === 0) {
                throw new Error('Shortcut name cannot be empty');
            }

            if (updates.name.length > 100) {
                throw new Error('Shortcut name must be 100 characters or less');
            }

            shortcut.name = updates.name.trim();
        }

        if (updates.source_filter) {
            shortcut.source_filter = updates.source_filter;
        }

        shortcut.updated_at = new Date().toISOString();

        data.shortcuts[shortcutIndex] = shortcut;

        if (this.saveAllShortcuts(data)) {
            return shortcut;
        } else {
            throw new Error('Failed to update shortcut');
        }
    }

    /**
     * Remove a shortcut
     */
    removeShortcut(id) {
        const data = this.getAllShortcuts();
        const initialCount = data.shortcuts.length;

        data.shortcuts = data.shortcuts.filter(s => s.id !== id);

        // Reorder remaining shortcuts
        data.shortcuts.forEach((shortcut, index) => {
            shortcut.order = index;
        });

        if (data.shortcuts.length < initialCount) {
            if (this.saveAllShortcuts(data)) {
                return true;
            } else {
                throw new Error('Failed to save after removing shortcut');
            }
        }

        return false; // Shortcut not found
    }

    /**
     * Reorder shortcuts
     */
    reorderShortcuts(newOrder) {
        const data = this.getAllShortcuts();

        if (!Array.isArray(newOrder) || newOrder.length !== data.shortcuts.length) {
            throw new Error('Invalid new order array');
        }

        // Create a map of ID -> new order
        const orderMap = new Map(newOrder.map((id, index) => [id, index]));

        // Update order for each shortcut
        data.shortcuts.forEach(shortcut => {
            if (orderMap.has(shortcut.id)) {
                shortcut.order = orderMap.get(shortcut.id);
            }
        });

        // Sort by new order
        data.shortcuts.sort((a, b) => a.order - b.order);

        return this.saveAllShortcuts(data);
    }

    /**
     * Get shortcuts grouped by domain
     */
    getShortcutsByDomain() {
        const data = this.getAllShortcuts();
        const grouped = {};

        // Initialize domain groups
        Object.keys(this.domainGroups).forEach(domain => {
            grouped[domain] = [];
        });

        // Group shortcuts
        data.shortcuts.forEach(shortcut => {
            const domain = shortcut.domain || 'Other';
            if (!grouped[domain]) {
                grouped[domain] = [];
            }
            grouped[domain].push(shortcut);
        });

        return grouped;
    }

    /**
     * Get shortcut by ID
     */
    getShortcut(id) {
        const data = this.getAllShortcuts();
        return data.shortcuts.find(s => s.id === id);
    }

    /**
     * Check if a source shortcut already exists
     */
    shortcutExists(name, sourceFilter) {
        const data = this.getAllShortcuts();
        return data.shortcuts.some(shortcut =>
            shortcut.name.toLowerCase() === name.toLowerCase() ||
            JSON.stringify(shortcut.source_filter) === JSON.stringify(sourceFilter)
        );
    }

    /**
     * Get storage statistics
     */
    getStorageStats() {
        const data = this.getAllShortcuts();
        const grouped = this.getShortcutsByDomain();

        const stats = {
            totalShortcuts: data.shortcuts.length,
            maxShortcuts: this.maxShortcuts,
            domainCounts: {},
            storageUsed: 0
        };

        Object.keys(grouped).forEach(domain => {
            stats.domainCounts[domain] = grouped[domain].length;
        });

        try {
            const stored = localStorage.getItem(this.storageKey);
            stats.storageUsed = stored ? stored.length : 0;
        } catch (error) {
            stats.storageUsed = -1; // Error calculating size
        }

        return stats;
    }

    /**
     * Clear all shortcuts
     */
    clearAllShortcuts() {
        try {
            localStorage.removeItem(this.storageKey);
            return true;
        } catch (error) {
            console.error('Error clearing shortcuts:', error);
            return false;
        }
    }

    /**
     * Export shortcuts for backup
     */
    exportShortcuts() {
        const data = this.getAllShortcuts();
        return {
            version: '1.0',
            exported_at: new Date().toISOString(),
            shortcuts: data.shortcuts
        };
    }

    /**
     * Import shortcuts from backup
     */
    importShortcuts(exportData) {
        if (!exportData || !Array.isArray(exportData.shortcuts)) {
            throw new Error('Invalid export data format');
        }

        const data = { shortcuts: [] };

        // Validate and import shortcuts
        exportData.shortcuts.forEach((shortcut, index) => {
            if (this.isValidShortcut(shortcut)) {
                // Generate new ID to avoid conflicts
                const newShortcut = {
                    ...shortcut,
                    id: this.generateId(),
                    order: index,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString()
                };
                data.shortcuts.push(newShortcut);
            }
        });

        return this.saveAllShortcuts(data);
    }
}

// Create global instance
window.shortcutsManager = new ShortcutsManager();

// Make available for Dash callbacks
window.getAllShortcuts = function() {
    return window.shortcutsManager.getAllShortcuts();
};

window.addShortcut = function(name, domain, sourceFilter) {
    return window.shortcutsManager.addShortcut(name, domain, sourceFilter);
};

window.removeShortcut = function(id) {
    return window.shortcutsManager.removeShortcut(id);
};

window.updateShortcut = function(id, updates) {
    return window.shortcutsManager.updateShortcut(id, updates);
};

window.reorderShortcuts = function(newOrder) {
    return window.shortcutsManager.reorderShortcuts(newOrder);
};

window.getShortcutsByDomain = function() {
    return window.shortcutsManager.getShortcutsByDomain();
};

window.getShortcutStats = function() {
    return window.shortcutsManager.getStorageStats();
};
