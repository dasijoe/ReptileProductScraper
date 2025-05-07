/**
 * Main JavaScript for Reptile Products Scraper Application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', function() {
            document.querySelector('.wrapper').classList.toggle('sidebar-collapsed');
        });
    }
    
    // Enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto close alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var alertInstance = bootstrap.Alert.getInstance(alert);
            if (alertInstance) {
                alertInstance.close();
            } else {
                alert.classList.remove('show');
                setTimeout(function() {
                    alert.remove();
                }, 150);
            }
        });
    }, 5000);
    
    // Image error handling - replace broken images with placeholder
    document.querySelectorAll('img.product-img').forEach(function(img) {
        img.addEventListener('error', function() {
            this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZWVlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIGZpbGw9IiM5OTk5OTkiPk5vIEltYWdlPC90ZXh0Pjwvc3ZnPg==';
            this.classList.add('img-placeholder');
        });
    });

    // Website status updates
    function updateWebsiteStatus() {
        const statusElement = document.getElementById('website-status-container');
        if (statusElement) {
            fetch('/api/website-status')
                .then(response => response.json())
                .then(data => {
                    // Update status indicators
                    data.forEach(website => {
                        const statusBadge = document.querySelector(`.website-status-${website.id}`);
                        if (statusBadge) {
                            // Remove all status classes
                            statusBadge.classList.remove('bg-success', 'bg-danger', 'bg-primary', 'bg-secondary');
                            
                            // Set appropriate class based on status
                            if (website.status === 'completed') {
                                statusBadge.classList.add('bg-success');
                                statusBadge.textContent = 'Completed';
                            } else if (website.status === 'scraping') {
                                statusBadge.classList.add('bg-primary');
                                statusBadge.textContent = 'Scraping';
                            } else if (website.status === 'failed') {
                                statusBadge.classList.add('bg-danger');
                                statusBadge.textContent = 'Failed';
                            } else {
                                statusBadge.classList.add('bg-secondary');
                                statusBadge.textContent = website.status;
                            }
                        }
                    });
                })
                .catch(error => console.error('Error fetching website status:', error));
        }
    }

    // Update status periodically if on websites page
    if (document.querySelector('.website-status-container')) {
        updateWebsiteStatus();
        setInterval(updateWebsiteStatus, 10000); // Update every 10 seconds
    }
    
    // Handle form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

/**
 * Format a number as currency
 */
function formatCurrency(value, currency = 'ZAR') {
    if (value === null || value === undefined || isNaN(value)) {
        return '';
    }
    
    const formatter = new Intl.NumberFormat('en-ZA', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2
    });
    
    return formatter.format(value);
}

/**
 * Format a date string
 */
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    
    return new Intl.DateTimeFormat('en-ZA', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}
