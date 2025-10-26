// SymbiHub App JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    // Dark Mode Toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    const darkModeIcon = document.getElementById('darkModeIcon');
    const html = document.documentElement;

    if (darkModeToggle && darkModeIcon) {
        // Check for saved theme preference or default to dark
        const currentTheme = localStorage.getItem('theme') || 'dark';
        if (currentTheme === 'dark') {
            html.classList.add('dark');
            darkModeIcon.className = 'ph ph-moon text-xl';
        } else {
            html.classList.remove('dark');
            darkModeIcon.className = 'ph ph-sun text-xl';
        }

        darkModeToggle.addEventListener('click', () => {
            if (html.classList.contains('dark')) {
                html.classList.remove('dark');
                darkModeIcon.className = 'ph ph-sun text-xl';
                localStorage.setItem('theme', 'light');
            } else {
                html.classList.add('dark');
                darkModeIcon.className = 'ph ph-moon text-xl';
                localStorage.setItem('theme', 'dark');
            }
        });
    }

    // Mobile Menu Toggle
    const mobileMenuButton = document.getElementById('mobileMenuButton');
    const mobileMenu = document.getElementById('mobileMenu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Tab functionality
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Remove active class from all buttons
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('border-blue-600', 'text-blue-600');
                btn.classList.add('border-transparent', 'text-gray-500');
            });
            
            // Add active class to clicked button
            button.classList.add('border-blue-600', 'text-blue-600');
            button.classList.remove('border-transparent', 'text-gray-500');
            
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.add('hidden');
            });
            
            // Show selected tab content
            const targetTab = document.getElementById(tabName + '-tab');
            if (targetTab) {
                targetTab.classList.remove('hidden');
            }
        });
    });

    // Template selection
    document.querySelectorAll('.template-option').forEach(option => {
        option.addEventListener('click', () => {
            // Remove selection from all options
            document.querySelectorAll('.template-option').forEach(opt => {
                opt.classList.remove('border-blue-600');
                opt.classList.add('border-transparent');
            });
            
            // Add selection to clicked option
            option.classList.add('border-blue-600');
            option.classList.remove('border-transparent');
        });
    });

    // File upload handling
    const csvUpload = document.getElementById('csv-upload');
    if (csvUpload) {
        csvUpload.addEventListener('change', (e) => {
            const fileName = e.target.files[0]?.name || 'No file selected';
            const nextElement = e.target.nextElementSibling;
            if (nextElement) {
                nextElement.textContent = fileName;
            }
        });
    }

    // Search functionality
    const searchInputs = document.querySelectorAll('input[type="text"][placeholder*="Search"]');
    searchInputs.forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = e.target.value;
                const currentPath = window.location.pathname;
                
                if (currentPath.includes('/dashboard')) {
                    window.location.href = `/search_events?q=${encodeURIComponent(query)}`;
                } else if (currentPath.includes('/clubs')) {
                    window.location.href = `/search_clubs?q=${encodeURIComponent(query)}`;
                }
            }
        });
    });

    // Filter buttons
    document.querySelectorAll('button[class*="bg-gray-200"]').forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all filter buttons
            document.querySelectorAll('button[class*="bg-gray-200"]').forEach(btn => {
                btn.classList.remove('bg-blue-600', 'text-white');
                btn.classList.add('bg-gray-200', 'dark:bg-gray-600', 'text-gray-700', 'dark:text-gray-300');
            });
            
            // Add active class to clicked button
            button.classList.remove('bg-gray-200', 'dark:bg-gray-600', 'text-gray-700', 'dark:text-gray-300');
            button.classList.add('bg-blue-600', 'text-white');
        });
    });

    // Notification settings toggles
    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            // Save notification preferences
            const setting = e.target.closest('label').querySelector('h3').textContent;
            localStorage.setItem(`notification_${setting.toLowerCase().replace(/\s+/g, '_')}`, e.target.checked);
        });
    });

    // Auto-refresh notifications
    if (window.location.pathname.includes('/notifications')) {
        setInterval(() => {
            fetch('/api/notifications?student_id=anita-sharma')
                .then(response => response.json())
                .then(data => {
                    // Update notification count in header
                    const notificationCount = data.length;
                    const countElement = document.querySelector('.notification-count');
                    if (countElement) {
                        countElement.textContent = notificationCount;
                        countElement.style.display = notificationCount > 0 ? 'block' : 'none';
                    }
                })
                .catch(error => console.log('Error fetching notifications:', error));
        }, 30000); // Check every 30 seconds
    }

    // Form validation
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('border-red-500');
                    field.classList.remove('border-gray-300', 'dark:border-gray-600');
                } else {
                    field.classList.remove('border-red-500');
                    field.classList.add('border-gray-300', 'dark:border-gray-600');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Loading states for buttons
    document.querySelectorAll('button[type="submit"]').forEach(button => {
        button.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="ph ph-spinner animate-spin mr-2"></i>Processing...';
            this.disabled = true;
            
            // Re-enable after 2 seconds (in case of errors)
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            }, 2000);
        });
    });

    // Dynamic content loading
    function loadContent(url, containerId) {
        fetch(url)
            .then(response => response.text())
            .then(html => {
                document.getElementById(containerId).innerHTML = html;
            })
            .catch(error => console.log('Error loading content:', error));
    }

    // Real-time updates
    if (window.location.pathname.includes('/dashboard')) {
        setInterval(() => {
            // Update event counts
            fetch('/api/events')
                .then(response => response.json())
                .then(data => {
                    // Update event statistics
                    const eventCount = data.length;
                    const countElements = document.querySelectorAll('.event-count');
                    countElements.forEach(el => {
                        el.textContent = eventCount;
                    });
                })
                .catch(error => console.log('Error fetching events:', error));
        }, 60000); // Update every minute
    }

    // Image lazy loading
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));

    // Toast notifications
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg text-white ${
            type === 'success' ? 'bg-green-600' : 
            type === 'error' ? 'bg-red-600' : 
            'bg-blue-600'
        }`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    // Global error handling
    window.addEventListener('error', (e) => {
        console.error('Global error:', e.error);
        showToast('An error occurred. Please try again.', 'error');
    });

    // Service worker registration (for PWA functionality)
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => console.log('SW registered'))
            .catch(error => console.log('SW registration failed'));
    }
});

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function debounce(func, wait) {
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

// Export functions for use in templates
window.SymbiHub = {
    formatDate,
    formatTime,
    debounce
};
