// Minimal sanitization helpers for rendering API/user-provided strings into HTML.
// Avoids XSS when we must use template strings/innerHTML in the vanilla frontend.
(function () {
    const escapeHtml = (value) => {
        const str = String(value ?? '');
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    const safeUrl = (value) => {
        if (!value) return '#';
        try {
            // Resolve relative URLs against the current origin.
            const url = new URL(String(value), window.location.origin);
            if (url.protocol === 'http:' || url.protocol === 'https:') {
                return url.href;
            }
        } catch (_error) {
            // Fall through.
        }
        return '#';
    };

    window.NEXTSTEP_SANITIZE = { escapeHtml, safeUrl };
})();

