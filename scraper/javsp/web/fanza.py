"""Scrape data from FANZA (DMM) via Affiliate API with web scraping fallback"""

import os
import re
import sys
import json
import logging
from typing import Dict, List, Tuple, Optional


from javsp.web.base import Request, resp2html
from javsp.web.exceptions import *
from javsp.config import Cfg
from javsp.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = "https://www.dmm.co.jp"
api_url = "https://api.dmm.com/affiliate/v3/ItemList"

# Web scraping request (cookies for age check bypass)
request = Request()
request.cookies = {"age_check_done": "1"}
request.headers["Accept-Language"] = "ja,en-US;q=0.9"

# API request (no cookies needed)
api_request = Request()
api_request.headers["Accept"] = "application/json"


# ============================================================================
# DMM Affiliate API
# ============================================================================


def _get_api_credentials() -> Optional[Tuple[str, str]]:
    """Get DMM API credentials from config. Returns (api_id, affiliate_id) or None."""
    cfg = Cfg()
    api_id = getattr(cfg.network, "dmm_api_id", None)
    affiliate_id = getattr(cfg.network, "dmm_affiliate_id", None)
    if api_id and affiliate_id:
        return (str(api_id), str(affiliate_id))
    # Also check environment variables as fallback
    api_id = os.environ.get("DMM_API_ID")
    affiliate_id = os.environ.get("DMM_AFFILIATE_ID")
    if api_id and affiliate_id:
        return (api_id, affiliate_id)
    return None


def _normalize_cid_for_api(cid: str) -> str:
    """Normalize a CID for DMM API search.

    DMM CIDs in URLs use underscores but API may need different format.
    e.g., 'sone00555' or 'sone_555' -> try both formats
    """
    return cid.lower().replace("-", "")


def _search_by_cid(api_id: str, affiliate_id: str, cid: str) -> Optional[dict]:
    """Search DMM API by content ID. Returns the first matching item or None."""
    normalized_cid = _normalize_cid_for_api(cid)
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "cid": normalized_cid,
        "hits": "1",
        "output": "json",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{api_url}?{query}"

    try:
        r = api_request.get(url, delay_raise=True)
        if r.status_code != 200:
            logger.debug(f"DMM API returned status {r.status_code} for cid={cid}")
            return None

        data = r.json()
        result = data.get("result", {})
        items = result.get("items", [])
        if items:
            return items[0]

        # If cid search returned nothing, try keyword search with the DVD ID
        logger.debug(
            f"DMM API cid search found nothing for {normalized_cid}, trying keyword search"
        )
        return _search_by_keyword(api_id, affiliate_id, cid)
    except Exception as e:
        logger.debug(f"DMM API search failed for cid={cid}: {e}")
        return None


def _search_by_keyword(api_id: str, affiliate_id: str, keyword: str) -> Optional[dict]:
    """Search DMM API by keyword. Returns the first matching item or None."""
    import urllib.parse

    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "keyword": urllib.parse.quote(keyword),
        "hits": "5",
        "output": "json",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{api_url}?{query}"

    try:
        r = api_request.get(url, delay_raise=True)
        if r.status_code != 200:
            return None

        data = r.json()
        result = data.get("result", {})
        items = result.get("items", [])
        if not items:
            return None

        # Try to match by content_id
        target_cid = _normalize_cid_for_api(keyword)
        for item in items:
            item_cid = item.get("content_id", "").lower()
            if item_cid == target_cid:
                return item

        # Return first result if no exact match
        return items[0]
    except Exception as e:
        logger.debug(f"DMM API keyword search failed for {keyword}: {e}")
        return None


def _parse_api_item(movie: MovieInfo, item: dict):
    """Parse a DMM API item response into MovieInfo fields."""
    # Title
    title = item.get("title", "")
    if title:
        movie.title = title

    # Plot / Description
    # DMM API may return description in 'comment' or 'description' field
    plot = item.get("comment", "") or item.get("description", "")
    if plot:
        movie.plot = plot.strip()

    # Cover image
    image_url = item.get("imageURL", {})
    # Prefer large image
    cover = image_url.get("large", "") or image_url.get("small", "")
    if cover:
        movie.cover = cover

    # Content ID
    content_id = item.get("content_id", "")
    if content_id:
        movie.cid = content_id

    # URL
    affiliate_url = item.get("affiliateURL", "") or item.get("URL", "")
    if affiliate_url:
        movie.url = affiliate_url

    # Publish date
    date = item.get("date", "")  # Format: "2024-01-15 10:00:00"
    if date:
        movie.publish_date = date.split(" ")[0]  # Keep only date part

    # Duration (in minutes)
    # DMM API may return volume (duration) as a string
    volume = item.get("volume", "")
    if volume:
        match = re.search(r"\d+", str(volume))
        if match:
            movie.duration = match.group(0)

    # Review / Score
    review = item.get("review", {})
    if isinstance(review, dict):
        average = review.get("average", "")
        if average:
            try:
                score = float(average) * 2  # Convert 5-point to 10-point scale
                movie.score = f"{score:.2f}"
            except (ValueError, TypeError):
                pass

    # Item info (actress, genre, director, series, maker)
    iteminfo = item.get("iteminfo", {})

    # Actress
    actress_list = iteminfo.get("actress", [])
    if actress_list:
        movie.actress = [a.get("name", "") for a in actress_list if a.get("name")]

    # Director
    director_list = iteminfo.get("director", [])
    if director_list:
        movie.director = director_list[0].get("name", "")

    # Series
    series_list = iteminfo.get("series", [])
    if series_list:
        movie.serial = series_list[0].get("name", "")

    # Maker (producer)
    maker_list = iteminfo.get("maker", [])
    if maker_list:
        movie.producer = maker_list[0].get("name", "")

    # Label (publisher)
    label_list = iteminfo.get("label", [])
    if label_list:
        movie.publisher = label_list[0].get("name", "")

    # Genre
    genre_list = iteminfo.get("genre", [])
    if genre_list:
        movie.genre = [g.get("name", "") for g in genre_list if g.get("name")]
        movie.genre_id = [str(g.get("id", "")) for g in genre_list if g.get("id")]

    # Preview images (sample images)
    sample_images = item.get("sampleImageURL", {})
    sample_s = sample_images.get("sample_s", {})
    if isinstance(sample_s, dict):
        pics = sample_s.get("image", [])
        if pics:
            movie.preview_pics = pics

    # Preview video
    sample_movie = item.get("sampleMovieURL", {})
    if isinstance(sample_movie, dict):
        # Prefer highest quality
        for quality in ["size_720_480", "size_644_414", "size_560_360", "size_476_306"]:
            video_url = sample_movie.get(quality, "")
            if video_url:
                movie.preview_video = video_url
                break

    # FANZA content is always censored
    movie.uncensored = False


def _parse_via_api(movie: MovieInfo) -> bool:
    """Try to parse movie data via DMM Affiliate API. Returns True on success."""
    credentials = _get_api_credentials()
    if not credentials:
        logger.debug("DMM API credentials not configured, skipping API scraping")
        return False

    api_id, affiliate_id = credentials
    item = _search_by_cid(api_id, affiliate_id, movie.cid)
    if not item:
        logger.debug(f"DMM API: no results for cid={movie.cid}")
        return False

    _parse_api_item(movie, item)
    logger.debug(f"DMM API: successfully parsed data for cid={movie.cid}")
    return True


# ============================================================================
# Web scraping fallback (legacy - may not work due to DMM SPA migration)
# ============================================================================

_PRODUCT_PRIORITY = {"digital": 10, "mono": 5, "monthly": 2, "rental": 1}
_TYPE_PRIORITY = {
    "videoa": 10,
    "anime": 8,
    "nikkatsu": 6,
    "doujin": 4,
    "dvd": 3,
    "ppr": 2,
    "paradisetv": 1,
}


def sort_search_result(result: List[Dict]):
    """Sort search results by product and type priority"""
    scores = {
        i["url"]: (
            _PRODUCT_PRIORITY.get(i["product"], 0),
            _TYPE_PRIORITY.get(i["type"], 0),
        )
        for i in result
    }
    sorted_result = sorted(result, key=lambda x: scores[x["url"]], reverse=True)
    return sorted_result


def get_urls_of_cid(cid: str) -> List[Dict]:
    """Search for possible movie URLs by CID"""
    r = request.get(
        f"https://www.dmm.co.jp/search/?redirect=1&enc=UTF-8&category=&searchstr={cid}&commit.x=0&commit.y=0"
    )
    if r.status_code == 404:
        raise MovieNotFoundError(__name__, cid)
    r.raise_for_status()
    html = resp2html_wrapper(r)
    result = html.xpath("//ul[@id='list']/li/div/p/a/@href")
    parsed_result = {}
    for url in result:
        items = url.split("/")
        type_, cid_found = None, None
        for i, part in enumerate(items):
            if part == "-":
                product, type_ = items[i - 2], items[i - 1]
            elif part.startswith("cid="):
                cid_found = part[4:]
                new_url = "/".join(i for i in items if not i.startswith("?")) + "/"
                parsed_result.setdefault(cid_found, []).append(
                    {"product": product, "type": type_, "url": new_url}
                )
                break
    if cid not in parsed_result:
        if len(result) > 0:
            logger.debug(f"Unknown URL in search result: " + ", ".join(result))
        raise MovieNotFoundError(__name__, cid)
    sorted_result = sort_search_result(parsed_result[cid])
    return sorted_result


def resp2html_wrapper(resp):
    html = resp2html(resp)
    if "not available in your region" in html.text_content():
        raise SiteBlocked(
            "FANZA is not available from your region. Check your network and proxy settings."
        )
    elif "/login/" in resp.url:
        raise SiteBlocked("FANZA requires login from your IP. Try using a Japanese IP.")
    return html


def _parse_via_web(movie: MovieInfo) -> bool:
    """Try to parse movie data via web scraping. Returns True on success.

    NOTE: DMM has migrated to Next.js SPA (React Server Components).
    This method may not work for newer pages but is kept as fallback
    for older content that may still be server-rendered.
    """
    try:
        default_url = f"{base_url}/digital/videoa/-/detail/=/cid={movie.cid}/"
        r0 = request.get(default_url, delay_raise=True)
        if r0.status_code == 404:
            urls = get_urls_of_cid(movie.cid)
            for d in urls:
                func_name = f"parse_{d['type']}_page"
                if func_name in globals():
                    parse_func = globals()[func_name]
                else:
                    logger.debug(f"Unknown fanza page type: {d['type']}: {d['url']}")
                    continue
                r = request.get(d["url"])
                html = resp2html_wrapper(r)
                try:
                    parse_func(movie, html)
                    movie.url = d["url"]
                    return True
                except:
                    logger.debug(f"Failed to parse {d['url']}", exc_info=True)
                    if d is urls[-1]:
                        return False
        else:
            html = resp2html_wrapper(r0)
            parse_videoa_page(movie, html)
            movie.url = default_url
            return True
    except (SiteBlocked, MovieNotFoundError):
        raise
    except Exception as e:
        logger.debug(f"Web scraping failed for cid={movie.cid}: {e}")
        return False
    return False


def parse_videoa_page(movie: MovieInfo, html):
    """Parse videoa page layout"""
    title = html.xpath("//div[@class='hreview']/h1/text()")[0]
    container = html.xpath("//table[@class='mg-b12']/tr/td")[0]
    cover = container.xpath("//div[@id='sample-video']/a/@href")[0]
    date_tag = container.xpath(
        "//td[text()='配信開始日：']/following-sibling::td/text()"
    )
    if date_tag:
        movie.publish_date = date_tag[0].strip().replace("/", "-")
    duration_str = container.xpath(
        "//td[text()='収録時間：']/following-sibling::td/text()"
    )[0].strip()
    match = re.search(r"\d+", duration_str)
    if match:
        movie.duration = match.group(0)
    actress = container.xpath("//span[@id='performer']/a/text()")
    director_tag = container.xpath(
        "//td[text()='監督：']/following-sibling::td/a/text()"
    )
    if director_tag:
        movie.director = director_tag[0].strip()
    serial_tag = container.xpath(
        "//td[text()='シリーズ：']/following-sibling::td/a/text()"
    )
    if serial_tag:
        movie.serial = serial_tag[0].strip()
    producer_tag = container.xpath(
        "//td[text()='メーカー：']/following-sibling::td/a/text()"
    )
    if producer_tag:
        movie.producer = producer_tag[0].strip()
    genre_tags = container.xpath(
        "//td[text()='ジャンル：']/following-sibling::td/a[contains(@href,'?keyword=') or contains(@href,'article=keyword')]"
    )
    genre, genre_id = [], []
    for tag in genre_tags:
        genre.append(tag.text.strip())
        genre_id.append(tag.get("href").split("=")[-1].strip("/"))
    cid = container.xpath("//td[text()='品番：']/following-sibling::td/text()")[
        0
    ].strip()
    plot_tags = container.xpath("//div[contains(@class, 'mg-b20 lh4')]/text()")
    plot = plot_tags[0].strip() if plot_tags else ""
    preview_pics = container.xpath("//a[@name='sample-image']/img/@src")
    score_tag = container.xpath("//p[@class='d-review__average']/strong/text()")
    if score_tag:
        match = re.search(r"\d+", score_tag[0].strip())
        if match:
            score = float(match.group()) * 2
            movie.score = f"{score:.2f}"
    else:
        score_img_tags = container.xpath(
            "//td[text()='平均評価：']/following-sibling::td/img/@src"
        )
        if score_img_tags:
            movie.score = int(score_img_tags[0].split("/")[-1].split(".")[0])

    if Cfg().crawler.hardworking:
        # Preview video is dynamically loaded
        video_url = f"{base_url}/service/digitalapi/-/html5_player/=/cid={movie.cid}"
        try:
            html2 = request.get_html(video_url)
            script = html2.xpath(
                "//script[contains(text(),'getElementById(\"dmmplayer\")')]/text()"
            )[0].strip()
            match = re.search(r"\{.*\}", script)
            data = json.loads(match.group())
            video_url = data.get("src")
            if video_url and video_url.startswith("//"):
                video_url = "https:" + video_url
            movie.preview_video = video_url
        except Exception as e:
            logger.debug("Failed to parse video URL: " + repr(e))

    movie.cid = cid
    movie.title = title
    movie.cover = cover
    movie.actress = actress
    movie.genre = genre
    movie.genre_id = genre_id
    if plot:
        movie.plot = plot
    movie.preview_pics = preview_pics
    movie.uncensored = False


def parse_anime_page(movie: MovieInfo, html):
    """Parse anime page layout"""
    title = html.xpath("//h1[@id='title']/text()")[0]
    container = html.xpath("//table[@class='mg-b12']/tr/td")[0]
    cover = container.xpath("//img[@name='package-image']/@src")[0]
    date_str = container.xpath("//td[text()='発売日：']/following-sibling::td/text()")[
        0
    ].strip()
    publish_date = date_str.replace("/", "-")
    duration_tag = container.xpath(
        "//td[text()='収録時間：']/following-sibling::td/text()"
    )
    if duration_tag:
        movie.duration = duration_tag[0].strip().replace("分", "")
    serial_tag = container.xpath(
        "//td[text()='シリーズ：']/following-sibling::td/a/text()"
    )
    if serial_tag:
        movie.serial = serial_tag[0].strip()
    producer_tag = container.xpath(
        "//td[text()='メーカー：']/following-sibling::td/a/text()"
    )
    if producer_tag:
        movie.producer = producer_tag[0].strip()
    genre_tags = container.xpath(
        "//td[text()='ジャンル：']/following-sibling::td/a[contains(@href,'article=keyword')]"
    )
    genre, genre_id = [], []
    for tag in genre_tags:
        genre.append(tag.text.strip())
        genre_id.append(tag.get("href").split("=")[-1].strip("/"))
    cid = container.xpath("//td[text()='品番：']/following-sibling::td/text()")[
        0
    ].strip()
    plot = container.xpath("//div[@class='mg-b20 lh4']/p")[0].text_content().strip()
    preview_pics = container.xpath("//a[@name='sample-image']/img/@data-lazy")
    score_img = container.xpath(
        "//td[text()='平均評価：']/following-sibling::td/img/@src"
    )[0]
    score = int(score_img.split("/")[-1].split(".")[0])

    movie.cid = cid
    movie.title = title
    movie.cover = cover
    movie.publish_date = publish_date
    movie.genre = genre
    movie.genre_id = genre_id
    movie.plot = plot
    movie.score = f"{score / 5:.2f}"
    movie.preview_pics = preview_pics
    movie.uncensored = False


parse_ppr_page = parse_videoa_page
parse_nikkatsu_page = parse_videoa_page
parse_doujin_page = parse_anime_page


# ============================================================================
# Main entry point
# ============================================================================


def parse_data(movie: MovieInfo):
    """Parse movie data from FANZA/DMM.

    Strategy:
    1. Try DMM Affiliate API first (reliable, structured data, requires credentials)
    2. Fall back to web scraping (may fail due to DMM's SPA migration)
    3. If both fail, raise MovieNotFoundError
    """
    # Try API first
    if _parse_via_api(movie):
        return

    # Fall back to web scraping
    logger.debug(f"Falling back to web scraping for cid={movie.cid}")
    if _parse_via_web(movie):
        return

    # Both methods failed
    raise MovieNotFoundError(__name__, movie.cid)


if __name__ == "__main__":
    import pretty_errors

    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo(cid="d_aisoft3356")
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
