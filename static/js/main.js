// Main JavaScript for Profit Hub
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

    // Auto-hide alerts
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)')
        alerts.forEach(function(alert) {
            bootstrap.Alert.getOrCreateInstance(alert).close()
        })
    }, 5000)

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault()
            const target = document.querySelector(this.getAttribute('href'))
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                })
            }
        })
    })

    // Add hover effects to cards
    const cards = document.querySelectorAll('.card-dtf, .stat-card-dtf')
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('card-hover-effect')
        })

        card.addEventListener('mouseleave', function() {
            this.classList.remove('card-hover-effect')
        })
    })

    // Search functionality
    const searchBox = document.querySelector('.dtf-search-input')
    if (searchBox) {
        searchBox.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch(this.value)
            }
        })
    }

    function performSearch(query) {
        if (query.trim()) {
            window.location.href = `/search/?q=${encodeURIComponent(query)}`
        }
    }

    // Add loading animation to buttons
    const buttons = document.querySelectorAll('.btn-dtf, .btn-outline-dtf')
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!this.classList.contains('no-loading')) {
                const originalText = this.innerHTML
                this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>' + this.textContent
                this.disabled = true

                // Re-enable after 2 seconds if still disabled
                setTimeout(() => {
                    if (this.disabled) {
                        this.disabled = false
                        this.innerHTML = originalText
                    }
                }, 2000)
            }
        })
    })

    console.log('Profit Hub DTF Edition initialized successfully!')
})

// Utility functions
function formatNumber(number) {
    return new Intl.NumberFormat('ru-RU').format(number)
}

function debounce(func, wait) {
    let timeout
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout)
            func(...args)
        }
        clearTimeout(timeout)
        timeout = setTimeout(later, wait)
    }
}