#!/bin/bash
set -e

# Plex JAV Solution — One-script setup for Unraid
# https://github.com/nxxxsooo/plex-jav

REPO_URL="https://github.com/nxxxsooo/plex-jav.git"
REPO_RAW="https://raw.githubusercontent.com/nxxxsooo/plex-jav/master"

echo "============================================"
echo "  Plex JAV Solution — Unraid Setup"
echo "============================================"
echo ""

# --- Gather user input ---

read -p "Media path (parent folder for input/output, e.g. /mnt/user/media/jav): " MEDIA_PATH
MEDIA_PATH="${MEDIA_PATH%/}"

read -p "Plex appdata path [/mnt/user/appdata/plex]: " PLEX_APPDATA
PLEX_APPDATA="${PLEX_APPDATA:-/mnt/user/appdata/plex}"
PLEX_APPDATA="${PLEX_APPDATA%/}"

read -p "JavSP appdata path [/mnt/user/appdata/javsp]: " JAVSP_APPDATA
JAVSP_APPDATA="${JAVSP_APPDATA:-/mnt/user/appdata/javsp}"
JAVSP_APPDATA="${JAVSP_APPDATA%/}"

read -p "Need a proxy? (y/n) [n]: " NEED_PROXY
NEED_PROXY="${NEED_PROXY:-n}"

PROXY_URL=""
USE_PROXY="no"
EXTRA_PARAMS="--entrypoint /config/entrypoint.sh"

if [[ "$NEED_PROXY" =~ ^[Yy] ]]; then
    read -p "Proxy URL (e.g. http://192.168.1.1:7890): " PROXY_URL
    USE_PROXY="yes"
    EXTRA_PARAMS="--entrypoint /config/entrypoint.sh --env HTTP_PROXY=${PROXY_URL} --env HTTPS_PROXY=${PROXY_URL} --env NO_PROXY=localhost,127.0.0.1"
fi

read -p "Docker network [bridge]: " DOCKER_NETWORK
DOCKER_NETWORK="${DOCKER_NETWORK:-bridge}"

read -p "JavSP WebUI port [8501]: " JAVSP_PORT
JAVSP_PORT="${JAVSP_PORT:-8501}"

read -p "DMM Affiliate API ID (optional, for plot/synopsis — register free at https://affiliate.dmm.com): " DMM_API_ID
DMM_API_ID="${DMM_API_ID:-}"

read -p "DMM Affiliate ID (optional, e.g. yourname-999): " DMM_AFFILIATE_ID
DMM_AFFILIATE_ID="${DMM_AFFILIATE_ID:-}"
echo ""
echo "--- Confirm ---"
echo "Media path:     ${MEDIA_PATH}"
echo "  Input:        ${MEDIA_PATH}/input"
echo "  Output:       ${MEDIA_PATH}/output"
echo "Plex appdata:   ${PLEX_APPDATA}"
echo "JavSP appdata:  ${JAVSP_APPDATA}"
echo "Proxy:          ${USE_PROXY} ${PROXY_URL}"
echo "Network:        ${DOCKER_NETWORK}"
echo "JavSP port:     ${JAVSP_PORT}"
echo "DMM API:        ${DMM_API_ID:-(not set)} / ${DMM_AFFILIATE_ID:-(not set)}"
echo ""
read -p "Proceed? (y/n) [y]: " CONFIRM
CONFIRM="${CONFIRM:-y}"
if [[ ! "$CONFIRM" =~ ^[Yy] ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "[1/6] Creating directories..."
mkdir -p "${MEDIA_PATH}/input"
mkdir -p "${MEDIA_PATH}/output"
mkdir -p "${JAVSP_APPDATA}"
chown -R 99:100 "${MEDIA_PATH}" 2>/dev/null || true

echo "[2/6] Downloading repo..."
TMP_DIR=$(mktemp -d)
if command -v git &>/dev/null; then
    git clone --depth 1 "$REPO_URL" "$TMP_DIR/plex-jav" 2>/dev/null
else
    # Fallback: download files individually
    mkdir -p "$TMP_DIR/plex-jav/plugin/JAVnfoMoviesImporter.bundle/Contents/Code"
    mkdir -p "$TMP_DIR/plex-jav/config/javsp"
    for f in \
        "plugin/JAVnfoMoviesImporter.bundle/Contents/Code/__init__.py" \
        "plugin/JAVnfoMoviesImporter.bundle/Contents/Code/subtitles.py" \
        "plugin/JAVnfoMoviesImporter.bundle/Contents/DefaultPrefs.json" \
        "plugin/JAVnfoMoviesImporter.bundle/Contents/Info.plist" \
        "config/javsp/config.ini.template" \
        "config/javsp/entrypoint.sh"; do
        curl -sSL -o "$TMP_DIR/plex-jav/$f" "$REPO_RAW/$f"
    done
fi

echo "[3/6] Installing Plex plugin..."
PLEX_PLUGINS="${PLEX_APPDATA}/Library/Application Support/Plex Media Server/Plug-ins"
mkdir -p "$PLEX_PLUGINS"
rm -rf "$PLEX_PLUGINS/JAVnfoMoviesImporter.bundle"
cp -r "$TMP_DIR/plex-jav/plugin/JAVnfoMoviesImporter.bundle" "$PLEX_PLUGINS/"

echo "     Downloading Filetree.json (actress avatar mapping, ~4.5MB)..."
curl -sSL -o "$PLEX_PLUGINS/JAVnfoMoviesImporter.bundle/Filetree.json" \
    "https://raw.githubusercontent.com/gfriends/gfriends/master/Filetree.json" 2>/dev/null || \
    echo "     WARNING: Failed to download Filetree.json. Plugin will try at runtime."

echo "[4/6] Generating JavSP config..."
cp "$TMP_DIR/plex-jav/config/javsp/entrypoint.sh" "${JAVSP_APPDATA}/entrypoint.sh"
chmod +x "${JAVSP_APPDATA}/entrypoint.sh"

sed -e "s|{{USE_PROXY}}|${USE_PROXY}|g" \
    -e "s|{{PROXY_URL}}|${PROXY_URL}|g" \
    "$TMP_DIR/plex-jav/config/javsp/config.ini.template" > "${JAVSP_APPDATA}/config.ini"

echo "[5/6] Generating Unraid Docker template for JavSP..."
TEMPLATE_DIR="/boot/config/plugins/dockerman/templates-user"
mkdir -p "$TEMPLATE_DIR"
cat > "${TEMPLATE_DIR}/my-javsp.xml" <<XMLEOF
<?xml version="1.0"?>
<Container version="2">
  <Name>javsp</Name>
  <Repository>ghcr.io/nxxxsooo/javsp:latest</Repository>
  <Registry>https://github.com/nxxxsooo/JavSP/pkgs/container/javsp</Registry>
  <Network>${DOCKER_NETWORK}</Network>
  <MyIP/>
  <Shell>sh</Shell>
  <Privileged>true</Privileged>
  <Support>https://github.com/nxxxsooo/plex-jav</Support>
  <Project>https://github.com/nxxxsooo/plex-jav</Project>
  <Overview>JavSP metadata scraper for Plex JAV Solution</Overview>
  <WebUI>http://[IP]:[PORT:${JAVSP_PORT}]</WebUI>
  <ExtraParams>${EXTRA_PARAMS}</ExtraParams>
  <PostArgs/>
  <CPUset/>
  <DonateText/>
  <DonateLink/>
  <Requires/>
  <Config Name="WebUI Port" Target="${JAVSP_PORT}" Default="${JAVSP_PORT}" Mode="tcp" Description="JavSP WebUI" Type="Port" Display="always" Required="false" Mask="false">${JAVSP_PORT}</Config>
  <Config Name="Config" Target="/app/core/config.ini" Default="" Mode="rw" Description="JavSP configuration" Type="Path" Display="always" Required="true" Mask="false">${JAVSP_APPDATA}/config.ini</Config>
  <Config Name="Entrypoint" Target="/config/entrypoint.sh" Default="" Mode="rw" Description="Wrapper script for permissions" Type="Path" Display="always" Required="true" Mask="false">${JAVSP_APPDATA}/entrypoint.sh</Config>
  <Config Name="Media" Target="/media" Default="" Mode="rw" Description="Media folder (input + output)" Type="Path" Display="always" Required="true" Mask="false">${MEDIA_PATH}</Config>
  <Config Name="PUID" Target="PUID" Default="99" Mode="" Description="" Type="Variable" Display="always" Required="false" Mask="false">99</Config>
  <Config Name="PGID" Target="PGID" Default="100" Mode="" Description="" Type="Variable" Display="always" Required="false" Mask="false">100</Config>
  <Config Name="UMASK" Target="UMASK" Default="000" Mode="" Description="" Type="Variable" Display="always" Required="false" Mask="false">000</Config>
  <Config Name="DMM_API_ID" Target="DMM_API_ID" Default="" Mode="" Description="DMM Affiliate API ID (for plot/synopsis)" Type="Variable" Display="always" Required="false" Mask="false">${DMM_API_ID}</Config>
  <Config Name="DMM_AFFILIATE_ID" Target="DMM_AFFILIATE_ID" Default="" Mode="" Description="DMM Affiliate ID (for plot/synopsis)" Type="Variable" Display="always" Required="false" Mask="false">${DMM_AFFILIATE_ID}</Config>
</Container>
XMLEOF

echo "[6/6] Cleanup..."
rm -rf "$TMP_DIR"

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "What's done:"
echo "  - Plugin installed to Plex"
echo "  - JavSP config at ${JAVSP_APPDATA}/config.ini"
echo "  - Unraid Docker template created (check Docker tab)"
echo "  - Media folders: ${MEDIA_PATH}/input and ${MEDIA_PATH}/output"
if [ -n "${DMM_API_ID}" ]; then
echo "  - DMM API configured (plot/synopsis enabled)"
else
echo "  - DMM API not configured (plot/synopsis disabled — register at https://affiliate.dmm.com)"
fi
echo ""
echo "Next steps:"
echo "  1. Restart Plex (Docker tab → plex → Restart)"
echo "  2. Add JavSP container (Docker tab → Add Container → Template: javsp)"
echo "  3. Create a Movies library in Plex:"
echo "     - Content folder: ${MEDIA_PATH}/output"
echo "     - Agent: JAVnfoMoviesImporter"
echo "  4. Drop files into ${MEDIA_PATH}/input, run JavSP, scan library"
echo ""
