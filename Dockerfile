FROM python:3.12-slim

# Install Firefox and dependencies for both headless and VNC/noVNC operation
RUN apt-get update && \
    apt-get install -y --no-install-recommends firefox-esr wget gnupg curl jq && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y --no-install-recommends xvfb fluxbox x11vnc openssl nano xterm && \
    rm -rf /var/lib/apt/lists/*

# Install geckodriver
RUN set -eux; \
    url=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest | \
        jq -r '.assets[] | select(.name | test("linux64.tar.gz$")) | .browser_download_url'); \
    if [ -z "$url" ] || [ "$url" = "null" ]; then \
        echo "Could not find geckodriver linux64 asset in GitHub API response"; \
        exit 1; \
    fi; \
    wget -O /tmp/geckodriver.tar.gz "$url"; \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin; \
    rm /tmp/geckodriver.tar.gz

# Install noVNC and websockify
RUN wget -qO- https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz | tar xz -C /opt && \
    ln -s /opt/noVNC-1.4.0 /opt/novnc && \
    wget -qO- https://github.com/novnc/websockify/archive/refs/tags/v0.11.0.tar.gz | tar xz -C /opt && \
    ln -s /opt/websockify-0.11.0 /opt/novnc/utils/websockify

RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /opt/websockify-0.11.0/self.pem \
  -out /opt/websockify-0.11.0/self.pem \
  -subj "/CN=localhost"

# Set workdir and copy code
WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip && pip install .

# Create /data directory for persistent storage (profile + downloads)
RUN mkdir -p /data/firefox_profile /data/downloads

# Copy login entrypoint script
COPY insta_selenium_login.sh /usr/local/bin/insta_selenium_login
RUN chmod +x /usr/local/bin/insta_selenium_login

# Set environment variable for headless operation by default
ENV MOZ_HEADLESS=1

# Expose VNC and noVNC ports for login mode
EXPOSE 5900 6080

# Default command (can be overridden)
#CMD ["insta_selenium_login", "--firefox-profile-dir", "/data/firefox_profile", "--download-path", "/data/downloads"]
CMD ["insta_selenium", "--firefox-profile-dir", "/data/firefox_profile", "--download-path", "/data/downloads", "--headless"]