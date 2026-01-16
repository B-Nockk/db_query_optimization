FROM nginx:alpine

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy configuration templates
COPY conf.d/default.conf /etc/nginx/templates/default.conf.template
COPY includes/ /etc/nginx/includes/

# Set default environment variables
ENV API_HOST=api \
  API_PORT=8000 \
  SERVER_NAME=localhost \
  SSL_ENABLED=false \
  SSL_CERT_PATH=/etc/nginx/ssl/cert.pem \
  SSL_KEY_PATH=/etc/nginx/ssl/key.pem

# The official nginx image automatically runs envsubst on /etc/nginx/templates/*.template
# and outputs to /etc/nginx/conf.d/

EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1