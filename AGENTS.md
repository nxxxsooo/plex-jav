# Plex JAV Solution — AI Setup Guide

You are setting up a complete JAV metadata solution on **Unraid** with **Plex**.

## Architecture

```
JAV files → [JavSP Docker] → NFO + artwork → [Plex + JAVnfoMoviesImporter plugin] → fully tagged library with actress avatars
```

Three components:

1. **JavSP** (`ghcr.io/nxxxsooo/javsp:latest`) — Docker container that scrapes metadata, generates NFO files and downloads cover/fanart artwork. Includes DMM Affiliate API support for plot/synopsis data.
2. **JAVnfoMoviesImporter.bundle** — Plex plugin that reads NFO files and automatically fetches actress avatar photos from the [gfriends](https://github.com/gfriends/gfriends) database
3. **Unraid Docker + Plex** — the runtime environment

## Setup Workflow

When a user asks you to set up this solution, follow these steps:

### Step 1: Gather User Environment

Ask the user these questions (adapt based on what they volunteer):

1. **Media path**: "Where on your Unraid do you want to store JAV files? I need:
   - An **input** folder (where you drop raw JAV files)
   - An **output** folder (where JavSP writes organized files with NFO/artwork)
   - Example: `/mnt/user/media/jav/` with `input/` and `output/` subdirectories"

2. **Plex appdata**: "Where is your Plex appdata? (Usually `/mnt/user/appdata/plex`)"

3. **Proxy/Network**: "Does your Unraid need a proxy to access the internet?
   - If yes: what's the proxy URL? (e.g., `http://192.168.1.1:7890`)
   - If no: we'll configure direct access"

4. **Docker network**: "Which Docker network should the containers use? (e.g., `bridge`, `br0`, or a custom bridge like `proxynet`)"

5. **Existing Plex**: "Do you already have Plex running on Unraid, or should I set it up fresh?"

6. **DMM API** (optional): "Do you have a DMM Affiliate API account? This enables plot/synopsis data.
   - If yes: what's your API ID and Affiliate ID?
   - If no: you can register for free at https://affiliate.dmm.com/ (takes 1-3 business days for approval)"

### Step 2: Install the Plugin

Copy the plugin bundle to Plex's plugin directory:

```bash
# Source: this repo's plugin/ directory
# Destination: Plex plugin directory on Unraid

PLEX_PLUGINS="<PLEX_APPDATA>/Library/Application Support/Plex Media Server/Plug-ins"

# Copy the entire bundle
cp -r plugin/JAVnfoMoviesImporter.bundle "$PLEX_PLUGINS/"

# The plugin ships WITHOUT Filetree.json (4.5MB gfriends avatar mapping)
# It will be auto-downloaded on first use, or can be pre-fetched:
curl -L -o "$PLEX_PLUGINS/JAVnfoMoviesImporter.bundle/Filetree.json" \
  "https://raw.githubusercontent.com/gfriends/gfriends/master/Filetree.json"
```

After copying, restart Plex. The plugin appears as agent **"JAVnfoMoviesImporter"** in Plex settings.

**Plex Agent Configuration:**
- Go to Settings → Agents → Movies → JAVnfoMoviesImporter
- Set as primary agent for your JAV library

### Step 3: Generate JavSP Config

Use the template at `config/javsp/config.ini.template` to generate a `config.ini`:

- Replace `{{USE_PROXY}}` with `yes` or `no`
- Replace `{{PROXY_URL}}` with the user's proxy URL (or leave empty)
- Input dir inside container is always `/media/input`
- Output dir inside container is always `/media/output`
- Save to Unraid at `<JAVSP_APPDATA>/config.ini`

If the user has DMM API credentials, set the `DMM_API_ID` and `DMM_AFFILIATE_ID` environment variables on the Docker container. These enable plot/synopsis fetching from FANZA via the DMM Affiliate API.

Also copy `config/javsp/entrypoint.sh` to `<JAVSP_APPDATA>/entrypoint.sh` and `chmod +x` it.

### Step 4: Create JavSP Docker Container

**On Unraid, prefer the Docker GUI.** Guide the user to create a container with these settings:

| Setting | Value |
|---------|-------|
| Name | `javsp` |
| Repository | `ghcr.io/nxxxsooo/javsp:latest` |
| Network | User's chosen network |
| WebUI | `http://[IP]:[PORT:8501]` |
| Extra Parameters | `--entrypoint /config/entrypoint.sh` |
| Port | `8501` → `8501` TCP |
| Path: config | Container: `/app/core/config.ini` → Host: `<JAVSP_APPDATA>/config.ini` |
| Path: entrypoint | Container: `/config/entrypoint.sh` → Host: `<JAVSP_APPDATA>/entrypoint.sh` |
| Path: media | Container: `/media` → Host: `<MEDIA_PATH>` |
| Variable: PUID | `99` |
| Variable: PGID | `100` |
| Variable: UMASK | `000` |
| Variable: DMM_API_ID | DMM Affiliate API ID (optional, for plot/synopsis) |
| Variable: DMM_AFFILIATE_ID | DMM Affiliate ID (optional, for plot/synopsis) |

**If proxy is needed**, add to Extra Parameters:
```
--entrypoint /config/entrypoint.sh --env HTTP_PROXY=<PROXY_URL> --env HTTPS_PROXY=<PROXY_URL> --env NO_PROXY=localhost,127.0.0.1
```

Alternatively, an Unraid XML template can be generated — see `docker-compose.yml` for the equivalent compose definition.

### Step 5: Create Media Folder Structure

```bash
mkdir -p <MEDIA_PATH>/input   # Drop raw JAV files here
mkdir -p <MEDIA_PATH>/output  # JavSP writes organized files here
chown -R 99:100 <MEDIA_PATH>
```

### Step 6: Configure Plex Library

Guide the user:
1. Create a new **Movies** library in Plex
2. Add `<MEDIA_PATH>/output` as the content folder
3. Set the agent to **JAVnfoMoviesImporter**
4. Under Advanced, enable "Local Media Assets" as well
5. Scan the library

### Step 7: Verify

Test the full pipeline:
1. Drop a JAV file into `<MEDIA_PATH>/input`
2. Run or trigger the JavSP container (via WebUI at port 8501)
3. Check that NFO + artwork appear in `<MEDIA_PATH>/output/<actress>/<number>/`
4. Scan the Plex library
5. Verify the movie shows up with metadata and actress avatar photos

## Key Technical Details

### Plugin Avatar Mechanism

The plugin (`__init__.py`) fetches actress avatars via:

1. Downloads `Filetree.json` from `https://raw.githubusercontent.com/gfriends/gfriends/master/Filetree.json`
2. Uses `ssl._create_unverified_context()` to bypass SSL cert issues
3. Falls back to local `Filetree.json` if download fails
4. Maps actress names (uppercased) to GitHub-hosted avatar URLs
5. Sets `newrole.photo` for each actor in the NFO

**The plugin needs NO proxy configuration.** It handles network issues via SSL bypass + local fallback.

### JavSP Container Flow

1. Scans `/media/input` for video files
2. Identifies movie numbers from filenames
3. Scrapes metadata from multiple sites (javbus, javdb, jav321, etc.)
4. Generates NFO file + downloads cover/fanart
5. Moves organized files to `/media/output/<actress>/<number>/`
6. `entrypoint.sh` fixes ownership to `99:100` (Unraid nobody:users)

### Unraid Permissions

All files must be owned by `99:100` (nobody:users) for Unraid compatibility.
The `entrypoint.sh` wrapper handles this automatically after JavSP runs.

### ProxyFree Sites

JavSP has built-in proxy-free mirror URLs for some sites. These change over time.
If scraping fails, the user may need to update `[ProxyFree]` in `config.ini` with current mirrors.

## File Reference

```
plex-jav/
├── AGENTS.md                          # This file (AI setup instructions)
├── README.md                          # Brief project description
├── LICENSE                            # MIT
├── .gitignore
├── .env.example                       # Environment variable template
├── docker-compose.yml                 # Reference compose (Unraid uses Docker GUI)
├── config/
│   └── javsp/
│       ├── config.ini.template        # JavSP config template (AI fills in values)
│       └── entrypoint.sh             # Permission-fixing wrapper script
└── plugin/
    └── JAVnfoMoviesImporter.bundle/   # Plex plugin (copy to Plex Plug-ins dir)
        ├── Contents/
        │   ├── Code/
        │   │   ├── __init__.py        # Main plugin (avatar scraping logic)
        │   │   └── subtitles.py       # Subtitle file handler
        │   ├── DefaultPrefs.json      # Plugin preferences schema
        │   └── Info.plist             # Plugin manifest
        └── .gitignore
```

## Upstream References

- JavSP: https://github.com/Yuukiy/JavSP
- JAVnfoMoviesImporter (original): https://github.com/ddd354/JAVnfoMoviesImporter.bundle
- gfriends avatar database: https://github.com/gfriends/gfriends
- JavSP Docker image (fork): https://github.com/nxxxsooo/JavSP/pkgs/container/javsp
