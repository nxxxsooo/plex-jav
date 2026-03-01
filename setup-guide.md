# Plex JAV Solution — Setup Guide

Fill in your values below, then run the setup command.

## Your Environment

| Setting | Your Value | Example |
|---------|-----------|---------|
| Media path | ______________ | `/mnt/user/media/jav` |
| Plex appdata | ______________ | `/mnt/user/appdata/plex` |
| JavSP appdata | ______________ | `/mnt/user/appdata/javsp` |
| Need proxy? | yes / no | `no` |
| Proxy URL | ______________ | `http://192.168.1.1:7890` |
| Docker network | ______________ | `bridge` |
| JavSP WebUI port | ______________ | `8501` |

## Run

SSH into Unraid and run:

```bash
curl -sSL https://raw.githubusercontent.com/nxxxsooo/plex-jav/master/setup.sh | bash
```

The script will ask the questions above interactively, then:

1. Create media folders (`input/` and `output/`)
2. Install the Plex plugin (JAVnfoMoviesImporter with actress avatar support)
3. Download actress avatar database (~4.5MB)
4. Generate JavSP config
5. Create Unraid Docker template for JavSP container

## After Setup

1. **Restart Plex** — Docker tab → plex → Restart
2. **Add JavSP container** — Docker tab → Add Container → select `javsp` template
3. **Create Plex library** — Add a Movies library, set content folder to your `output/` path, agent to `JAVnfoMoviesImporter`
4. **Use it** — Drop files into `input/`, run JavSP (WebUI), scan Plex library

## Workflow

```
input/           →  JavSP scrapes  →  output/<actress>/<number>/
  movie.mp4                             movie.mp4
                                        movie.nfo
                                        poster.jpg
                                        fanart.jpg
                                          ↓
                                    Plex scans library
                                          ↓
                                    NFO → metadata
                                    gfriends → actress avatars
```
