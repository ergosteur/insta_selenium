#!/bin/bash
#
# This script sets up a virtual X11 environment with VNC and noVNC access,
# launches a lightweight window manager, and runs the insta_selenium login process
# with a visible Firefox browser (not headless). It is intended for use
# with the Dockerfile provided.

# Start Xvfb (virtual X server)
Xvfb :1 -screen 0 1920x1080x24 &
sleep 2

# Start a lightweight window manager
fluxbox &

# Start x11vnc server (no password, for demo; set a password for security!)
x11vnc -display :1 -forever -nopw -listen 0.0.0.0 -xkb &

# Start noVNC (websocket proxy on :6080)
/opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &

# Run the login command (no --headless)
insta_selenium --firefox-profile-dir /data/firefox_profile --download-path /data/downloads --login