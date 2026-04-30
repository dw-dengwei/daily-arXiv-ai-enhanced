const DATA_CONFIG = {
    getDataBaseUrl: function() {
        return window.location.origin;
    },

    getDataUrl: function(filePath) {
        const baseUrl = this.getDataBaseUrl().replace(/\/+$/, '');
        const cleanedPath = String(filePath || '').replace(/^\/+/, '');
        return `${baseUrl}/${cleanedPath}`;
    }
};
