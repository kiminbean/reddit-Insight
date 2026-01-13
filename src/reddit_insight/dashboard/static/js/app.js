/**
 * Reddit Insight Dashboard - Application JavaScript
 *
 * Enhanced with mobile sidebar, dark mode, loading states, and toast notifications.
 * Most interactivity is handled by HTMX.
 */

(function() {
    'use strict';

    /**
     * Initialize the application on DOM ready
     */
    document.addEventListener('DOMContentLoaded', function() {
        initMobileSidebar();
        initThemeToggle();
        initHTMXHandlers();
        initChartDefaults();
        initTabNavigation();
        initRangeInputs();
        initEventDelegation();
        initKeyboardNavigation();
    });

    /**
     * Mobile sidebar with slide animation
     */
    function initMobileSidebar() {
        var menuBtn = document.getElementById('mobile-menu-btn');
        var closeBtn = document.getElementById('mobile-menu-close');
        var sidebar = document.getElementById('mobile-sidebar');
        var overlay = document.getElementById('mobile-menu-overlay');

        if (!menuBtn || !sidebar || !overlay) return;

        function openSidebar() {
            sidebar.classList.remove('-translate-x-full');
            overlay.classList.remove('hidden');
            // Trigger reflow for animation
            overlay.offsetHeight;
            overlay.classList.remove('opacity-0');
            overlay.classList.add('opacity-100');
            document.body.style.overflow = 'hidden';
            menuBtn.setAttribute('aria-expanded', 'true');
            // Focus first link in sidebar for accessibility
            var firstLink = sidebar.querySelector('a');
            if (firstLink) firstLink.focus();
        }

        function closeSidebar() {
            sidebar.classList.add('-translate-x-full');
            overlay.classList.remove('opacity-100');
            overlay.classList.add('opacity-0');
            setTimeout(function() {
                overlay.classList.add('hidden');
            }, 300);
            document.body.style.overflow = '';
            menuBtn.setAttribute('aria-expanded', 'false');
            menuBtn.focus();
        }

        menuBtn.addEventListener('click', openSidebar);
        if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
        overlay.addEventListener('click', closeSidebar);

        // Close on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && !sidebar.classList.contains('-translate-x-full')) {
                closeSidebar();
            }
        });

        // Close sidebar on resize to desktop
        window.addEventListener('resize', function() {
            if (window.innerWidth >= 640 && !sidebar.classList.contains('-translate-x-full')) {
                closeSidebar();
            }
        });
    }

    /**
     * Dark mode toggle with localStorage persistence
     */
    function initThemeToggle() {
        var themeToggle = document.getElementById('theme-toggle');
        var mobileThemeToggle = document.getElementById('mobile-theme-toggle');

        function toggleTheme() {
            var isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');

            // Update chart colors if charts exist
            updateChartTheme(isDark);
        }

        if (themeToggle) {
            themeToggle.addEventListener('click', toggleTheme);
        }
        if (mobileThemeToggle) {
            mobileThemeToggle.addEventListener('click', toggleTheme);
        }

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            if (!localStorage.getItem('theme')) {
                if (e.matches) {
                    document.documentElement.classList.add('dark');
                } else {
                    document.documentElement.classList.remove('dark');
                }
                updateChartTheme(e.matches);
            }
        });
    }

    /**
     * Update Chart.js theme colors
     */
    function updateChartTheme(isDark) {
        if (typeof Chart === 'undefined') return;

        var textColor = isDark ? '#e5e7eb' : '#6b7280';
        var gridColor = isDark ? '#374151' : '#e5e7eb';

        Chart.defaults.color = textColor;
        Chart.defaults.borderColor = gridColor;

        // Update existing charts
        Chart.helpers.each(Chart.instances, function(chart) {
            if (chart.options.scales) {
                Object.keys(chart.options.scales).forEach(function(scaleKey) {
                    if (chart.options.scales[scaleKey].grid) {
                        chart.options.scales[scaleKey].grid.color = gridColor;
                    }
                    if (chart.options.scales[scaleKey].ticks) {
                        chart.options.scales[scaleKey].ticks.color = textColor;
                    }
                });
            }
            chart.update('none');
        });
    }

    /**
     * Tab navigation with keyboard support
     */
    function initTabNavigation() {
        var tabContainers = document.querySelectorAll('[data-tab-container]');

        tabContainers.forEach(function(container) {
            var tabs = container.querySelectorAll('[data-tab]');
            var panels = container.parentElement.querySelectorAll('[data-tab-panel]');

            tabs.forEach(function(tab) {
                tab.addEventListener('click', function() {
                    var targetTab = this.getAttribute('data-tab');
                    activateTab(tabs, panels, targetTab);
                });

                // Keyboard navigation
                tab.addEventListener('keydown', function(e) {
                    var tabArray = Array.from(tabs);
                    var currentIndex = tabArray.indexOf(this);

                    if (e.key === 'ArrowRight') {
                        e.preventDefault();
                        var nextIndex = (currentIndex + 1) % tabArray.length;
                        tabArray[nextIndex].focus();
                        tabArray[nextIndex].click();
                    } else if (e.key === 'ArrowLeft') {
                        e.preventDefault();
                        var prevIndex = (currentIndex - 1 + tabArray.length) % tabArray.length;
                        tabArray[prevIndex].focus();
                        tabArray[prevIndex].click();
                    }
                });
            });
        });
    }

    function activateTab(tabs, panels, targetTab) {
        tabs.forEach(function(t) {
            var isActive = t.getAttribute('data-tab') === targetTab;
            t.setAttribute('aria-selected', isActive ? 'true' : 'false');
            t.setAttribute('tabindex', isActive ? '0' : '-1');
            t.classList.toggle('text-blue-600', isActive);
            t.classList.toggle('dark:text-blue-400', isActive);
            t.classList.toggle('border-blue-600', isActive);
            t.classList.toggle('dark:border-blue-400', isActive);
            t.classList.toggle('text-gray-500', !isActive);
            t.classList.toggle('dark:text-gray-400', !isActive);
            t.classList.toggle('border-transparent', !isActive);
        });

        panels.forEach(function(p) {
            var isActive = p.getAttribute('data-tab-panel') === targetTab;
            p.classList.toggle('hidden', !isActive);
        });
    }

    /**
     * Range input value display
     */
    function initRangeInputs() {
        var rangeInputs = document.querySelectorAll('input[type="range"][data-value-display]');

        rangeInputs.forEach(function(input) {
            var displayId = input.getAttribute('data-value-display');
            var display = document.getElementById(displayId);

            if (display) {
                input.addEventListener('input', function() {
                    display.textContent = this.value;
                });
            }
        });
    }

    /**
     * Event delegation for dynamically loaded content
     */
    function initEventDelegation() {
        // Handle suggestion clicks for search
        document.addEventListener('click', function(e) {
            var suggestionItem = e.target.closest('[data-suggestion]');
            if (suggestionItem) {
                var query = suggestionItem.getAttribute('data-suggestion');
                var searchInput = document.getElementById('search-input');
                if (searchInput && query) {
                    searchInput.value = query;
                    var suggestionsDropdown = document.getElementById('suggestions-dropdown');
                    if (suggestionsDropdown) {
                        suggestionsDropdown.innerHTML = '';
                    }
                }
            }
        });
    }

    /**
     * Global keyboard navigation for accessibility
     */
    function initKeyboardNavigation() {
        // Skip link functionality
        var skipLink = document.querySelector('[data-skip-link]');
        if (skipLink) {
            skipLink.addEventListener('click', function(e) {
                e.preventDefault();
                var target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.setAttribute('tabindex', '-1');
                    target.focus();
                }
            });
        }

        // Focus trap for modals
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                var modal = document.querySelector('[role="dialog"]:not(.hidden)');
                if (modal) {
                    var focusableElements = modal.querySelectorAll(
                        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
                    );
                    var firstElement = focusableElements[0];
                    var lastElement = focusableElements[focusableElements.length - 1];

                    if (e.shiftKey && document.activeElement === firstElement) {
                        e.preventDefault();
                        lastElement.focus();
                    } else if (!e.shiftKey && document.activeElement === lastElement) {
                        e.preventDefault();
                        firstElement.focus();
                    }
                }
            }
        });
    }

    /**
     * HTMX Event Handlers with loading states
     */
    function initHTMXHandlers() {
        // Handle HTMX before request - show loading state
        document.body.addEventListener('htmx:beforeRequest', function(event) {
            var target = event.detail.target;
            if (target) {
                target.classList.add('htmx-request');
                // Show loading indicator if exists
                var indicator = target.querySelector('.loading-indicator');
                if (indicator) {
                    indicator.classList.remove('hidden');
                }
            }
        });

        // Handle HTMX after request - hide loading state
        document.body.addEventListener('htmx:afterRequest', function(event) {
            var target = event.detail.target;
            if (target) {
                target.classList.remove('htmx-request');
                // Hide loading indicator if exists
                var indicator = target.querySelector('.loading-indicator');
                if (indicator) {
                    indicator.classList.add('hidden');
                }
            }
        });

        // Handle HTMX errors
        document.body.addEventListener('htmx:responseError', function(event) {
            console.error('HTMX Error:', event.detail.error);
            var statusCode = event.detail.xhr ? event.detail.xhr.status : 'Unknown';
            var message = statusCode === 404
                ? 'The requested resource was not found.'
                : statusCode === 500
                    ? 'A server error occurred. Please try again later.'
                    : 'An error occurred. Please try again.';
            showNotification(message, 'error');
        });

        // Handle HTMX send error (network issues)
        document.body.addEventListener('htmx:sendError', function(event) {
            console.error('HTMX Send Error:', event.detail);
            showNotification('Network error. Please check your connection and try again.', 'error');
        });

        // Handle successful form submissions
        document.body.addEventListener('htmx:afterOnLoad', function(event) {
            // Check for success message in response headers
            var xhr = event.detail.xhr;
            if (xhr) {
                var successMessage = xhr.getResponseHeader('X-Success-Message');
                if (successMessage) {
                    showNotification(successMessage, 'success');
                }
            }
        });
    }

    /**
     * Initialize Chart.js default settings
     */
    function initChartDefaults() {
        if (typeof Chart === 'undefined') return;

        var isDark = document.documentElement.classList.contains('dark');
        var textColor = isDark ? '#e5e7eb' : '#6b7280';
        var gridColor = isDark ? '#374151' : '#e5e7eb';

        Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
        Chart.defaults.color = textColor;
        Chart.defaults.borderColor = gridColor;
        Chart.defaults.plugins.legend.position = 'bottom';
        Chart.defaults.plugins.tooltip.backgroundColor = isDark ? '#1f2937' : '#111827';
        Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
        Chart.defaults.plugins.tooltip.bodyColor = '#ffffff';
        Chart.defaults.plugins.tooltip.cornerRadius = 6;
        Chart.defaults.plugins.tooltip.padding = 12;

        // Responsive defaults
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - The notification type (success, error, warning, info)
     * @param {number} duration - Duration in milliseconds (default: 5000)
     */
    function showNotification(message, type, duration) {
        type = type || 'info';
        duration = duration || 5000;

        var container = document.getElementById('toast-container');
        if (!container) {
            // Fallback: create container if not exists
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'fixed bottom-4 right-4 z-50 space-y-2';
            container.setAttribute('aria-live', 'polite');
            container.setAttribute('aria-atomic', 'true');
            document.body.appendChild(container);
        }

        var toast = document.createElement('div');
        toast.className = 'flex items-center p-4 rounded-lg shadow-lg transform transition-all duration-300 ease-in-out translate-x-full opacity-0 max-w-sm';
        toast.setAttribute('role', 'alert');

        var icons = {
            success: '<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
            error: '<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
            warning: '<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>',
            info: '<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>'
        };

        var colors = {
            success: 'bg-green-500 text-white',
            error: 'bg-red-500 text-white',
            warning: 'bg-yellow-500 text-white',
            info: 'bg-blue-500 text-white'
        };

        toast.className += ' ' + (colors[type] || colors.info);
        toast.innerHTML =
            '<span class="mr-2">' + (icons[type] || icons.info) + '</span>' +
            '<span class="flex-1 text-sm font-medium">' + escapeHtml(message) + '</span>' +
            '<button type="button" class="ml-3 -mr-1 p-1 rounded hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white" aria-label="Dismiss">' +
                '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>' +
            '</button>';

        container.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(function() {
            toast.classList.remove('translate-x-full', 'opacity-0');
        });

        // Close button handler
        var closeBtn = toast.querySelector('button');
        function removeToast() {
            toast.classList.add('translate-x-full', 'opacity-0');
            setTimeout(function() {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }

        closeBtn.addEventListener('click', removeToast);

        // Auto-remove after duration
        setTimeout(removeToast, duration);
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Fetch chart data with error handling
     * @param {string} url - API endpoint URL
     * @returns {Promise<Object>} - Chart data or null on error
     */
    async function fetchChartData(url) {
        try {
            var response = await fetch(url);
            if (!response.ok) {
                throw new Error('HTTP ' + response.status + ': ' + response.statusText);
            }
            return await response.json();
        } catch (error) {
            console.error('Chart data fetch error:', error);
            showNotification('Failed to load chart data. Please try again.', 'error');
            return null;
        }
    }

    /**
     * Initialize a Chart.js chart with error handling
     * @param {string} canvasId - Canvas element ID
     * @param {string} dataUrl - API endpoint URL for chart data
     * @param {string} chartType - Chart type (line, bar, pie, etc.)
     * @param {Object} options - Additional chart options
     * @returns {Promise<Chart|null>} - Chart instance or null on error
     */
    async function initChart(canvasId, dataUrl, chartType, options) {
        var canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn('Canvas element not found:', canvasId);
            return null;
        }

        var ctx = canvas.getContext('2d');
        if (!ctx) {
            console.error('Could not get 2D context for canvas:', canvasId);
            return null;
        }

        var data = await fetchChartData(dataUrl);
        if (!data) {
            return null;
        }

        try {
            return new Chart(ctx, {
                type: chartType || 'line',
                data: data,
                options: options || {}
            });
        } catch (error) {
            console.error('Chart initialization error:', error);
            showNotification('Failed to initialize chart.', 'error');
            return null;
        }
    }

    // Expose utility functions globally for use in templates
    window.RedditInsight = {
        showNotification: showNotification,
        fetchChartData: fetchChartData,
        initChart: initChart,
        updateChartTheme: updateChartTheme
    };

})();
