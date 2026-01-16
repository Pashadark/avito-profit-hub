// Theme toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle-btn');
    const themeIcon = themeToggle.querySelector('.theme-icon');

    // Check saved theme
    const currentTheme = localStorage.getItem('theme') || 'light';
    if (currentTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'theme-dark');
        themeIcon.className = 'ri-sun-line ri-lg theme-icon';
    }

    themeToggle.addEventListener('click', function() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'theme-dark';

        if (isDark) {
            // Switch to light
            document.documentElement.setAttribute('data-theme', 'theme-default');
            themeIcon.className = 'ri-moon-clear-line ri-lg theme-icon';
            localStorage.setItem('theme', 'light');
        } else {
            // Switch to dark
            document.documentElement.setAttribute('data-theme', 'theme-dark');
            themeIcon.className = 'ri-sun-line ri-lg theme-icon';
            localStorage.setItem('theme', 'dark');
        }
    });
});