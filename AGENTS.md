# Plex JAV Solution — AI Setup Guide

You are setting up a complete JAV metadata solution on **Unraid** with **Plex**.

## Architecture

```
JAV files → [JavSP Docker (with embedded MetaTube)] → NFO + artwork → [Plex + JAVnfoMoviesImporter plugin] → fully tagged library with actress avatars
```

Three components:

1. **JavSP** (`ghcr.io/nxxxsooo/plex-jav:latest`) — Docker container that scrapes metadata, generates NFO files and downloads cover/fanart artwork. Includes an **embedded MetaTube server** that provides plot/synopsis from 20+ sources including FANZA/DMM — no API keys needed.
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

3. **JavSP appdata**: "Where to store JavSP config and MetaTube data? (Default: `/mnt/user/appdata/javsp`)"

4. **Proxy/Network**: "Does your Unraid need a proxy to access the internet?
   - If yes: what's the proxy URL? (e.g., `http://192.168.1.1:7890`)
   - If no: we'll configure direct access"

5. **Docker network**: "Which Docker network should the container use? (e.g., `bridge`, `br0`, or a custom bridge)"

6. **Existing Plex**: "Do you already have Plex running on Unraid, or should I set it up fresh?"

7. **MetaTube token** (optional): "Do you want to secure the embedded MetaTube API with a token?"

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

Use the template at `config/javsp/config.yml.template` to generate a `config.yml`:

- Replace `{{PROXY_SERVER}}` with the user's proxy URL (YAML quoted) or `null`
- Replace `{{DMM_API_ID}}` and `{{DMM_AFFILIATE_ID}}` with values or `null`
- Input dir inside container is always `/media/input`
- Output dir inside container is always `/media/output`
- Save to Unraid at `<JAVSP_APPDATA>/config.yml`

**Note**: MetaTube URL is no longer needed in config — the embedded server runs at `localhost:8080` inside the container automatically.

### Step 4: Create JavSP Docker Container

**On Unraid, prefer the Docker GUI.** Guide the user to create a container with these settings:

| Setting | Value |
|---------|-------|
| Name | `plex-jav` |
| Repository | `ghcr.io/nxxxsooo/plex-jav:latest` |
| Network | User's chosen network |
| WebUI | `http://[IP]:[PORT:8501]` |
| Port | `8501` → `8501` TCP |
| Path: Config | Container: `/config` → Host: `<JAVSP_APPDATA>` |
| Path: Media | Container: `/media` → Host: `<MEDIA_PATH>` |
| Variable: PUID | `99` |
| Variable: PGID | `100` |
| Variable: UMASK | `000` |
| Variable: METATUBE_ENABLED | `1` (enables embedded MetaTube server) |
| Variable: METATUBE_TOKEN | Access token (optional, secures the embedded API) |

**If proxy is needed**, add environment variables:
```
HTTP_PROXY=<PROXY_URL>
HTTPS_PROXY=<PROXY_URL>
NO_PROXY=localhost,127.0.0.1
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
4. Verify the NFO contains a `<plot>` tag (provided by embedded MetaTube)
5. Scan the Plex library
6. Verify the movie shows up with metadata, plot, and actress avatar photos

## Key Technical Details

### Embedded MetaTube

MetaTube is a Go-based metadata server bundled inside the JavSP Docker image:
- **20+ data sources** including FANZA/DMM — built-in crawlers, no API keys needed
- Runs automatically on container start (port 8080 inside the container)
- Uses SQLite for caching, stored at `/config/metatube/metatube.db`
- JavSP's `metatube` crawler connects to `localhost:8080` automatically
- Can be disabled by setting `METATUBE_ENABLED=0`
- Optionally secured with `METATUBE_TOKEN`

### Plugin Avatar Mechanism

The plugin (`__init__.py`) fetches actress avatars via:

1. Downloads `Filetree.json` from `https://raw.githubusercontent.com/gfriends/gfriends/master/Filetree.json`
2. Uses `ssl._create_unverified_context()` to bypass SSL cert issues
3. Falls back to local `Filetree.json` if download fails
4. Maps actress names (uppercased) to GitHub-hosted avatar URLs
5. Sets `newrole.photo` for each actor in the NFO

**The plugin needs NO proxy configuration.** It handles network issues via SSL bypass + local fallback.

### JavSP Container Flow

1. Entrypoint starts embedded MetaTube server in background
2. Waits for MetaTube to be ready (up to 15 seconds)
3. Scans `/media/input` for video files
4. Identifies movie numbers from filenames
5. Queries MetaTube (localhost) for plot/synopsis (priority source)
6. Scrapes additional metadata from other sites (javbus, javdb, jav321, etc.)
7. Generates NFO file + downloads cover/fanart
8. Moves organized files to `/media/output/<actress>/<number>/`

### Unraid Permissions

All files must be owned by `99:100` (nobody:users) for Unraid compatibility.
The entrypoint handles this automatically.

### ProxyFree Sites

JavSP has built-in proxy-free mirror URLs for some sites. These change over time.
If scraping fails, the user may need to update `proxy_free` in `config.yml` with current mirrors.

## File Reference

```
plex-jav/
├── AGENTS.md                          # This file (AI setup instructions)
├── README.md                          # Brief project description
├── LICENSE                            # MIT
├── .gitignore
├── .env.example                       # Environment variable template
├── docker-compose.yml                 # Reference compose (Unraid uses Docker GUI)
├── setup.sh                           # Interactive setup script
├── setup-guide.md                     # Manual setup reference
├── .github/
│   └── workflows/
│       └── docker-build.yml           # CI/CD: builds ghcr.io/nxxxsooo/plex-jav
├── config/
│   └── javsp/
│       └── config.yml.template        # JavSP config template (AI fills in values)
├── scraper/                           # JavSP scraper source code
│   ├── javsp/                         # Main Python package
│   ├── docker/                        # Dockerfile + entrypoint
│   ├── data/                          # CSV data files
│   ├── pyproject.toml                 # Poetry project config
│   ├── poetry.lock
│   ├── config.yml                     # Default config (copied to /config in Docker)
│   └── ...
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

- JavSP (upstream, archived): https://github.com/Yuukiy/JavSP
- MetaTube: https://github.com/metatube-community/metatube-sdk-go
- JAVnfoMoviesImporter (original): https://github.com/ddd354/JAVnfoMoviesImporter.bundle
- gfriends avatar database: https://github.com/gfriends/gfriends
