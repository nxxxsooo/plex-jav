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
| MetaTube token (optional) | ______________ | `mysecrettoken` |
| DMM API ID (optional, legacy) | ______________ | `your_api_id` |
| DMM Affiliate ID (optional, legacy) | ______________ | `yourname-999` |

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
5. Create Unraid Docker template for JavSP (with embedded MetaTube server)

## After Setup

1. **Restart Plex** — Docker tab → plex → Restart
2. **Add plex-jav container** — Docker tab → Add Container → select `plex-jav` template
3. **Create Plex library** — Add a Movies library, set content folder to your `output/` path, agent to `JAVnfoMoviesImporter`
4. **Use it** — Move completed files into `input/`, then start the stopped `plex-jav` container
5. **Verify it** — Follow the container log; after one scan it stops automatically
6. **Scan Plex** — Exit code `0` means the JavSP batch completed successfully

## Workflow

```
completed file   →  manually start plex-jav  →  output/<actress>/<number>/
in input/               │                         movie.mp4
  movie.mp4             │                         movie.nfo (with plot)
                        │                         poster.jpg
                        │                         fanart.jpg
                        │                           ↓
                        │                    Plex scans library
                        │                           ↓
                        └─ MetaTube            NFO → metadata + plot
                          (job-local)         gfriends → actress avatars
```

MetaTube starts inside the container for each batch and stops when JavSP
finishes. It has no host port or WebUI. The container restart policy is `no`,
so an empty input or a failed scrape remains visibly stopped with a non-zero
exit code instead of looping.
