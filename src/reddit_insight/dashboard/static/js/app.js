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
    });

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

    // Expose utility functions globally for use in templates
    window.RedditInsight = {
        showNotification: showNotification
    };

})();
