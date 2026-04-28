/**
 * Data Source Configuration
 *
 * Local/LAN deployments serve the generated data files from the same site as
 * the HTML pages, so all data requests should resolve relative to the current
 * page instead of GitHub Raw.
 */

const DATA_CONFIG = {
    /**
     * Get the base URL for same-origin static files.
     * Works for both "/" and nested paths such as "/daily-arXiv-ai-enhanced/".
     * @returns {string} Base URL for static data files
     */
    getDataBaseUrl: function() {
        return new URL('.', window.location.href).toString();
    },

    /**
     * Get the full URL for a data file.
     * @param {string} filePath - Relative path to the data file (e.g., 'data/2025-01-01.jsonl')
     * @returns {string} Full URL to the data file
     */
    getDataUrl: function(filePath) {
        const normalizedPath = filePath.replace(/^\/+/, '');
        return new URL(normalizedPath, this.getDataBaseUrl()).toString();
    }
};

