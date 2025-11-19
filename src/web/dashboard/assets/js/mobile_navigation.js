/**
 * Mobile Navigation JavaScript for Watchtower Dashboard
 * Handles hamburger menu functionality and mobile-specific navigation behaviors
 */

class MobileNavigation {
    constructor() {
        this.isMobile = window.innerWidth <= 768;
        this.mobileNavContainer = null;
        this.mobileNavToggle = null;
        this.mobileNavClose = null;
        this.currentActiveTab = null;

        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }

        // Listen for resize events
        window.addEventListener('resize', this.debounce(this.handleResize.bind(this), 250));
    }

    setup() {
        this.createMobileNavigation();
        this.setupEventListeners();
        this.initializeFromCurrentState();
    }

    createMobileNavigation() {
        // Create mobile navigation toggle button
        this.mobileNavToggle = document.createElement('button');
        this.mobileNavToggle.className = 'mobile-nav-toggle btn btn-outline-primary';
        this.mobileNavToggle.innerHTML = `
            <i class="fas fa-bars"></i>
            <span class="ms-2">Menu</span>
        `;
        this.mobileNavToggle.setAttribute('aria-label', 'Toggle navigation menu');
        this.mobileNavToggle.setAttribute('aria-expanded', 'false');
        this.mobileNavToggle.style.display = this.isMobile ? 'block' : 'none';

        // Create mobile navigation container
        this.mobileNavContainer = document.createElement('div');
        this.mobileNavContainer.className = 'mobile-nav-container';
        this.mobileNavContainer.setAttribute('role', 'navigation');
        this.mobileNavContainer.setAttribute('aria-label', 'Mobile navigation');

        // Create mobile navigation header
        const mobileNavHeader = document.createElement('div');
        mobileNavHeader.className = 'mobile-nav-header';

        const mobileNavTitle = document.createElement('h2');
        mobileNavTitle.className = 'h5 mb-0';
        mobileNavTitle.textContent = 'Navigation';

        // Create close button
        this.mobileNavClose = document.createElement('button');
        this.mobileNavClose.className = 'btn btn-outline-secondary btn-sm';
        this.mobileNavClose.innerHTML = '<i class="fas fa-times"></i>';
        this.mobileNavClose.setAttribute('aria-label', 'Close navigation menu');

        mobileNavHeader.appendChild(mobileNavTitle);
        mobileNavHeader.appendChild(this.mobileNavClose);

        // Create navigation list
        const mobileNavList = this.createMobileNavList();

        this.mobileNavContainer.appendChild(mobileNavHeader);
        this.mobileNavContainer.appendChild(mobileNavList);

        // Add elements to page
        this.addElementsToPage();
    }

    createMobileNavList() {
        const navList = document.createElement('ul');
        navList.className = 'mobile-nav-list';

        // Find all desktop tabs and create mobile equivalents
        const desktopTabs = document.querySelectorAll('.nav-tabs .nav-link');

        desktopTabs.forEach((tab, index) => {
            const tabId = tab.getAttribute('aria-controls') || tab.id || `tab-${index}`;
            const isActive = tab.classList.contains('active');
            const tabLabel = tab.textContent.trim();
            const tabIcon = this.extractIconFromLabel(tabLabel);

            const listItem = document.createElement('li');
            listItem.className = 'mobile-nav-item';

            const link = document.createElement('a');
            link.className = `mobile-nav-link ${isActive ? 'active' : ''}`;
            link.href = '#';
            link.setAttribute('data-tab-id', tabId);
            link.setAttribute('role', 'tab');
            link.setAttribute('aria-selected', isActive ? 'true' : 'false');
            link.setAttribute('aria-controls', tabId);

            if (tabIcon) {
                link.innerHTML = `<span class="me-2">${tabIcon}</span>${tabLabel}`;
            } else {
                link.textContent = tabLabel;
            }

            // Add click handler
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleMobileTabClick(tabId, link);
            });

            listItem.appendChild(link);
            navList.appendChild(listItem);

            if (isActive) {
                this.currentActiveTab = tabId;
            }
        });

        return navList;
    }

    extractIconFromLabel(label) {
        // Extract emojis or icon patterns from tab labels
        const iconMatch = label.match(/^[\p{Emoji}\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}]/u);
        return iconMatch ? iconMatch[0] : null;
    }

    addElementsToPage() {
        // Find the header buttons container or create one
        let buttonsContainer = document.querySelector('.header-buttons');
        if (!buttonsContainer) {
            // Look for the existing buttons container
            const existingButtons = document.querySelector('.d-flex.gap-2');
            if (existingButtons) {
                buttonsContainer = existingButtons;
            }
        }

        if (buttonsContainer) {
            buttonsContainer.appendChild(this.mobileNavToggle);
        } else {
            // Fallback: add to the first div in the header row
            const headerRow = document.querySelector('.container > .row:first-child');
            if (headerRow) {
                headerRow.appendChild(this.mobileNavToggle);
            }
        }

        // Add mobile navigation to body
        document.body.appendChild(this.mobileNavContainer);
    }

    setupEventListeners() {
        // Toggle button click
        this.mobileNavToggle.addEventListener('click', () => {
            this.toggleMobileNav();
        });

        // Close button click
        this.mobileNavClose.addEventListener('click', () => {
            this.closeMobileNav();
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.mobileNavContainer.classList.contains('show')) {
                this.closeMobileNav();
            }
        });

        // Close on outside click
        this.mobileNavContainer.addEventListener('click', (e) => {
            if (e.target === this.mobileNavContainer) {
                this.closeMobileNav();
            }
        });

        // Handle touch events for better mobile experience
        let touchStartY = 0;
        this.mobileNavContainer.addEventListener('touchstart', (e) => {
            touchStartY = e.touches[0].clientY;
        });

        this.mobileNavContainer.addEventListener('touchmove', (e) => {
            const touchEndY = e.touches[0].clientY;
            const diff = touchStartY - touchEndY;

            // Swipe down to close
            if (diff < -50) {
                this.closeMobileNav();
            }
        });
    }

    toggleMobileNav() {
        const isOpen = this.mobileNavContainer.classList.contains('show');

        if (isOpen) {
            this.closeMobileNav();
        } else {
            this.openMobileNav();
        }
    }

    openMobileNav() {
        this.mobileNavContainer.classList.add('show');
        this.mobileNavToggle.setAttribute('aria-expanded', 'true');

        // Prevent body scroll when mobile nav is open
        document.body.style.overflow = 'hidden';

        // Focus on first navigation link
        const firstNavLink = this.mobileNavContainer.querySelector('.mobile-nav-link');
        if (firstNavLink) {
            setTimeout(() => firstNavLink.focus(), 100);
        }
    }

    closeMobileNav() {
        this.mobileNavContainer.classList.remove('show');
        this.mobileNavToggle.setAttribute('aria-expanded', 'false');

        // Restore body scroll
        document.body.style.overflow = '';

        // Return focus to toggle button
        this.mobileNavToggle.focus();
    }

    handleMobileTabClick(tabId, mobileLink) {
        // Update mobile navigation active state
        this.mobileNavContainer.querySelectorAll('.mobile-nav-link').forEach(link => {
            link.classList.remove('active');
            link.setAttribute('aria-selected', 'false');
        });

        mobileLink.classList.add('active');
        mobileLink.setAttribute('aria-selected', 'true');

        this.currentActiveTab = tabId;

        // Close mobile navigation
        this.closeMobileNav();

        // Activate the desktop tab
        this.activateDesktopTab(tabId);
    }

    activateDesktopTab(tabId) {
        // Find and click the corresponding desktop tab
        const desktopTab = document.querySelector(`.nav-tabs .nav-link[aria-controls="${tabId}"]`);
        if (desktopTab) {
            desktopTab.click();
        } else {
            // Fallback: find by text content
            const mobileLink = document.querySelector(`.mobile-nav-link[data-tab-id="${tabId}"]`);
            if (mobileLink) {
                const labelText = mobileLink.textContent.trim();
                const allDesktopTabs = document.querySelectorAll('.nav-tabs .nav-link');

                allDesktopTabs.forEach(tab => {
                    if (tab.textContent.trim() === labelText) {
                        tab.click();
                    }
                });
            }
        }
    }

    initializeFromCurrentState() {
        // Set initial active tab based on current desktop state
        const activeDesktopTab = document.querySelector('.nav-tabs .nav-link.active');
        if (activeDesktopTab) {
            const tabId = activeDesktopTab.getAttribute('aria-controls') || activeDesktopTab.id;
            if (tabId) {
                this.currentActiveTab = tabId;

                // Update mobile navigation to match
                const mobileLink = this.mobileNavContainer.querySelector(`[data-tab-id="${tabId}"]`);
                if (mobileLink) {
                    mobileLink.classList.add('active');
                    mobileLink.setAttribute('aria-selected', 'true');
                }
            }
        }
    }

    handleResize() {
        const wasMobile = this.isMobile;
        this.isMobile = window.innerWidth <= 768;

        // Handle mobile/desktop transition
        if (wasMobile !== this.isMobile) {
            this.mobileNavToggle.style.display = this.isMobile ? 'block' : 'none';

            // Close mobile nav when switching to desktop
            if (!this.isMobile && this.mobileNavContainer.classList.contains('show')) {
                this.closeMobileNav();
            }
        }
    }

    // Utility function for debouncing resize events
    debounce(func, wait) {
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

    // Public methods for external use
    getCurrentTab() {
        return this.currentActiveTab;
    }

    isNavigationOpen() {
        return this.mobileNavContainer.classList.contains('show');
    }
}

// Initialize mobile navigation when DOM is ready
let mobileNavigation;

// Auto-initialize
(function() {
    if (typeof window !== 'undefined') {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                mobileNavigation = new MobileNavigation();
                window.mobileNavigation = mobileNavigation; // Expose globally
            });
        } else {
            mobileNavigation = new MobileNavigation();
            window.mobileNavigation = mobileNavigation; // Expose globally
        }
    }
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobileNavigation;
}