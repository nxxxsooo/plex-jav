# Plex JAV Solution

A complete JAV metadata solution for **Unraid + Plex** — automated scraping, NFO generation, plot/synopsis fetching, and actress avatar support.

## What It Does

```
Drop JAV files → JavSP scrapes metadata → Plex reads NFO + fetches actress photos → fully organized library
```

- **JavSP** (Docker) scrapes metadata from multiple sources, generates NFO files and downloads artwork
- **MetaTube** (Docker) provides plot/synopsis from 20+ sources including FANZA/DMM — no API keys needed
- **JAVnfoMoviesImporter** (Plex plugin) reads NFO files and automatically fetches actress avatar photos from [gfriends](https://github.com/gfriends/gfriends)

## Setup

### Option 1: Interactive Script

SSH into your Unraid and run:

```bash
curl -sSL https://raw.githubusercontent.com/nxxxsooo/plex-jav/master/setup.sh | bash
```

The script will ask a few questions about your environment (media paths, proxy, network), then automatically:

- Install the Plex plugin
- Download the actress avatar database
- Set up MetaTube (local metadata server for plot/synopsis)
- Generate JavSP config
- Create Unraid Docker templates

### Option 2: AI-Assisted Setup

Paste the contents of [`AGENTS.md`](AGENTS.md) into your AI coding agent and let it guide you through setup interactively.

Compatible tools:
- [OpenCode](https://github.com/opencode-ai/opencode) (recommended)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [Cursor](https://cursor.sh)
- Any AI coding assistant that supports markdown context

## Credits

- [JavSP](https://github.com/Yuukiy/JavSP) by Yuukiy (fork: [nxxxsooo/JavSP](https://github.com/nxxxsooo/JavSP))
- [MetaTube](https://github.com/metatube-community/metatube-sdk-go) by metatube-community
- [JAVnfoMoviesImporter](https://github.com/ddd354/JAVnfoMoviesImporter.bundle) by ddd354 (modified for avatar support)
- [gfriends](https://github.com/gfriends/gfriends) — actress avatar database

## License

MIT
