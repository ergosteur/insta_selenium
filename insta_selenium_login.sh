#!/bin/bash
#
# This script sets up a virtual X11 environment with VNC and noVNC access,
# launches a lightweight window manager, and runs the insta_selenium login process
# with a visible Firefox browser (not headless). It is intended for use
# with the Dockerfile provided.

export DISPLAY=:1
unset MOZ_HEADLESS  # Ensure Firefox runs in non-headless mode for login

# Start Xvfb (virtual X server)
Xvfb :1 -screen 0 1920x1080x24 &
sleep 2

# Start a lightweight window manager
fluxbox &
sleep 2

# Start x11vnc server (add -noxdamage for blank screen issues)
x11vnc -display :1 -noxdamage -forever -nopw -listen 0.0.0.0 -xkb &
sleep 2

# Start noVNC (websocket proxy on :6080)
if [ -f /opt/websockify-0.11.0/self.pem ]; then
    /opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 --cert /opt/websockify-0.11.0/self.pem &
else
    /opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &
fi

# Run the login command (no --headless)
insta_selenium --firefox-profile-dir /data/firefox_profile --download-path /data/downloads --login