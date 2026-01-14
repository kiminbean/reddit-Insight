/**
 * Reddit Insight Dashboard - Chart Utilities
 *
 * Color-blind friendly chart configurations and helper functions.
 * Uses ColorBrewer palettes optimized for accessibility.
 */

(function() {
    'use strict';

    /**
     * Color-blind friendly color palettes (ColorBrewer)
     * These palettes are designed to be distinguishable by people with
     * various forms of color blindness (protanopia, deuteranopia, tritanopia).
     */
    const ColorPalettes = {
        // Qualitative palette - for categorical data (8 colors, colorblind safe)
        categorical: [
            '#1f77b4',  // Blue
            '#ff7f0e',  // Orange
            '#2ca02c',  // Green
            '#d62728',  // Red
            '#9467bd',  // Purple
            '#8c564b',  // Brown
            '#e377c2',  // Pink
            '#7f7f7f'   // Gray
        ],

        // Alternative categorical palette (Tableau 10, also colorblind friendly)
        tableau10: [
            '#4e79a7',  // Steel Blue
            '#f28e2b',  // Orange
            '#e15759',  // Red
            '#76b7b2',  // Teal
            '#59a14f',  // Green
            '#edc948',  // Yellow
            '#b07aa1',  // Purple
            '#ff9da7',  // Pink
            '#9c755f',  // Brown
            '#bab0ac'   // Gray
        ],

        // Sequential palette - for ordered data (single hue blue)
        sequential: [
            '#08306b',
            '#08519c',
            '#2171b5',
            '#4292c6',
            '#6baed6',
            '#9ecae1',
            '#c6dbef',
            '#deebf7'
        ],

        // Diverging palette - for data with meaningful midpoint
        diverging: [
            '#b2182b',  // Dark red
            '#d6604d',
            '#f4a582',
            '#fddbc7',
            '#f7f7f7',  // Neutral
            '#d1e5f0',
            '#92c5de',
            '#4393c3',
            '#2166ac'   // Dark blue
        ],

        // Sentiment colors (high contrast)
        sentiment: {
            positive: '#2ca02c',      // Green
            negative: '#d62728',      // Red
            neutral: '#7f7f7f',       // Gray
            positiveLight: '#98df8a', // Light green (for fills)
            negativeLight: '#ff9896', // Light red (for fills)
            neutralLight: '#c7c7c7'   // Light gray (for fills)
        },

        // Status colors (traffic light, optimized)
        status: {
            success: '#2ca02c',
            warning: '#ff7f0e',
            error: '#d62728',
            info: '#1f77b4'
        },

        // Dark mode variants
        dark: {
            categorical: [
                '#6baed6',  // Light blue
                '#fdae6b',  // Light orange
                '#74c476',  // Light green
                '#fc9272',  // Light red
                '#bcbddc',  // Light purple
                '#d9d9d9',  // Light gray
                '#f7b6d2',  // Light pink
                '#c49c94'   // Light brown
            ],
            text: '#e5e7eb',
            grid: '#374151',
            background: '#1f2937'
        }
    };

    /**
     * Get color palette based on data type and mode
     */
    function getColorPalette(type, isDarkMode) {
        if (isDarkMode && type === 'categorical') {
            return ColorPalettes.dark.categorical;
        }
        return ColorPalettes[type] || ColorPalettes.categorical;
    }

    /**
     * Generate dataset colors with proper transparency
     */
    function generateDatasetColors(count, options = {}) {
        const {
            palette = 'categorical',
            isDarkMode = document.documentElement.classList.contains('dark'),
            backgroundAlpha = 0.6,
            borderAlpha = 1
        } = options;

        const colors = getColorPalette(palette, isDarkMode);
        const result = {
            backgroundColor: [],
            borderColor: []
        };

        for (let i = 0; i < count; i++) {
            const colorIndex = i % colors.length;
            const color = colors[colorIndex];

            // Parse hex color to RGB
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);

            result.backgroundColor.push(`rgba(${r}, ${g}, ${b}, ${backgroundAlpha})`);
            result.borderColor.push(`rgba(${r}, ${g}, ${b}, ${borderAlpha})`);
        }

        return result;
    }

    /**
     * Enhanced Chart.js default configuration
     */
    function getChartDefaults(isDarkMode) {
        const textColor = isDarkMode ? '#e5e7eb' : '#374151';
        const gridColor = isDarkMode ? '#374151' : '#e5e7eb';
        const tooltipBg = isDarkMode ? '#1f2937' : '#111827';

        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: textColor,
                        padding: 16,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        font: {
                            family: "'Inter', 'system-ui', sans-serif",
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: tooltipBg,
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: isDarkMode ? '#4b5563' : '#374151',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    titleFont: {
                        family: "'Inter', 'system-ui', sans-serif",
                        size: 13,
                        weight: 'bold'
                    },
                    bodyFont: {
                        family: "'Inter', 'system-ui', sans-serif",
                        size: 12
                    },
                    displayColors: true,
                    boxPadding: 6,
                    // Multi-line tooltip support
                    callbacks: {
                        title: function(tooltipItems) {
                            return tooltipItems[0].label || '';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: textColor,
                        font: {
                            family: "'Inter', 'system-ui', sans-serif",
                            size: 11
                        }
                    },
                    title: {
                        color: textColor,
                        font: {
                            family: "'Inter', 'system-ui', sans-serif",
                            size: 12,
                            weight: 'bold'
                        }
                    }
                },
                y: {
                    grid: {
                        color: gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: textColor,
                        font: {
                            family: "'Inter', 'system-ui', sans-serif",
                            size: 11
                        }
                    },
                    title: {
                        color: textColor,
                        font: {
                            family: "'Inter', 'system-ui', sans-serif",
                            size: 12,
                            weight: 'bold'
                        }
                    }
                }
            },
            animation: {
                duration: 400,
                easing: 'easeOutQuart'
            },
            interaction: {
                mode: 'nearest',
                axis: 'xy',
                intersect: false
            }
        };
    }

    /**
     * Apply colorblind-friendly defaults to Chart.js
     */
    function applyChartDefaults() {
        if (typeof Chart === 'undefined') return;

        const isDarkMode = document.documentElement.classList.contains('dark');
        const defaults = getChartDefaults(isDarkMode);

        // Apply defaults
        Chart.defaults.font.family = "'Inter', 'system-ui', sans-serif";
        Chart.defaults.responsive = defaults.responsive;
        Chart.defaults.maintainAspectRatio = defaults.maintainAspectRatio;
        Chart.defaults.animation = defaults.animation;

        // Set default colors to colorblind-friendly palette
        Chart.defaults.backgroundColor = ColorPalettes.categorical;
        Chart.defaults.borderColor = ColorPalettes.categorical;

        // Plugin defaults
        Object.assign(Chart.defaults.plugins.legend, defaults.plugins.legend);
        Object.assign(Chart.defaults.plugins.tooltip, defaults.plugins.tooltip);
    }

    /**
     * Update all existing charts with new theme colors
     */
    function updateChartsTheme(isDarkMode) {
        if (typeof Chart === 'undefined') return;

        const textColor = isDarkMode ? '#e5e7eb' : '#374151';
        const gridColor = isDarkMode ? '#374151' : '#e5e7eb';

        Chart.helpers.each(Chart.instances, function(chart) {
            // Update scales
            if (chart.options.scales) {
                Object.keys(chart.options.scales).forEach(function(scaleKey) {
                    const scale = chart.options.scales[scaleKey];
                    if (scale.grid) {
                        scale.grid.color = gridColor;
                    }
                    if (scale.ticks) {
                        scale.ticks.color = textColor;
                    }
                    if (scale.title) {
                        scale.title.color = textColor;
                    }
                });
            }

            // Update legend
            if (chart.options.plugins && chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = textColor;
            }

            chart.update('none');
        });
    }

    /**
     * Create accessible chart with proper ARIA labels
     */
    function createAccessibleChart(canvas, config) {
        if (!canvas || typeof Chart === 'undefined') return null;

        // Add ARIA attributes to canvas
        canvas.setAttribute('role', 'img');

        if (config.options && config.options.plugins && config.options.plugins.title) {
            canvas.setAttribute('aria-label', config.options.plugins.title.text || 'Chart');
        } else {
            canvas.setAttribute('aria-label', 'Data visualization chart');
        }

        // Add screen reader description
        const descId = `chart-desc-${Date.now()}`;
        let description = document.createElement('div');
        description.id = descId;
        description.className = 'sr-only';
        description.textContent = generateChartDescription(config);
        canvas.parentNode.insertBefore(description, canvas.nextSibling);
        canvas.setAttribute('aria-describedby', descId);

        // Create chart with merged defaults
        const isDarkMode = document.documentElement.classList.contains('dark');
        const mergedConfig = mergeChartConfig(config, isDarkMode);

        return new Chart(canvas.getContext('2d'), mergedConfig);
    }

    /**
     * Generate text description of chart for screen readers
     */
    function generateChartDescription(config) {
        const type = config.type || 'chart';
        const datasets = config.data && config.data.datasets ? config.data.datasets.length : 0;
        const labels = config.data && config.data.labels ? config.data.labels.length : 0;

        let description = `This is a ${type} chart`;

        if (datasets > 0) {
            description += ` with ${datasets} dataset${datasets > 1 ? 's' : ''}`;
        }

        if (labels > 0) {
            description += ` showing ${labels} data point${labels > 1 ? 's' : ''}`;
        }

        // Add summary of data if available
        if (config.data && config.data.datasets && config.data.datasets[0]) {
            const firstDataset = config.data.datasets[0];
            if (firstDataset.data && firstDataset.data.length > 0) {
                const max = Math.max(...firstDataset.data.filter(d => typeof d === 'number'));
                const min = Math.min(...firstDataset.data.filter(d => typeof d === 'number'));
                description += `. Values range from ${min} to ${max}`;
            }
        }

        return description + '.';
    }

    /**
     * Merge user config with accessible defaults
     */
    function mergeChartConfig(config, isDarkMode) {
        const defaults = getChartDefaults(isDarkMode);

        // Generate colors for datasets if not provided
        if (config.data && config.data.datasets) {
            config.data.datasets.forEach((dataset, index) => {
                if (!dataset.backgroundColor) {
                    const colors = generateDatasetColors(1, { isDarkMode });
                    dataset.backgroundColor = colors.backgroundColor[0];
                    dataset.borderColor = colors.borderColor[0];
                }
            });
        }

        // Deep merge options
        const mergedOptions = {
            ...defaults,
            ...config.options,
            plugins: {
                ...defaults.plugins,
                ...(config.options && config.options.plugins)
            },
            scales: {
                ...defaults.scales,
                ...(config.options && config.options.scales)
            }
        };

        return {
            ...config,
            options: mergedOptions
        };
    }

    /**
     * Format number for display in charts
     */
    function formatChartNumber(value, options = {}) {
        const { compact = false, decimals = 0, prefix = '', suffix = '' } = options;

        if (value === null || value === undefined) return '';

        let formatted;
        if (compact && Math.abs(value) >= 1000) {
            if (Math.abs(value) >= 1000000) {
                formatted = (value / 1000000).toFixed(1) + 'M';
            } else if (Math.abs(value) >= 1000) {
                formatted = (value / 1000).toFixed(1) + 'K';
            }
        } else {
            formatted = value.toLocaleString(undefined, {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            });
        }

        return `${prefix}${formatted}${suffix}`;
    }

    /**
     * Create gradient for line charts
     */
    function createChartGradient(ctx, color, height = 200) {
        const gradient = ctx.createLinearGradient(0, 0, 0, height);

        // Parse hex color
        const r = parseInt(color.slice(1, 3), 16);
        const g = parseInt(color.slice(3, 5), 16);
        const b = parseInt(color.slice(5, 7), 16);

        gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.4)`);
        gradient.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.1)`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);

        return gradient;
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        applyChartDefaults();
    });

    // Listen for theme changes
    if (typeof window !== 'undefined') {
        // Observe class changes on document element for dark mode toggle
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'class') {
                    const isDarkMode = document.documentElement.classList.contains('dark');
                    updateChartsTheme(isDarkMode);
                }
            });
        });

        observer.observe(document.documentElement, { attributes: true });
    }

    // Expose utilities globally
    window.ChartUtils = {
        ColorPalettes: ColorPalettes,
        getColorPalette: getColorPalette,
        generateDatasetColors: generateDatasetColors,
        getChartDefaults: getChartDefaults,
        applyChartDefaults: applyChartDefaults,
        updateChartsTheme: updateChartsTheme,
        createAccessibleChart: createAccessibleChart,
        formatChartNumber: formatChartNumber,
        createChartGradient: createChartGradient
    };

})();
