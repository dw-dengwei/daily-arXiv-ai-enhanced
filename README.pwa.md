# PWA Support Documentation

This document describes how to test and use the PWA (Progressive Web App) features of Daily arXiv AI Enhanced.

## Local Testing

1. Serve the site locally:
   ```bash
   python -m http.server 8000
   # Or with HTTPS using mkcert:
   # mkcert localhost
   # python -m http.server 8000 --cert=localhost.pem --key=localhost-key.pem
   ```

2. Open Chrome and navigate to:
   - http://localhost:8000 (or https://localhost:8000 if using HTTPS)

## Installing on Android

1. Open Chrome on your Android device
2. Visit the deployed site (e.g., https://your-username.github.io/daily-arXiv-ai-enhanced-moviable/)
3. Tap the menu (three dots) in the upper right
4. Select "Add to Home screen"
5. Follow the prompts to install the PWA

## Testing Offline Support

1. Install the PWA as described above
2. Enable airplane mode or disable network connection
3. Launch the app from your home screen
4. Verify that the main page and precached resources are available offline

## PWA Features

- Full offline support for main pages
- Installable on Android devices
- Responsive design optimized for mobile
- Fast loading with service worker caching

## Lighthouse Testing

Run a Lighthouse PWA audit locally:

```bash
# Install Lighthouse CLI
npm install -g @lhci/cli

# Run audit (replace URL with your local or deployed URL)
lhci autorun --collect.url=https://localhost:8000
```

## Reverting PWA Changes

To remove PWA support, delete or revert the following files:

1. manifest.json
2. service-worker.js
3. icons/icon-192.png
4. icons/icon-512.png

And remove the following lines from index.html (and other HTML files):
- `<link rel="manifest" href="/manifest.json">`
- `<meta name="theme-color" content="#2196f3">`
- `<link rel="apple-touch-icon" href="/icons/icon-192.png">`
- The service worker registration script at the bottom of the file
