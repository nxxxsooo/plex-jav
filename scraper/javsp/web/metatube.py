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


def parse_data(movie: MovieInfo):
    """Parse movie data from a MetaTube server instance."""
    url = _get_metatube_url()
    if not url:
        raise MovieNotFoundError(__name__, movie.dvdid)

    # Search for the movie
    results = _search_movie(url, movie.dvdid)
    if not results:
        raise MovieNotFoundError(__name__, movie.dvdid)

    # Pick the best match (first result)
    best = results[0]
    provider = best.get("provider", "")
    mid = best.get("id", "")

    # Get full movie info with plot/summary
    info = _get_movie_info(url, provider, mid)
    if not info:
        raise MovieNotFoundError(__name__, movie.dvdid)

    # Map MetaTube fields to JavSP MovieInfo
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
