#!/bin/bash

# Local Authentication Setup Script
# This script reads ACCESS_PASSWORD from .env and writes an ignored local override.

set -e

echo "🔐 Setting up local authentication..."
echo "⚠️  This is only a client-side UI gate; it does not protect public GitHub Pages data."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file with ACCESS_PASSWORD=your_password"
    exit 1
fi

# Load environment variables from .env
export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)

# Check if ACCESS_PASSWORD is set
if [ -z "$ACCESS_PASSWORD" ]; then
    echo "⚠️  ACCESS_PASSWORD is not set in .env file"
    echo "Password protection will be disabled"
    PASSWORD_HASH="DISABLED_NO_PASSWORD_SET_IN_SECRETS"
else
    echo "✅ Found ACCESS_PASSWORD in .env"

    # Generate SHA-256 hash using openssl
    if command -v openssl &> /dev/null; then
        PASSWORD_HASH=$(echo -n "$ACCESS_PASSWORD" | openssl dgst -sha256 -hex | awk '{print $2}')
        echo "✅ Generated SHA-256 hash using openssl"
    # Fallback to shasum if openssl is not available
    elif command -v shasum &> /dev/null; then
        PASSWORD_HASH=$(echo -n "$ACCESS_PASSWORD" | shasum -a 256 | awk '{print $1}')
        echo "✅ Generated SHA-256 hash using shasum"
    else
        echo "❌ Error: Neither openssl nor shasum is available"
        echo "Please install openssl or shasum to generate password hash"
        exit 1
    fi
fi

if [ ! -f "js/auth-config.js" ]; then
    echo "❌ Error: js/auth-config.js not found!"
    exit 1
fi

# Never modify the tracked deployment configuration. The HTML pages load this
# ignored file after auth-config.js and before auth.js for local-only testing.
printf '%s\n' \
    "if (typeof AUTH_CONFIG !== 'undefined') {" \
    "    AUTH_CONFIG.passwordHash = '$PASSWORD_HASH';" \
    "}" > js/auth-config.local.js
echo "✅ Wrote ignored local override: js/auth-config.local.js"

echo ""
echo "🎉 Local authentication setup complete!"
echo ""
echo "📝 Summary:"
echo "  - Config file: js/auth-config.local.js (ignored; local UI test only)"
echo ""
echo "💡 Tips:"
echo "  - Open login.html in browser to test"
echo "  - Use password from .env to login"
echo "  - The tracked auth-config.js was not modified"
echo ""
