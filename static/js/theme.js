/**
 * Theme Toggle System
 * Handles light/dark mode switching with persistence
 */

class ThemeManager {
    constructor() {
        this.init();
    }

    init() {
        // Get saved theme or default to light
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.applyTheme(this.currentTheme);
        this.createThemeToggle();
        this.updateChartTheme();
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        localStorage.setItem('theme', theme);
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        this.updateChartTheme();
        this.updateThemeToggle();
    }

    createThemeToggle() {
        // Check if toggle already exists
        if (document.querySelector('.theme-toggle')) return;

        const toggle = document.createElement('button');
        toggle.className = 'theme-toggle';
        toggle.setAttribute('aria-label', 'Toggle theme');
        toggle.innerHTML = this.getToggleIcon();
        
        toggle.addEventListener('click', () => this.toggleTheme());
        document.body.appendChild(toggle);
    }

    updateThemeToggle() {
        const toggle = document.querySelector('.theme-toggle');
        if (toggle) {
            toggle.innerHTML = this.getToggleIcon();
        }
    }

    getToggleIcon() {
        const lightIcon = `
            <svg class="theme-toggle-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
            </svg>
            <span>Light</span>
        `;
        
        const darkIcon = `
            <svg class="theme-toggle-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
            </svg>
            <span>Dark</span>
        `;

        return this.currentTheme === 'light' ? darkIcon : lightIcon;
    }

    updateChartTheme() {
        // Update Chart.js default colors for theme
        if (typeof Chart !== 'undefined') {
            const isDark = this.currentTheme === 'dark';
            
            Chart.defaults.color = isDark ? '#cbd5e1' : '#475569';
            Chart.defaults.borderColor = isDark ? '#334155' : '#e2e8f0';
            Chart.defaults.backgroundColor = isDark ? '#1e293b' : '#ffffff';
            
            // Update existing charts
            Chart.instances.forEach(chart => {
                if (chart.options.scales) {
                    const gridColor = isDark ? '#334155' : '#e2e8f0';
                    const tickColor = isDark ? '#cbd5e1' : '#475569';
                    
                    ['x', 'y'].forEach(axis => {
                        if (chart.options.scales[axis]) {
                            if (chart.options.scales[axis].grid) {
                                chart.options.scales[axis].grid.color = gridColor;
                            }
                            if (chart.options.scales[axis].ticks) {
                                chart.options.scales[axis].ticks.color = tickColor;
                            }
                        }
                    });
                }
                chart.update();
            });
        }
    }

    // Get current theme colors for JavaScript use
    getThemeColors() {
        const isDark = this.currentTheme === 'dark';
        
        return {
            primary: isDark ? '#f8fafc' : '#0f172a',
            secondary: isDark ? '#cbd5e1' : '#475569',
            tertiary: isDark ? '#94a3b8' : '#64748b',
            accent: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#06b6d4',
            background: isDark ? '#020617' : '#ffffff',
            surface: isDark ? '#1e293b' : '#f8fafc',
            border: isDark ? '#334155' : '#e2e8f0'
        };
    }
}

// Initialize theme manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeManager;
}