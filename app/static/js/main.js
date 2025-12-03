// GameStore Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Update cart count on page load
    updateCartCount();
    
    // Cart management
    initializeCart();
    
    // Form validation enhancements
    enhanceForms();
    
    // Image loading handling
    handleImageLoading();
});

// Update cart count from session
function updateCartCount() {
    const cartCountElements = document.querySelectorAll('#cartCount, .cart-count');
    cartCountElements.forEach(element => {
        // The count is now managed by server-side session
        // This just ensures the display is consistent
        const currentCount = element.textContent;
        if (currentCount === '0' || !currentCount) {
            // If count is 0, check if we need to update from session
            // This is a fallback for when session might not be synced
            const cart = JSON.parse(localStorage.getItem('cart') || '[]');
            if (cart.length > 0) {
                element.textContent = cart.length;
            }
        }
    });
}

// Cart functionality
function initializeCart() {
    // Add to cart animation
    const addToCartButtons = document.querySelectorAll('a[href*="/add-to-cart/"]');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Add loading animation
            const originalHTML = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            this.classList.add('disabled');
            
            // The actual navigation will happen naturally
            // We'll update the count after a short delay to simulate sync
            setTimeout(() => {
                updateCartCount();
            }, 1000);
        });
    });

    // Buy now buttons
    const buyNowButtons = document.querySelectorAll('a[href*="/buy-now/"]');
    buyNowButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Add loading animation
            const originalHTML = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            this.classList.add('disabled');
        });
    });

    // Clear cart functionality
    const clearCartBtn = document.querySelector('#clearCart');
    if (clearCartBtn) {
        clearCartBtn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to clear your entire cart?')) {
                e.preventDefault();
                return;
            }
            
            // Clear local storage
            localStorage.removeItem('cart');
            
            // Show notification
            showNotification('Cart cleared successfully!', 'success');
            
            // Update count
            updateCartCount();
        });
    }
}

// Form enhancements
function enhanceForms() {
    // Real-time form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                if (this.classList.contains('is-invalid')) {
                    validateField(this);
                }
            });
        });
    });

    // File input preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                // Validate file size (5MB max)
                if (file.size > 5 * 1024 * 1024) {
                    showNotification('File size must be less than 5MB', 'error');
                    this.value = '';
                    return;
                }

                // Validate file type
                const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'];
                if (!validTypes.includes(file.type)) {
                    showNotification('Please select a valid image or PDF file', 'error');
                    this.value = '';
                    return;
                }

                // Show preview for images
                if (file.type.startsWith('image/')) {
                    showImagePreview(this, file);
                }
            }
        });
    });
}

// Field validation
function validateField(field) {
    const value = field.value.trim();
    const fieldName = field.name;
    
    // Clear previous validation
    field.classList.remove('is-invalid', 'is-valid');
    
    // Remove existing feedback
    const existingFeedback = field.parentNode.querySelector('.invalid-feedback, .valid-feedback');
    if (existingFeedback) {
        existingFeedback.remove();
    }

    let isValid = true;
    let message = '';

    switch (fieldName) {
        case 'email':
            if (!value) {
                isValid = false;
                message = 'Email is required';
            } else if (!isValidEmail(value)) {
                isValid = false;
                message = 'Please enter a valid email address';
            }
            break;
            
        case 'password':
            if (!value) {
                isValid = false;
                message = 'Password is required';
            } else if (value.length < 6) {
                isValid = false;
                message = 'Password must be at least 6 characters';
            }
            break;
            
        case 'price':
            if (!value || parseFloat(value) < 0) {
                isValid = false;
                message = 'Please enter a valid price';
            }
            break;
            
        case 'title':
        case 'username':
            if (!value) {
                isValid = false;
                message = 'This field is required';
            }
            break;
    }

    if (!isValid) {
        field.classList.add('is-invalid');
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        field.parentNode.appendChild(feedback);
    } else {
        field.classList.add('is-valid');
    }
    
    return isValid;
}

// Email validation
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Image preview
function showImagePreview(input, file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        // Remove existing preview
        const existingPreview = input.parentNode.querySelector('.image-preview');
        if (existingPreview) {
            existingPreview.remove();
        }

        // Create preview
        const preview = document.createElement('div');
        preview.className = 'image-preview mt-2';
        preview.innerHTML = `
            <img src="${e.target.result}" class="img-thumbnail" style="max-height: 150px;" alt="Preview">
            <small class="text-muted d-block mt-1">Preview</small>
        `;
        input.parentNode.appendChild(preview);
    };
    reader.readAsDataURL(file);
}

// Image loading handling
function handleImageLoading() {
    const images = document.querySelectorAll('img');
    
    images.forEach(img => {
        // Add loading state
        img.addEventListener('load', function() {
            this.classList.add('loaded');
        });
        
        // Handle errors
        img.addEventListener('error', function() {
            this.src = 'https://res.cloudinary.com/dzfkklsza/image/upload/v1700000000/default-game.jpg';
            this.alt = 'Image not available';
        });
    });
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.custom-notification');
    existingNotifications.forEach(notification => {
        notification.remove();
    });

    // Create notification
    const notification = document.createElement('div');
    notification.className = `custom-notification alert alert-${type} alert-dismissible fade show`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Price formatting
function formatPrice(price) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(price);
}

// Category card animations
document.addEventListener('DOMContentLoaded', function() {
    const categoryCards = document.querySelectorAll('.category-card');
    categoryCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});

// Export functions for global use
window.GameStore = {
    showNotification,
    formatPrice,
    validateField,
    updateCartCount
};