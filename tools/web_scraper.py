"""Web scraping tools — fetch and extract content from web pages."""
from __future__ import annotations

import re
import urllib.request
import urllib.parse
import json
import csv
import io
import hashlib
import difflib
from datetime import datetime
import xml.etree.ElementTree as ET
import os
from pathlib import Path
import concurrent.futures
import requests

from tools import tool


@tool(
    name="fetch_page",
    description="Fetch a web page and extract its text content (strips HTML).",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return (default 3000)",
            },
        },
        "required": ["url"],
    },
)
def fetch_page(url: str, max_chars: int = 3000) -> str:
    import time as _time
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        t0 = _time.perf_counter()
        with urllib.request.urlopen(req, timeout=15) as resp:
            elapsed = _time.perf_counter() - t0
            html = resp.read().decode("utf-8", errors="replace")

            # Strip HTML
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            status = resp.status
            content_type = resp.headers.get("Content-Type", "")

            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n... ({len(text) - max_chars} more chars)"

            return (
                f"GET {url} → {status} ({elapsed*1000:.0f}ms)\n"
                f"Content-Type: {content_type}\n\n{text[:max_chars+200]}"
            )
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL unreachable: {e.reason}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="fetch_page_links",
    description="Extract all links from a web page.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to extract links from",
            },
        },
        "required": ["url"],
    },
)
def fetch_page_links(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")

        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Extract href links
        links = re.findall(r'href=["\']([^"\']+)["\']', html)

        # Filter to unique
        seen = set()
        unique = []
        for l in links:
            if l not in seen and not l.startswith(("javascript:", "mailto:")):
                seen.add(l)
                unique.append(l)

        if not unique:
            return f"No links found on {url}"

        lines = [f"Links on {url} ({len(unique)}):"]
        for l in unique[:50]:
            lines.append(f"  {l}")
        if len(unique) > 50:
            lines.append(f"  ...and {len(unique)-50} more")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="fetch_page_images",
    description="Extract all image URLs from a web page.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to extract images from",
            },
        },
        "required": ["url"],
    },
)
def fetch_page_images(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")

        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Extract image sources
        images = re.findall(r'src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp|svg|avif))["\']', html, re.IGNORECASE)
        images += re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)

        seen = set()
        unique = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique.append(img)

        if not unique:
            return f"No images found on {url}"

        lines = [f"Images on {url} ({len(unique)}):"]
        for img in unique[:30]:
            lines.append(f"  {img}")
        if len(unique) > 30:
            lines.append(f"  ...and {len(unique)-30} more")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="scrape_structured_data",
    description="Extract tables, lists, and metadata (OpenGraph, JSON-LD) from a webpage's HTML.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to scrape structured data from"},
            "target_type": {
                "type": "string",
                "description": "What to extract: 'table', 'list', 'metadata', or 'all'",
                "enum": ["table", "list", "metadata", "all"],
                "default": "all",
            },
            "output_format": {
                "type": "string",
                "description": "Format for tables/lists: 'json' or 'csv'",
                "enum": ["json", "csv"],
                "default": "json",
            },
        },
        "required": ["url"],
    },
)
def scrape_structured_data(url: str, target_type: str = "all", output_format: str = "json") -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from lxml import html
    except ImportError:
        return "error: lxml package is not installed."

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        tree = html.fromstring(resp.content)
    except Exception as e:
        return f"error fetching or parsing page: {e}"

    result_data = {}

    # 1. Metadata extraction
    if target_type in ("metadata", "all"):
        meta_info = {}
        title_el = tree.xpath("//title/text()")
        meta_info["title"] = title_el[0].strip() if title_el else ""
        for m in tree.xpath("//meta"):
            name = m.get("name") or m.get("property")
            content = m.get("content")
            if name and content:
                meta_info[name] = content.strip()
        json_ld = []
        for script in tree.xpath("//script[@type='application/ld+json']/text()"):
            try:
                json_ld.append(json.loads(script.strip()))
            except Exception:
                pass
        if json_ld:
            meta_info["json_ld"] = json_ld
        result_data["metadata"] = meta_info

    # 2. Tables extraction
    if target_type in ("table", "all"):
        extracted_tables = []
        for idx, table_el in enumerate(tree.xpath("//table")):
            rows = []
            header_tr = table_el.xpath(".//tr[th]")
            headers = []
            if header_tr:
                headers = [th.text_content().strip() for th in header_tr[0].xpath(".//th")]
            
            for tr in table_el.xpath(".//tr"):
                if header_tr and tr == header_tr[0]:
                    continue
                cells = [td.text_content().strip() for td in tr.xpath(".//td | .//th")]
                if cells:
                    rows.append(cells)
            
            if rows:
                if not headers:
                    headers = [f"Column {i+1}" for i in range(len(rows[0]))]
                extracted_tables.append({
                    "table_index": idx + 1,
                    "headers": headers,
                    "rows": rows,
                })
        result_data["tables"] = extracted_tables

    # 3. Lists extraction
    if target_type in ("list", "all"):
        extracted_lists = []
        for idx, list_el in enumerate(tree.xpath("//ul | //ol")):
            items = [li.text_content().strip() for li in list_el.xpath(".//li")]
            items = [item for item in items if item]
            if items:
                extracted_lists.append({
                    "list_index": idx + 1,
                    "type": list_el.tag,
                    "items": items[:50],
                })
        result_data["lists"] = extracted_lists

    output_lines = []
    
    if "metadata" in result_data:
        meta = result_data["metadata"]
        output_lines.append("=== Webpage Metadata ===")
        output_lines.append(f"Title: {meta.get('title')}")
        output_lines.append(f"Description: {meta.get('description') or meta.get('og:description') or 'N/A'}")
        if "json_ld" in meta:
            output_lines.append(f"JSON-LD Schemas found: {len(meta['json_ld'])}")
        output_lines.append("")

    if "tables" in result_data:
        output_lines.append(f"=== Tables Found ({len(result_data['tables'])}) ===")
        for tbl in result_data["tables"]:
            output_lines.append(f"Table #{tbl['table_index']}:")
            if output_format == "json":
                dict_rows = []
                for r in tbl["rows"]:
                    dict_rows.append(dict(zip(tbl["headers"], r)))
                output_lines.append(json.dumps(dict_rows[:10], indent=2))
                if len(tbl["rows"]) > 10:
                    output_lines.append(f"... and {len(tbl['rows']) - 10} more rows")
            else:
                f = io.StringIO()
                writer = csv.writer(f)
                writer.writerow(tbl["headers"])
                writer.writerows(tbl["rows"][:20])
                output_lines.append(f.getvalue().strip())
                if len(tbl["rows"]) > 20:
                    output_lines.append(f"... and {len(tbl['rows']) - 20} more rows")
            output_lines.append("")

    if "lists" in result_data:
        output_lines.append(f"=== Lists Found ({len(result_data['lists'])}) ===")
        for lst in result_data["lists"]:
            output_lines.append(f"List #{lst['list_index']} ({lst['type']}):")
            if output_format == "json":
                output_lines.append(json.dumps(lst["items"][:10], indent=2))
            else:
                output_lines.append(", ".join(lst["items"][:20]))
            if len(lst["items"]) > 10:
                output_lines.append(f"... and {len(lst['items']) - 10} more items")
            output_lines.append("")

    return "\n".join(output_lines).strip()


@tool(
    name="monitor_webpage_changes",
    description="Check if a URL's content has changed since the last check. Saves state in data/webpage_monitor.json.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to monitor"},
            "reset": {"type": "boolean", "description": "If true, reset the baseline to the current webpage state without alerting.", "default": False},
        },
        "required": ["url"],
    },
)
def monitor_webpage_changes(url: str, reset: bool = False) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from lxml import html
    except ImportError:
        return "error: lxml package is not installed."

    def get_page_text(html_content: bytes) -> str:
        tree = html.fromstring(html_content)
        for bad in tree.xpath("//script | //style | //noscript"):
            bad.getparent().remove(bad)
        text = tree.text_content()
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join([l for l in lines if l])

    db_path = Path("data/webpage_monitor.json")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = {}
    if db_path.exists():
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            pass

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        current_text = get_page_text(resp.content)
    except Exception as e:
        return f"error fetching webpage for monitoring: {e}"

    current_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
    timestamp = datetime.now().isoformat()

    entry = db.get(url)

    if reset or not entry:
        db[url] = {
            "hash": current_hash,
            "text": current_text,
            "last_checked": timestamp,
            "last_changed": timestamp,
        }
        try:
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)
        except Exception as e:
            return f"Baseline established, but failed to save database: {e}"
        
        if reset:
            return f"Baseline monitoring reset for {url}."
        return f"Established initial baseline for {url}. We will alert you on future changes."

    old_hash = entry.get("hash")
    old_text = entry.get("text", "")

    if current_hash == old_hash:
        entry["last_checked"] = timestamp
        try:
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)
        except Exception:
            pass
        return f"No changes detected for {url}.\nLast checked: {timestamp}\nLast changed: {entry.get('last_changed')}"

    old_lines = old_text.splitlines()
    new_lines = current_text.splitlines()
    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="baseline", tofile="current",
        lineterm="", n=2
    ))

    entry["hash"] = current_hash
    entry["text"] = current_text
    entry["last_checked"] = timestamp
    entry["last_changed"] = timestamp
    db[url] = entry

    try:
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception:
        pass

    diff_str = "\n".join(diff[:25])
    if len(diff) > 25:
        diff_str += f"\n... and {len(diff) - 25} more lines of changes"

    return (
        f"⚠️ WEBPAGE CHANGED! ⚠️\n"
        f"URL: {url}\n"
        f"Time of Change: {timestamp}\n\n"
        f"Diff preview:\n```diff\n{diff_str}\n```"
    )


@tool(
    name="archive_webpage",
    description="Save a webpage to the Wayback Machine and/or save a local HTML copy.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to archive"},
            "mode": {
                "type": "string",
                "description": "Archive target: 'wayback', 'local', or 'both'",
                "enum": ["wayback", "local", "both"],
                "default": "both",
            },
        },
        "required": ["url"],
    },
)
def archive_webpage(url: str, mode: str = "both") -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    results = []

    # 1. Local archive
    if mode in ("local", "both"):
        local_dir = Path("data/archives")
        local_dir.mkdir(parents=True, exist_ok=True)
        
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace(":", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{timestamp}.html"
        file_path = local_dir / filename

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(resp.content)
            results.append(f"Saved local archive to {file_path.absolute()}")
        except Exception as e:
            results.append(f"Failed to save local archive: {e}")

    # 2. Wayback Machine
    if mode in ("wayback", "both"):
        wayback_save_url = f"https://web.archive.org/save/{url}"
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.post(wayback_save_url, headers=headers, timeout=20)
            if resp.status_code in (200, 301, 302):
                results.append("Submitted to Internet Archive (Wayback Machine) successfully.")
            else:
                results.append(f"Internet Archive submission returned status {resp.status_code} (queued or requires verification).")
        except Exception as e:
            results.append(f"Failed to submit to Internet Archive: {e}")

    return "\n".join(results)


@tool(
    name="download_media",
    description="Download media (images, audio, or video files) from a URL or scrape a webpage for media assets to download.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Webpage URL to scrape for media, or a direct file URL to download."},
            "media_type": {
                "type": "string",
                "description": "Media type to download: 'image', 'audio', 'video', or 'all'",
                "enum": ["image", "audio", "video", "all"],
                "default": "all",
            },
            "output_dir": {"type": "string", "description": "Optional custom directory to save files. Defaults to data/downloads/."},
            "max_files": {"type": "integer", "description": "Maximum number of files to download (default 10, max 30)", "default": 10},
            "rate_limit_seconds": {"type": "number", "description": "Delay in seconds between downloads to avoid rate limits (default 1.0)", "default": 1.0},
        },
        "required": ["url"],
    },
)
def download_media(
    url: str,
    media_type: str = "all",
    output_dir: str | None = None,
    max_files: int = 10,
    rate_limit_seconds: float = 1.0,
) -> str:
    import time
    
    try:
        from lxml import html
    except ImportError:
        return "error: lxml package is not installed."

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    max_files = max(1, min(max_files, 30))
    rate_limit_seconds = max(0.1, min(rate_limit_seconds, 10.0))

    out_path = Path(output_dir) if output_dir else Path("data/downloads")
    out_path.mkdir(parents=True, exist_ok=True)

    parsed_url = urllib.parse.urlparse(url)
    path_lower = parsed_url.path.lower()
    
    media_exts = {
        "image": (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"),
        "audio": (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"),
        "video": (".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"),
    }

    is_direct = False
    target_exts = []
    if media_type == "all":
        target_exts = media_exts["image"] + media_exts["audio"] + media_exts["video"]
    else:
        target_exts = media_exts[media_type]

    if path_lower.endswith(target_exts):
        is_direct = True

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def sanitize_filename(name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    def download_file(file_url: str) -> str:
        try:
            parsed = urllib.parse.urlparse(file_url)
            filename = os.path.basename(parsed.path)
            if not filename or not filename.strip():
                filename = "file_" + hashlib.md5(file_url.encode()).hexdigest()[:8]
            
            filename = sanitize_filename(filename)
            file_dest = out_path / filename

            counter = 1
            while file_dest.exists():
                name_part, ext_part = os.path.splitext(filename)
                file_dest = out_path / f"{name_part}_{counter}{ext_part}"
                counter += 1

            r = requests.get(file_url, headers=headers, stream=True, timeout=15)
            r.raise_for_status()
            with open(file_dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return f"Downloaded: {filename} ({file_dest.stat().st_size} bytes)"
        except Exception as e:
            return f"Failed {file_url}: {e}"

    if is_direct:
        return download_file(url)

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        tree = html.fromstring(resp.content)
    except Exception as e:
        return f"Error loading webpage: {e}"

    candidate_urls = set()

    if media_type in ("image", "all"):
        for img in tree.xpath("//img[@src]"):
            candidate_urls.add(img.get("src"))
        for source in tree.xpath("//source[@srcset]"):
            src = source.get("srcset").split(",")[0].strip().split(" ")[0]
            if src:
                candidate_urls.add(src)

    if media_type in ("audio", "all"):
        for aud in tree.xpath("//audio[@src]"):
            candidate_urls.add(aud.get("src"))
        for aud_src in tree.xpath("//audio/source[@src]"):
            candidate_urls.add(aud_src.get("src"))

    if media_type in ("video", "all"):
        for vid in tree.xpath("//video[@src]"):
            candidate_urls.add(vid.get("src"))
        for vid_src in tree.xpath("//video/source[@src]"):
            candidate_urls.add(vid_src.get("src"))

    download_list = []
    for raw_url in candidate_urls:
        abs_url = urllib.parse.urljoin(url, raw_url)
        parsed_abs = urllib.parse.urlparse(abs_url)
        abs_path_lower = parsed_abs.path.lower()
        if abs_path_lower.endswith(target_exts):
            download_list.append(abs_url)

    if not download_list:
        return f"No matching {media_type} media links found on page {url}"

    download_list = download_list[:max_files]
    results = [f"Found {len(download_list)} media files to download:"]

    for idx, d_url in enumerate(download_list):
        if idx > 0 and rate_limit_seconds > 0:
            time.sleep(rate_limit_seconds)
        res = download_file(d_url)
        results.append(f"  {res}")

    return "\n".join(results)


@tool(
    name="social_media_search",
    description="Search real-time social media discussions on Hacker News, Reddit, Twitter/X, and LinkedIn.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword or phrase"},
            "network": {
                "type": "string",
                "description": "Limit search to: 'hn', 'reddit', 'twitter', 'linkedin', or 'all'",
                "enum": ["hn", "reddit", "twitter", "linkedin", "all"],
                "default": "all",
            },
            "max_results": {"type": "integer", "description": "Maximum number of results to display per network (default 5, max 10)", "default": 5},
        },
        "required": ["query"],
    },
)
def social_media_search(query: str, network: str = "all", max_results: int = 5) -> str:
    max_results = max(1, min(max_results, 10))
    
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # type: ignore[no-redef]
        except ImportError:
            DDGS = None

    results = []

    # 1. Hacker News API search
    if network in ("hn", "all"):
        try:
            hn_api = f"https://hn.algolia.com/api/v1/search?query={requests.utils.quote(query)}&tags=story"
            resp = requests.get(hn_api, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                hits = data.get("hits", [])[:max_results]
                if hits:
                    results.append("=== Hacker News Stories ===")
                    for idx, hit in enumerate(hits, 1):
                        title = hit.get("title")
                        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                        points = hit.get("points")
                        comments = hit.get("num_comments")
                        author = hit.get("author")
                        results.append(f"{idx}. {title}\n   Link: {url}\n   Points: {points} | Comments: {comments} | Author: {author}")
                    results.append("")
        except Exception as e:
            results.append(f"Hacker News Search error: {e}\n")

    def ddg_site_search(site_domain: str, label: str):
        if DDGS is None:
            return "DDGS search not available."
        try:
            site_query = f"site:{site_domain} {query}"
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(site_query, max_results=max_results))
            if not ddg_results:
                return f"No results on {label}."
            lines = [f"=== {label} Search ==="]
            for idx, r in enumerate(ddg_results, 1):
                title = r.get("title", "").strip()
                href = (r.get("href") or r.get("url") or "").strip()
                body = (r.get("body") or r.get("snippet") or "").strip()
                lines.append(f"{idx}. {title}\n   Link: {href}\n   Snippet: {body[:150]}")
            lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return f"{label} Search error: {e}\n"

    # 2. Reddit Search
    if network in ("reddit", "all"):
        try:
            reddit_url = f"https://www.reddit.com/search.json?q={requests.utils.quote(query)}&sort=relevance&limit={max_results}"
            headers = {"User-Agent": "LumiVoiceAssistant/1.0 by Atharv"}
            resp = requests.get(reddit_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                if children:
                    results.append("=== Reddit Search ===")
                    for idx, child in enumerate(children, 1):
                        post = child.get("data", {})
                        title = post.get("title")
                        permalink = post.get("permalink")
                        post_url = f"https://www.reddit.com{permalink}"
                        subreddit = post.get("subreddit_name_prefixed")
                        ups = post.get("ups")
                        num_comments = post.get("num_comments")
                        results.append(f"{idx}. {title}\n   Subreddit: {subreddit} | Link: {post_url}\n   Ups: {ups} | Comments: {num_comments}")
                    results.append("")
                else:
                    results.append(ddg_site_search("reddit.com", "Reddit"))
            else:
                results.append(ddg_site_search("reddit.com", "Reddit"))
        except Exception:
            results.append(ddg_site_search("reddit.com", "Reddit"))

    # 3. Twitter/X Search
    if network in ("twitter", "all"):
        results.append(ddg_site_search("twitter.com", "Twitter / X"))

    # 4. LinkedIn Search
    if network in ("linkedin", "all"):
        results.append(ddg_site_search("linkedin.com", "LinkedIn"))

    final_str = "\n".join(results).strip()
    return final_str if final_str else "No results found across any network."


@tool(
    name="rss_feed_reader",
    description="Manage RSS/Atom feed subscriptions and read feed updates. Actions: 'subscribe', 'unsubscribe', 'list', 'read', 'sync'.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action to take: 'subscribe', 'unsubscribe', 'list', 'read' (read single feed), or 'sync' (check updates from all subscriptions).",
                "enum": ["subscribe", "unsubscribe", "list", "read", "sync"],
                "default": "sync",
            },
            "url": {"type": "string", "description": "Feed URL (required for subscribe, unsubscribe, and read)"},
            "title": {"type": "string", "description": "Optional title for subscription"},
            "category": {"type": "string", "description": "Subscription category (default 'General')", "default": "General"},
            "max_items": {"type": "integer", "description": "Number of feed entries to read (default 5, max 10)", "default": 5},
        },
        "required": ["action"],
    },
)
def rss_feed_reader(
    action: str,
    url: str | None = None,
    title: str | None = None,
    category: str = "General",
    max_items: int = 5,
) -> str:
    db_path = Path("data/rss_subscriptions.json")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    max_items = max(1, min(max_items, 10))

    db = []
    if db_path.exists():
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            pass

    def parse_feed(feed_content: bytes, limit: int) -> list[dict]:
        entries = []
        try:
            root = ET.fromstring(feed_content)
        except Exception as e:
            raise ValueError(f"XML parsing failed: {e}")

        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item")[:limit]:
                t = item.find("title")
                l = item.find("link")
                d = item.find("description")
                p = item.find("pubDate")
                
                title_txt = t.text.strip() if t is not None and t.text else "No Title"
                link_txt = l.text.strip() if l is not None and l.text else ""
                desc_txt = d.text.strip() if d is not None and d.text else ""
                desc_txt = re.sub(r'<[^>]+>', ' ', desc_txt)
                desc_txt = re.sub(r'\s+', ' ', desc_txt).strip()
                
                entries.append({
                    "title": title_txt,
                    "link": link_txt,
                    "summary": desc_txt[:200] + ("..." if len(desc_txt) > 200 else ""),
                    "published": p.text.strip() if p is not None and p.text else "",
                })
            return entries

        ns = {}
        if root.tag.startswith("{"):
            ns_url = root.tag.split("}")[0][1:]
            ns = {"a": ns_url}

        prefix = "a:" if ns else ""
        entry_tags = root.findall(f".//{prefix}entry", ns)
        
        for entry in entry_tags[:limit]:
            t = entry.find(f"{prefix}title", ns)
            l = entry.find(f"{prefix}link", ns)
            s = entry.find(f"{prefix}summary", ns) or entry.find(f"{prefix}content", ns)
            u = entry.find(f"{prefix}updated", ns) or entry.find(f"{prefix}published", ns)
            
            title_txt = t.text.strip() if t is not None and t.text else "No Title"
            
            link_txt = ""
            if l is not None:
                link_txt = l.get("href") or (l.text.strip() if l.text else "")
                
            desc_txt = s.text.strip() if s is not None and s.text else ""
            desc_txt = re.sub(r'<[^>]+>', ' ', desc_txt)
            desc_txt = re.sub(r'\s+', ' ', desc_txt).strip()

            entries.append({
                "title": title_txt,
                "link": link_txt,
                "summary": desc_txt[:200] + ("..." if len(desc_txt) > 200 else ""),
                "published": u.text.strip() if u is not None and u.text else "",
            })
        return entries

    if action == "subscribe":
        if not url:
            return "error: 'url' parameter is required to subscribe."
        if any(item["url"] == url for item in db):
            return f"Already subscribed to feed: {url}"
        
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            parse_feed(resp.content, 1)
        except Exception as e:
            return f"error: Failed to validate RSS feed. Details: {e}"

        feed_title = title
        if not feed_title:
            try:
                root = ET.fromstring(resp.content)
                ch = root.find("channel/title")
                if ch is not None and ch.text:
                    feed_title = ch.text.strip()
                else:
                    feed_title = root.find(".//{http://www.w3.org/2005/Atom}title")
                    if feed_title is not None and feed_title.text:
                        feed_title = feed_title.text.strip()
            except Exception:
                pass
        
        feed_title = feed_title or url

        db.append({
            "url": url,
            "title": feed_title,
            "category": category,
            "added_at": datetime.now().isoformat(),
        })
        
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        return f"Successfully subscribed to '{feed_title}' under category '{category}'"

    elif action == "unsubscribe":
        if not url:
            return "error: 'url' parameter is required to unsubscribe."
        initial_len = len(db)
        db = [item for item in db if item["url"] != url]
        if len(db) == initial_len:
            return f"Feed URL not found: {url}"
        
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        return f"Unsubscribed from {url} successfully."

    elif action == "list":
        if not db:
            return "No RSS subscriptions yet. Subscribe using action='subscribe'."
        lines = ["=== RSS Subscriptions ==="]
        for idx, sub in enumerate(db, 1):
            lines.append(f"{idx}. {sub['title']} ({sub['category']})\n   Feed: {sub['url']}")
        return "\n".join(lines)

    elif action == "read":
        if not url:
            return "error: 'url' parameter is required to read."
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            entries = parse_feed(resp.content, max_items)
            if not entries:
                return f"No entries found in feed {url}"
            lines = [f"=== Feed: {url} ==="]
            for idx, entry in enumerate(entries, 1):
                lines.append(f"{idx}. {entry['title']}\n   Link: {entry['link']}\n   Published: {entry['published']}\n   Summary: {entry['summary']}")
            return "\n\n".join(lines)
        except Exception as e:
            return f"Error reading feed: {e}"

    elif action == "sync":
        if not db:
            return "No RSS subscriptions to sync. Subscribe to a feed first."
        
        sync_results = ["=== Feed Sync Updates ==="]
        def fetch_and_parse(sub):
            try:
                resp = requests.get(sub["url"], timeout=8)
                resp.raise_for_status()
                parsed_entries = parse_feed(resp.content, 3)
                return sub["title"], parsed_entries, None
            except Exception as e:
                return sub["title"], [], str(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_results = [executor.submit(fetch_and_parse, sub) for sub in db]
            for fut in concurrent.futures.as_completed(future_results):
                title_txt, entries, err = fut.result()
                if err:
                    sync_results.append(f"❌ {title_txt} (Error: {err})")
                else:
                    sync_results.append(f"📰 {title_txt} ({len(entries)} updates):")
                    for entry in entries:
                        sync_results.append(f"  - {entry['title']} ({entry['link']})")
                sync_results.append("")
        
        return "\n".join(sync_results).strip()
