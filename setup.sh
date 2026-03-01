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
PROXY_SERVER="null"
PROXY_ENVS=""

if [[ "$NEED_PROXY" =~ ^[Yy] ]]; then
    read -p "Proxy URL (e.g. http://192.168.1.1:7890): " PROXY_URL
    PROXY_SERVER="'${PROXY_URL}'"
    PROXY_ENVS="--env HTTP_PROXY=${PROXY_URL} --env HTTPS_PROXY=${PROXY_URL} --env NO_PROXY=localhost,127.0.0.1"
fi

read -p "Docker network [bridge]: " DOCKER_NETWORK
DOCKER_NETWORK="${DOCKER_NETWORK:-bridge}"

read -p "JavSP WebUI port [8501]: " JAVSP_PORT
JAVSP_PORT="${JAVSP_PORT:-8501}"

read -p "MetaTube access token (optional, secures the embedded API): " METATUBE_TOKEN
METATUBE_TOKEN="${METATUBE_TOKEN:-}"

read -p "DMM Affiliate API ID (optional, legacy): " DMM_API_ID
DMM_API_ID="${DMM_API_ID:-}"

read -p "DMM Affiliate ID (optional, e.g. yourname-999): " DMM_AFFILIATE_ID
DMM_AFFILIATE_ID="${DMM_AFFILIATE_ID:-}"
echo ""
echo "--- Confirm ---"
echo "Media path:       ${MEDIA_PATH}"
echo "  Input:          ${MEDIA_PATH}/input"
echo "  Output:         ${MEDIA_PATH}/output"
echo "Plex appdata:     ${PLEX_APPDATA}"
echo "JavSP appdata:    ${JAVSP_APPDATA}"
echo "Proxy:            ${PROXY_URL:-(direct)}"
echo "Network:          ${DOCKER_NETWORK}"
echo "JavSP port:       ${JAVSP_PORT}"
echo "MetaTube:         embedded in JavSP (auto-start)"
echo "MetaTube token:   ${METATUBE_TOKEN:-(not set)}"
echo "DMM API:          ${DMM_API_ID:-(not set)} / ${DMM_AFFILIATE_ID:-(not set)}"
echo ""
read -p "Proceed? (y/n) [y]: " CONFIRM
CONFIRM="${CONFIRM:-y}"
if [[ ! "$CONFIRM" =~ ^[Yy] ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "[1/5] Creating directories..."
mkdir -p "${MEDIA_PATH}/input"
mkdir -p "${MEDIA_PATH}/output"
mkdir -p "${JAVSP_APPDATA}"
chown -R 99:100 "${MEDIA_PATH}" 2>/dev/null || true

echo "[2/5] Downloading repo..."
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
        "config/javsp/config.yml.template"; do
        curl -sSL -o "$TMP_DIR/plex-jav/$f" "$REPO_RAW/$f"
    done
fi

echo "[3/5] Installing Plex plugin..."
PLEX_PLUGINS="${PLEX_APPDATA}/Library/Application Support/Plex Media Server/Plug-ins"
mkdir -p "$PLEX_PLUGINS"
rm -rf "$PLEX_PLUGINS/JAVnfoMoviesImporter.bundle"
cp -r "$TMP_DIR/plex-jav/plugin/JAVnfoMoviesImporter.bundle" "$PLEX_PLUGINS/"

echo "     Downloading Filetree.json (actress avatar mapping, ~4.5MB)..."
curl -sSL -o "$PLEX_PLUGINS/JAVnfoMoviesImporter.bundle/Filetree.json" \
    "https://raw.githubusercontent.com/gfriends/gfriends/master/Filetree.json" 2>/dev/null || \
    echo "     WARNING: Failed to download Filetree.json. Plugin will try at runtime."

echo "[4/5] Generating JavSP config..."

# Format DMM values for YAML (null if empty, quoted if set)
DMM_API_ID_YAML="null"
DMM_AFFILIATE_ID_YAML="null"
if [ -n "$DMM_API_ID" ]; then
    DMM_API_ID_YAML="'${DMM_API_ID}'"
fi
if [ -n "$DMM_AFFILIATE_ID" ]; then
    DMM_AFFILIATE_ID_YAML="'${DMM_AFFILIATE_ID}'"
fi

sed -e "s|{{PROXY_SERVER}}|${PROXY_SERVER}|g" \
    -e "s|{{DMM_API_ID}}|${DMM_API_ID_YAML}|g" \
    -e "s|{{DMM_AFFILIATE_ID}}|${DMM_AFFILIATE_ID_YAML}|g" \
    "$TMP_DIR/plex-jav/config/javsp/config.yml.template" > "${JAVSP_APPDATA}/config.yml"

# Remove old config.ini from previous versions
rm -f "${JAVSP_APPDATA}/config.ini" 2>/dev/null || true

echo "[5/5] Generating Unraid Docker template for JavSP..."
TEMPLATE_DIR="/boot/config/plugins/dockerman/templates-user"
mkdir -p "$TEMPLATE_DIR"

# Build extra params
EXTRA_PARAMS=""
if [ -n "$PROXY_ENVS" ]; then
    EXTRA_PARAMS="$PROXY_ENVS"
fi

cat > "${TEMPLATE_DIR}/my-plex-jav.xml" <<XMLEOF
<?xml version="1.0"?>
<Container version="2">
  <Name>plex-jav</Name>
  <Repository>ghcr.io/nxxxsooo/plex-jav:latest</Repository>
  <Registry>https://github.com/nxxxsooo/plex-jav/pkgs/container/plex-jav</Registry>
  <Network>${DOCKER_NETWORK}</Network>
  <MyIP/>
  <Shell>sh</Shell>
  <Privileged>false</Privileged>
  <Support>https://github.com/nxxxsooo/plex-jav</Support>
  <Project>https://github.com/nxxxsooo/plex-jav</Project>
  <Overview>JavSP metadata scraper with embedded MetaTube server for Plex JAV Solution</Overview>
  <WebUI>http://[IP]:[PORT:${JAVSP_PORT}]</WebUI>
  <ExtraParams>${EXTRA_PARAMS}</ExtraParams>
  <PostArgs/>
  <CPUset/>
  <DonateText/>
  <DonateLink/>
  <Requires/>
  <Config Name="WebUI Port" Target="8501" Default="8501" Mode="tcp" Description="JavSP WebUI" Type="Port" Display="always" Required="false" Mask="false">${JAVSP_PORT}</Config>
  <Config Name="Config" Target="/config" Default="" Mode="rw" Description="JavSP + MetaTube config/data" Type="Path" Display="always" Required="true" Mask="false">${JAVSP_APPDATA}</Config>
  <Config Name="Media" Target="/media" Default="" Mode="rw" Description="Media folder (input + output)" Type="Path" Display="always" Required="true" Mask="false">${MEDIA_PATH}</Config>
  <Config Name="PUID" Target="PUID" Default="99" Mode="" Description="" Type="Variable" Display="always" Required="false" Mask="false">99</Config>
  <Config Name="PGID" Target="PGID" Default="100" Mode="" Description="" Type="Variable" Display="always" Required="false" Mask="false">100</Config>
  <Config Name="UMASK" Target="UMASK" Default="000" Mode="" Description="" Type="Variable" Display="always" Required="false" Mask="false">000</Config>
  <Config Name="METATUBE_ENABLED" Target="METATUBE_ENABLED" Default="1" Mode="" Description="Enable embedded MetaTube server (1=yes, 0=no)" Type="Variable" Display="always" Required="false" Mask="false">1</Config>
  <Config Name="METATUBE_TOKEN" Target="METATUBE_TOKEN" Default="" Mode="" Description="MetaTube access token (optional)" Type="Variable" Display="always" Required="false" Mask="false">${METATUBE_TOKEN}</Config>
  <Config Name="DMM_API_ID" Target="DMM_API_ID" Default="" Mode="" Description="DMM Affiliate API ID (legacy, optional)" Type="Variable" Display="always" Required="false" Mask="false">${DMM_API_ID}</Config>
  <Config Name="DMM_AFFILIATE_ID" Target="DMM_AFFILIATE_ID" Default="" Mode="" Description="DMM Affiliate ID (legacy, optional)" Type="Variable" Display="always" Required="false" Mask="false">${DMM_AFFILIATE_ID}</Config>
</Container>
XMLEOF

# Remove old MetaTube template if it exists from previous version
rm -f "${TEMPLATE_DIR}/my-metatube.xml" 2>/dev/null || true
rm -f "${TEMPLATE_DIR}/my-javsp.xml" 2>/dev/null || true

echo "     Cleanup..."
rm -rf "$TMP_DIR"

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "What's done:"
echo "  - Plugin installed to Plex"
echo "  - JavSP config at ${JAVSP_APPDATA}/config.yml"
echo "  - JavSP template created (with embedded MetaTube server)"
echo "  - Media folders: ${MEDIA_PATH}/input and ${MEDIA_PATH}/output"
echo ""
echo "Next steps:"
echo "  1. Restart Plex (Docker tab → plex → Restart)"
echo "  2. Add JavSP container (Docker tab → Add Container → Template: javsp)"
echo "  3. Create a Movies library in Plex:"
echo "     - Content folder: ${MEDIA_PATH}/output"
echo "     - Agent: JAVnfoMoviesImporter"
echo "  4. Drop files into ${MEDIA_PATH}/input, run JavSP, scan library"
echo ""
