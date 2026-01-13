/**
 * Reddit Insight Dashboard - Application JavaScript
 *
 * Minimal JavaScript for enhanced functionality.
 * Most interactivity is handled by HTMX.
 */

(function() {
    'use strict';

    /**
     * Initialize the application on DOM ready
     */
    document.addEventListener('DOMContentLoaded', function() {
        initHTMXHandlers();
        initChartDefaults();
        initMobileMenu();
        initTabNavigation();
        initRangeInputs();
        initEventDelegation();
    });

    /**
     * Mobile menu toggle
     */
    function initMobileMenu() {
        var menuBtn = document.getElementById('mobile-menu-btn');
        var mobileMenu = document.getElementById('mobile-menu');

        if (menuBtn && mobileMenu) {
            menuBtn.addEventListener('click', function() {
                mobileMenu.classList.toggle('hidden');
            });
        }
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
                        var nextIndex = (currentIndex + 1) % tabArray.length;
                        tabArray[nextIndex].focus();
                        tabArray[nextIndex].click();
                    } else if (e.key === 'ArrowLeft') {
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
            t.classList.toggle('text-blue-600', isActive);
            t.classList.toggle('border-blue-600', isActive);
            t.classList.toggle('text-gray-500', !isActive);
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
     * HTMX Event Handlers
     */
    function initHTMXHandlers() {
        // Handle HTMX before request - show loading state
        document.body.addEventListener('htmx:beforeRequest', function(event) {
            const target = event.detail.target;
            if (target) {
                target.classList.add('htmx-request');
            }
        });

        // Handle HTMX after request - hide loading state
        document.body.addEventListener('htmx:afterRequest', function(event) {
            const target = event.detail.target;
            if (target) {
                target.classList.remove('htmx-request');
            }
        });

        // Handle HTMX errors
        document.body.addEventListener('htmx:responseError', function(event) {
            console.error('HTMX Error:', event.detail.error);
            showNotification('An error occurred. Please try again.', 'error');
        });
    }

    /**
     * Initialize Chart.js default settings
     */
    function initChartDefaults() {
        if (typeof Chart !== 'undefined') {
            Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
            Chart.defaults.color = '#6b7280';
            Chart.defaults.plugins.legend.position = 'bottom';
            Chart.defaults.plugins.tooltip.backgroundColor = '#1f2937';
            Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
            Chart.defaults.plugins.tooltip.bodyColor = '#ffffff';
            Chart.defaults.plugins.tooltip.cornerRadius = 4;
            Chart.defaults.plugins.tooltip.padding = 10;
        }
    }

    /**
     * Show a notification message
     * @param {string} message - The message to display
     * @param {string} type - The notification type (success, error, warning, info)
     */
    function showNotification(message, type) {
        type = type || 'info';

        var notification = document.createElement('div');
        notification.className = 'fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 transition-opacity duration-300';

        var colors = {
            success: 'bg-green-500 text-white',
            error: 'bg-red-500 text-white',
            warning: 'bg-yellow-500 text-white',
            info: 'bg-blue-500 text-white'
        };

        notification.className += ' ' + (colors[type] || colors.info);
        notification.textContent = message;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(function() {
            notification.style.opacity = '0';
            setTimeout(function() {
                notification.remove();
            }, 300);
        }, 5000);
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
        initChart: initChart
    };

})();
