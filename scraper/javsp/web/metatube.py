"""Fetch metadata from a local MetaTube server API.

MetaTube (https://github.com/metatube-community/metatube-sdk-go) provides
a REST API with 20+ built-in data sources including FANZA/DMM. No API keys
required — the server handles all crawling internally.

Configuration:
    Set metatube_url in config.yml under network section, or via
    METATUBE_URL environment variable.
    Optionally set METATUBE_TOKEN for token-gated endpoints.
"""

import os
import re
import logging

import requests

from javsp.web.exceptions import *
from javsp.datatype import MovieInfo


logger = logging.getLogger(__name__)


def _get_metatube_url():
    """Get MetaTube server URL from config, environment, or default."""
    # 1. Config file
    try:
        from javsp.config import Cfg

        url = getattr(Cfg().network, "metatube_url", None)
        if url:
            return str(url).rstrip("/")
    except Exception:
        pass
    # 2. Environment variable
    env_url = os.environ.get("METATUBE_URL")
    if env_url:
        return env_url.rstrip("/")
    # 3. Default (embedded server in Docker)
    return "http://localhost:8080"


def _get_headers():
    """Build request headers with optional Bearer token."""
    headers = {"Accept": "application/json"}
    token = os.environ.get("METATUBE_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _dvdid_to_cid(dvdid: str) -> str:
    """Convert DVD ID to FANZA content ID.

    FANZA CIDs are lowercase prefix + zero-padded number (5 digits).
    Examples: SNOS-038 -> snos00038, IPZZ-703 -> ipzz00703
    """
    m = re.match(r"^([A-Za-z]+)-?(\d+)$", dvdid)
    if not m:
        return dvdid.lower().replace("-", "")
    return f"{m.group(1).lower()}{m.group(2).zfill(5)}"


def _try_fanza_direct(base_url, dvdid):
    """Try FANZA direct detail lookup via MetaTube, bypassing broken search.

    MetaTube's FANZA search endpoint is broken (returns empty), but the
    detail endpoint works perfectly when given a valid CID.
    """
    cid = _dvdid_to_cid(dvdid)
    info = _get_movie_info(base_url, "FANZA", cid)
    if info and info.get("summary"):
        logger.debug(f"FANZA direct hit for {dvdid} (cid={cid})")
        return info
    # Some titles use 3-digit padding (e.g., ABP-001 -> abp001)
    m = re.match(r"^([A-Za-z]+)-?(\d+)$", dvdid)
    if m:
        cid_short = f"{m.group(1).lower()}{m.group(2).zfill(3)}"
        if cid_short != cid:
            info = _get_movie_info(base_url, "FANZA", cid_short)
            if info and info.get("summary"):
                logger.debug(f"FANZA direct hit for {dvdid} (cid={cid_short}, 3-pad)")
                return info
    return None


def _search_movie(base_url, dvdid):
    """Search MetaTube for a movie by DVD ID.

    Tries fanza provider first (best for plot/synopsis), then falls back
    to a provider-agnostic search.
    """
    headers = _get_headers()
    search_params_list = [
        {"q": dvdid, "provider": "fanza"},
        {"q": dvdid},
    ]
    for params in search_params_list:
        try:
            resp = requests.get(
                f"{base_url}/v1/movies/search",
                params=params,
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    return data
        except requests.RequestException as e:
            logger.debug(f"MetaTube search error ({params}): {e}")
    return []


def _get_movie_info(base_url, provider, movie_id):
    """Get full movie info (including plot/summary) from MetaTube."""
    headers = _get_headers()
    try:
        resp = requests.get(
            f"{base_url}/v1/movies/{provider}/{movie_id}",
            params={"lazy": "false"},
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("data")
    except requests.RequestException as e:
        logger.debug(f"MetaTube movie info error: {e}")
    return None


def _apply_info(movie: MovieInfo, info: dict):
    """Map MetaTube info dict fields to JavSP MovieInfo attributes."""
    movie.title = info.get("title")
    movie.plot = info.get("summary")  # The key field — plot/synopsis
    movie.cover = info.get("big_cover_url") or info.get("cover_url")
    movie.actress = info.get("actors") or []
    movie.genre = info.get("genres") or []
    if info.get("score"):
        movie.score = str(info["score"])
    movie.producer = info.get("maker")
    movie.serial = info.get("series")
    movie.director = info.get("director")
    if info.get("runtime"):
        movie.duration = str(info["runtime"])
    release_date = info.get("release_date")
    if release_date:
        movie.publish_date = str(release_date)
    movie.preview_pics = info.get("preview_images") or []
    movie.preview_video = info.get("preview_video_url")
    movie.url = info.get("homepage")


def parse_data(movie: MovieInfo):
    """Parse movie data from a MetaTube server instance.

    Strategy (optimized for plot/synopsis retrieval):
      1. Try FANZA direct detail first — bypasses broken FANZA search and
         returns full data including plot/summary for most titles.
      2. Fall back to generic MetaTube search → detail for titles FANZA
         doesn't have (region-blocked, etc.).
      3. If search-based result lacks plot, try FANZA direct as supplement.
    """
    url = _get_metatube_url()
    if not url:
        raise MovieNotFoundError(__name__, movie.dvdid)

    # Strategy 1: Try FANZA direct detail (best source for plot)
    fanza_info = _try_fanza_direct(url, movie.dvdid)
    if fanza_info:
        _apply_info(movie, fanza_info)
        return

    # Strategy 2: Fall back to MetaTube search
    results = _search_movie(url, movie.dvdid)
    if not results:
        raise MovieNotFoundError(__name__, movie.dvdid)

    best = results[0]
    provider = best.get("provider", "")
    mid = best.get("id", "")

    info = _get_movie_info(url, provider, mid)
    if not info:
        raise MovieNotFoundError(__name__, movie.dvdid)

    # Strategy 3: If search result has no plot, try FANZA direct to supplement
    if not info.get("summary"):
        fanza_info = _try_fanza_direct(url, movie.dvdid)
        if fanza_info and fanza_info.get("summary"):
            # Use FANZA for plot but keep other data from original provider
            info["summary"] = fanza_info["summary"]
            logger.debug(f"Supplemented plot from FANZA for {movie.dvdid}")

    _apply_info(movie, info)


if __name__ == "__main__":
    import pretty_errors

    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo("SSIS-001")
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
