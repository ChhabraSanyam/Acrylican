#!/bin/bash

# Script to generate secure secrets for production deployment
# Run this script to generate random secure passwords and keys

set -e

echo "🔐 Generating secure secrets for Artisan Promotion Platform..."

# Function to generate random password
generate_password() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate hex key
generate_hex_key() {
    local length=${1:-32}
    openssl rand -hex $length
}

# Create secrets file
SECRETS_FILE=".env.production.secrets"

cat > $SECRETS_FILE << EOF
# Generated secrets for production deployment
# Generated on: $(date)
# IMPORTANT: Keep this file secure and never commit to version control

# Database passwords
POSTGRES_PASSWORD=$(generate_password 24)
REDIS_PASSWORD=$(generate_password 24)

# Application security keys
SECRET_KEY=$(generate_password 64)
JWT_SECRET_KEY=$(generate_password 64)
ENCRYPTION_KEY=$(generate_hex_key 16)

# SMTP password (you'll need to set this manually)
SMTP_PASSWORD=your_smtp_password_here

# Cloud storage keys (you'll need to set these manually)
CLOUD_STORAGE_ACCESS_KEY=your_cloud_storage_access_key
CLOUD_STORAGE_SECRET_KEY=your_cloud_storage_secret_key

# Platform API secrets (you'll need to set these manually)
FACEBOOK_APP_SECRET=your_facebook_app_secret
INSTAGRAM_APP_SECRET=your_instagram_app_secret
ETSY_API_SECRET=your_etsy_api_secret
PINTEREST_APP_SECRET=your_pinterest_app_secret
SHOPIFY_API_SECRET=your_shopify_api_secret

# Gemini API key (you'll need to set this manually)
GEMINI_API_KEY=your_google_gemini_api_key_here

# Sentry DSN (you'll need to set this manually)
SENTRY_DSN=your_sentry_dsn_for_error_tracking
EOF

echo "✅ Secrets generated and saved to $SECRETS_FILE"
echo ""
echo "📋 Next steps:"
echo "1. Review the generated secrets in $SECRETS_FILE"
echo "2. Manually add your API keys and external service credentials"
echo "3. Copy the secrets to your production environment"
echo "4. Ensure $SECRETS_FILE is not committed to version control"
echo ""
echo "⚠️  SECURITY WARNING:"
echo "   - Keep $SECRETS_FILE secure and never share it"
echo "   - Use environment-specific secret management in production"
echo "   - Consider using Docker secrets or Kubernetes secrets"
echo "   - Rotate secrets regularly"

# Set restrictive permissions
chmod 600 $SECRETS_FILE

echo ""
echo "🔒 File permissions set to 600 (owner read/write only)"