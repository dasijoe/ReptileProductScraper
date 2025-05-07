/**
 * Chart initialization and configuration for Reptile Products Scraper
 */

/**
 * Initialize dashboard charts
 */
function initDashboardCharts() {
    // Set chart defaults
    Chart.defaults.color = '#cccccc';
    Chart.defaults.font.family = "'Helvetica Neue', 'Helvetica', 'Arial', sans-serif";
    
    // Create color palette
    const chartColors = {
        primary: 'rgb(54, 162, 235)',
        success: 'rgb(75, 192, 192)',
        danger: 'rgb(255, 99, 132)',
        warning: 'rgb(255, 205, 86)',
        info: 'rgb(153, 102, 255)',
        secondary: 'rgb(201, 203, 207)',
        primaryTransparent: 'rgba(54, 162, 235, 0.6)',
        successTransparent: 'rgba(75, 192, 192, 0.6)',
        dangerTransparent: 'rgba(255, 99, 132, 0.6)',
        warningTransparent: 'rgba(255, 205, 86, 0.6)',
        infoTransparent: 'rgba(153, 102, 255, 0.6)',
        secondaryTransparent: 'rgba(201, 203, 207, 0.6)'
    };
    
    // Reusable chart config
    const chartConfig = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    padding: 20,
                    boxWidth: 12
                }
            },
            tooltip: {
                backgroundColor: 'rgba(33, 37, 41, 0.9)',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                bodySpacing: 4,
                padding: 12,
                boxPadding: 8,
                usePointStyle: true
            }
        }
    };
    
    // Initialize products by category chart
    const categoryChart = document.getElementById('categoryChart');
    if (categoryChart) {
        // Data and options are set in the dashboard.html template's extra_js block
        // This is just to configure shared properties
        const categoryChartInstance = new Chart(categoryChart.getContext('2d'), {
            type: 'doughnut',
            options: {
                ...chartConfig,
                cutout: '70%',
                plugins: {
                    ...chartConfig.plugins,
                    legend: {
                        ...chartConfig.plugins.legend,
                        position: 'right'
                    }
                }
            }
            // data is provided in the dashboard template
        });
    }
    
    // Initialize scraping activity chart if present
    const scrapingChart = document.getElementById('scrapingActivityChart');
    if (scrapingChart) {
        // Example data - this would be populated from the backend
        const scrapingChartInstance = new Chart(scrapingChart.getContext('2d'), {
            type: 'bar',
            options: {
                ...chartConfig,
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
            // data is provided where the chart is used
        });
    }
    
    // Initialize price distribution chart if present
    const priceChart = document.getElementById('priceDistributionChart');
    if (priceChart) {
        // Example data - this would be populated from the backend
        const priceChartInstance = new Chart(priceChart.getContext('2d'), {
            type: 'line',
            options: {
                ...chartConfig,
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
            // data is provided where the chart is used
        });
    }
}

/**
 * Create a simple bar chart
 */
function createBarChart(elementId, labels, data, colors = []) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return null;
    
    // Use default colors if none provided
    if (!colors || !colors.length) {
        colors = [
            'rgba(54, 162, 235, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(255, 99, 132, 0.6)',
            'rgba(255, 205, 86, 0.6)',
            'rgba(153, 102, 255, 0.6)',
            'rgba(201, 203, 207, 0.6)'
        ];
    }
    
    // Create chart
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Count',
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.6', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Create a doughnut chart
 */
function createDoughnutChart(elementId, labels, data, colors = []) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return null;
    
    // Use default colors if none provided
    if (!colors || !colors.length) {
        colors = [
            'rgba(54, 162, 235, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(255, 99, 132, 0.6)',
            'rgba(255, 205, 86, 0.6)',
            'rgba(153, 102, 255, 0.6)',
            'rgba(201, 203, 207, 0.6)'
        ];
    }
    
    // Create chart
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.6', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                }
            },
            cutout: '70%'
        }
    });
}

// Initialize charts when document is ready
document.addEventListener('DOMContentLoaded', function() {
    initDashboardCharts();
});
