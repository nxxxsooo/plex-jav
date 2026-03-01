# Plex JAV Solution

A complete JAV metadata solution for **Unraid + Plex** — automated scraping, NFO generation, and actress avatar fetching.

## What It Does

```
Drop JAV files → JavSP scrapes metadata → Plex reads NFO + fetches actress photos → fully organized library
```

- **JavSP** (Docker) scrapes metadata from multiple sources, generates NFO files and downloads artwork
- **JAVnfoMoviesImporter** (Plex plugin) reads NFO files and automatically fetches actress avatar photos from [gfriends](https://github.com/gfriends/gfriends)
- Designed specifically for **Unraid** with proper permissions (nobody:users) and Docker conventions

## Setup

This project uses **AI-assisted setup**. Open this repo in your AI coding tool (OpenCode, Cursor, Claude Code, etc.) and ask:

> "Set up this Plex JAV solution on my Unraid server"

The AI will read `AGENTS.md`, ask about your environment (paths, proxy, network), and configure everything automatically.

## Credits

- [JavSP](https://github.com/Yuukiy/JavSP) by Yuukiy — metadata scraper
- [JAVnfoMoviesImporter](https://github.com/ddd354/JAVnfoMoviesImporter.bundle) by ddd354 — Plex NFO importer, modified for actress avatar support
- [gfriends](https://github.com/gfriends/gfriends) — actress avatar database
- [rishinyan/javsp](https://hub.docker.com/r/rishinyan/javsp) — Docker image

## License

MIT
