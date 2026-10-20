/* Browser-local appearance preference. Run before first paint on every route. */
(() => {
    if (window.sentinumThemeInitialized) return;
    window.sentinumThemeInitialized = true;
    const key = 'mioty-appearance';
    let storageAvailable = true;
    let theme = 'dark';
    try {
        if (localStorage.getItem(key) === 'light') theme = 'light';
    } catch (_) {
        storageAvailable = false;
    }
    const render = () => {
        document.documentElement.dataset.theme = theme;
        const button = document.getElementById('theme-toggle');
        if (button) {
            button.setAttribute('aria-checked', String(theme === 'dark'));
            button.textContent = theme === 'dark' ? 'Dunkel' : 'Hell';
        }
        const note = document.getElementById('theme-preference-note');
        if (note) note.textContent = storageAvailable
            ? 'Gilt für alle Seiten und wird in diesem Browser gespeichert.'
            : 'Die Auswahl gilt nur für diese Seite: Dein Browser erlaubt das Speichern der Darstellung nicht.';
    };
    render();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', render, { once: true });
    }
    document.addEventListener('click', event => {
        if (!event.target.closest('#theme-toggle')) return;
        theme = theme === 'dark' ? 'light' : 'dark';
        try {
            localStorage.setItem(key, theme);
            storageAvailable = true;
        } catch (_) {
            storageAvailable = false;
        }
        render();
    });
    window.addEventListener('storage', event => {
        if (event.key !== key && event.key !== null) return;
        theme = event.newValue === 'light' ? 'light' : 'dark';
        render();
    });
})();
