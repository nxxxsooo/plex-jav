# Plex JAV Solution

A complete JAV metadata solution for **Unraid + Plex** — on-demand scraping, NFO generation, plot/synopsis fetching, and actress avatar support.

## What It Does

```
Move completed JAV files into input → start plex-jav once → Plex reads NFO + fetches actress photos
```

- **JavSP** (Docker) scrapes metadata from multiple sources, generates NFO files and downloads artwork. Includes an embedded **MetaTube** server that provides plot/synopsis from 20+ sources including FANZA/DMM — no API keys needed
- **JAVnfoMoviesImporter** (Plex plugin) reads NFO files and automatically fetches actress avatar photos from [gfriends](https://github.com/gfriends/gfriends)

`plex-jav` is an on-demand job, not a continuously running service. Move only
completed downloads into the input directory, start the container manually in
Unraid, and inspect its log. The container exits after one scan; exit code `0`
means the batch completed successfully.

## Setup

### Option 1: Interactive Script

SSH into your Unraid and run:

```bash
curl -sSL https://raw.githubusercontent.com/nxxxsooo/plex-jav/master/setup.sh | bash
```

The script will ask a few questions about your environment (media paths, proxy, network), then automatically:

- Install the Plex plugin
- Download the actress avatar database
- Generate JavSP config (with embedded MetaTube for plot/synopsis)
- Create Unraid Docker template

## Run A Batch

1. Finish the download outside the configured input directory.
2. Move the completed video into the input directory.
3. In the Unraid Docker tab, start the stopped `plex-jav` container.
4. Follow its log. The container stops after one scan; exit code `0` means the
   batch completed successfully.

## Upgrade From v1.x

v2 changes `plex-jav` from a continuously running MetaTube service into a
manually started one-shot job. Existing containers must be recreated before
using the v2 image; otherwise an old `unless-stopped` policy will cause a
restart loop.

1. Stop `plex-jav`.
2. Change the image to `ghcr.io/nxxxsooo/plex-jav:2.0.3`.
3. Set the restart policy to `no`.
4. Remove the `8501` port mapping and WebUI URL.
5. Apply/recreate the container from the updated template.
6. Move only completed downloads into the input directory, then start the
   container manually for each batch.

Rollback: restore `ghcr.io/nxxxsooo/plex-jav:1.5.0`, the previous port mapping,
and the previous restart policy, then recreate the container.

### Option 2: AI-Assisted Setup

Paste the contents of [`AGENTS.md`](AGENTS.md) into your AI coding agent and let it guide you through setup interactively.

Compatible tools:
- [OpenCode](https://github.com/opencode-ai/opencode) (recommended)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [Cursor](https://cursor.sh)
- Any AI coding assistant that supports markdown context

## Credits

- [JavSP](https://github.com/Yuukiy/JavSP) by Yuukiy (scraper source included in `scraper/`)
- [MetaTube](https://github.com/metatube-community/metatube-sdk-go) by metatube-community
- [JAVnfoMoviesImporter](https://github.com/ddd354/JAVnfoMoviesImporter.bundle) by ddd354 (modified for avatar support)
- [gfriends](https://github.com/gfriends/gfriends) — actress avatar database

## License

MIT
