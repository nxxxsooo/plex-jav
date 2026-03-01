# Plex JAV Solution

A complete JAV metadata solution for **Unraid + Plex** — automated scraping, NFO generation, and actress avatar fetching.

## What It Does

```
Drop JAV files → JavSP scrapes metadata → Plex reads NFO + fetches actress photos → fully organized library
```

- **JavSP** (Docker) scrapes metadata from multiple sources, generates NFO files and downloads artwork
- **JAVnfoMoviesImporter** (Plex plugin) reads NFO files and automatically fetches actress avatar photos from [gfriends](https://github.com/gfriends/gfriends)

## Setup

SSH into your Unraid and run:

```bash
curl -sSL https://raw.githubusercontent.com/nxxxsooo/plex-jav/master/setup.sh | bash
```

The script will ask a few questions about your environment (media paths, proxy, network), then automatically:

- Install the Plex plugin
- Download the actress avatar database
- Generate JavSP config
- Create an Unraid Docker template

## Credits

- [JavSP](https://github.com/Yuukiy/JavSP) by Yuukiy
- [JAVnfoMoviesImporter](https://github.com/ddd354/JAVnfoMoviesImporter.bundle) by ddd354 (modified for avatar support)
- [gfriends](https://github.com/gfriends/gfriends) — actress avatar database

## License

MIT
