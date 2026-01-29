/**
 * Plan Limits JavaScript
 * Provides AJAX functionality for checking plan limits
 */

// Check plan limits before creating resources
function checkPlanLimit(resourceType, callback) {
    fetch(`/api/plan-usage/`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        const usage = data[resourceType];
        if (usage && usage.remaining <= 0) {
            showPlanLimitError(resourceType, usage.limit);
            return false;
        }
        if (callback) callback(true);
    })
    .catch(error => {
        console.error('Error checking plan limits:', error);
        if (callback) callback(true); // Allow creation if check fails
    });
}

// Show plan limit error message
function showPlanLimitError(resourceType, limit) {
    const message = `Plan limit exceeded. You can only create ${limit} ${resourceType}s with your current plan.`;
    
    // Show SweetAlert if available, otherwise use alert
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: 'Plan Limit Exceeded',
            text: message,
            icon: 'warning',
            confirmButtonText: 'OK'
        });
    } else {
        alert(message);
    }
}

// Add plan limit checking to forms
document.addEventListener('DOMContentLoaded', function() {
    // Check warehouse creation
    const warehouseForm = document.querySelector('form[action*="warehouse"]');
    if (warehouseForm) {
        warehouseForm.addEventListener('submit', function(e) {
            checkPlanLimit('warehouse', function(canCreate) {
                if (!canCreate) {
                    e.preventDefault();
                }
            });
        });
    }

    // Check farmer creation
    const farmerForm = document.querySelector('form[action*="farmer"]');
    if (farmerForm) {
        farmerForm.addEventListener('submit', function(e) {
            checkPlanLimit('farmer', function(canCreate) {
                if (!canCreate) {
                    e.preventDefault();
                }
            });
        });
    }

    // Check client creation
    const clientForm = document.querySelector('form[action*="client"]');
    if (clientForm) {
        clientForm.addEventListener('submit', function(e) {
            checkPlanLimit('client', function(canCreate) {
                if (!canCreate) {
                    e.preventDefault();
                }
            });
        });
    }

    // Check user creation
    const userForm = document.querySelector('form[action*="user"]');
    if (userForm) {
        userForm.addEventListener('submit', function(e) {
            checkPlanLimit('user', function(canCreate) {
                if (!canCreate) {
                    e.preventDefault();
                }
            });
        });
    }
});

// Update plan usage display
function updatePlanUsage() {
    fetch(`/api/plan-usage/`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        // Update usage numbers in the UI
        Object.keys(data).forEach(resourceType => {
            const usage = data[resourceType];
            const currentElement = document.querySelector(`[data-resource="${resourceType}"] .current-count`);
            const limitElement = document.querySelector(`[data-resource="${resourceType}"] .limit-count`);
            const remainingElement = document.querySelector(`[data-resource="${resourceType}"] .remaining-count`);
            
            if (currentElement) currentElement.textContent = usage.current;
            if (limitElement) limitElement.textContent = usage.limit;
            if (remainingElement) remainingElement.textContent = usage.remaining;
            
            // Update progress bar
            const progressBar = document.querySelector(`[data-resource="${resourceType}"] .progress-bar`);
            if (progressBar) {
                const percentage = (usage.current / usage.limit) * 100;
                progressBar.style.width = percentage + '%';
                progressBar.setAttribute('aria-valuenow', usage.current);
            }
        });
    })
    .catch(error => {
        console.error('Error updating plan usage:', error);
    });
}

// Auto-update plan usage every 30 seconds
setInterval(updatePlanUsage, 30000);
