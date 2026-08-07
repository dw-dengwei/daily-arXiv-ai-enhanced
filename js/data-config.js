/**
 * Data Source Configuration
 * Repository information is derived from the GitHub Pages URL. This keeps
 * forks working without committing an owner-specific generated file.
 */

function getGitHubPagesRepository() {
    const hostParts = window.location.hostname.split('.');
    const pathParts = window.location.pathname.split('/').filter(Boolean);
    const isProjectPage = hostParts.length >= 3 &&
        hostParts.slice(-2).join('.') === 'github.io' && pathParts.length > 0;

    return {
        owner: isProjectPage ? hostParts[0] : 'laoyunzai',
        name: isProjectPage ? pathParts[0] : 'daily-arXiv-ai-enhanced'
    };
}

const githubPagesRepository = getGitHubPagesRepository();

const DATA_CONFIG = {
    /**
     * GitHub repository owner (username)
     * Derived from the current GitHub Pages project URL
     */
    repoOwner: githubPagesRepository.owner,

    /**
     * GitHub repository name
     * Derived from the current GitHub Pages project URL
     */
    repoName: githubPagesRepository.name,

    /**
     * Data branch name
     * Default: 'data'
     */
    dataBranch: 'data',

    /**
     * Get the base URL for raw GitHub content from data branch
     * @returns {string} Base URL for raw GitHub content
     */
    getDataBaseUrl: function() {
        return `https://raw.githubusercontent.com/${this.repoOwner}/${this.repoName}/${this.dataBranch}`;
    },

    /**
     * Get the full URL for a data file
     * @param {string} filePath - Relative path to the data file (e.g., 'data/2025-01-01.jsonl')
     * @returns {string} Full URL to the data file
     */
    getDataUrl: function(filePath) {
        const encodedPath = filePath.split('/').map(encodeURIComponent).join('/');
        return `${this.getDataBaseUrl()}/${encodedPath}`;
    }
};
