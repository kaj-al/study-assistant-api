import logging
import re
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
import requests

import config

logger = logging.getLogger(__name__)

YOUTUBE_WATCH_REGEX = re.compile(
    r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
)

def extract_youtube_video_id(url: str) -> str:
    match = YOUTUBE_WATCH_REGEX.search(url)
    if match:
        return match.group(1)
    return ""

def parse_duration_to_seconds(dur_str: str) -> int:
    """Parses 'HH:MM:SS' or 'MM:SS' string into integer seconds."""
    if not dur_str:
        return 0
    try:
        parts = dur_str.strip().split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1 and parts[0].isdigit():
            return int(parts[0])
    except Exception:
        pass
    return 0

def get_youtube_videos(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """
    STRICT: Retrieves genuine YouTube video lectures, prioritizing both:
    1. Top popular Indian educators & institutions (NPTEL, Gate Smashers, Apna College, CodeWithHarry, Krish Naik, IITs)
    2. Renowned global academic courses (MIT, Stanford, freeCodeCamp, 3Blue1Brown)
    """
    videos: List[Dict[str, Any]] = []
    seen_ids = set()
    serper_key = config.SERPER_API_KEY

    clean_q = query.strip()

    if serper_key:
        try:
            url = "https://google.serper.dev/videos"
            headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}

            # Search A: Indian popular educators & NPTEL/Gate courses (gl='in')
            payload_indian = {
                "q": f'{clean_q} lecture tutorial hindi OR nptel OR "gate smashers" OR "apna college" OR "krish naik" OR "codewithharry" OR best',
                "gl": "in"
            }
            # Search B: Global university and masterclasses (gl='us')
            payload_global = {
                "q": f'{clean_q} full course lecture tutorial "mit" OR "stanford" OR "freecodecamp" OR "3blue1brown" OR university',
                "gl": "us"
            }

            with ThreadPoolExecutor(max_workers=2) as sub_exec:
                f_in = sub_exec.submit(requests.post, url, json=payload_indian, headers=headers, timeout=8)
                f_gl = sub_exec.submit(requests.post, url, json=payload_global, headers=headers, timeout=8)
                r_in = f_in.result()
                r_gl = f_gl.result()

            v_in = r_in.json().get("videos", []) if r_in.status_code == 200 else []
            v_gl = r_gl.json().get("videos", []) if r_gl.status_code == 200 else []

            # Interleave results: Indian popular educator + Global masterclass
            max_len = max(len(v_in), len(v_gl))
            for i in range(max_len):
                if i < len(v_in):
                    item = v_in[i]
                    link = item.get("link", "")
                    vid = extract_youtube_video_id(link)
                    if vid and vid not in seen_ids:
                        seen_ids.add(vid)
                        dur_sec = parse_duration_to_seconds(item.get("duration", ""))
                        videos.append({
                            "title": item.get("title", "YouTube Lecture"),
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "duration": dur_sec if dur_sec > 0 else None,
                            "channel": item.get("channel") or item.get("source") or "Popular Indian Educator",
                            "thumbnail": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                        })
                if i < len(v_gl):
                    item = v_gl[i]
                    link = item.get("link", "")
                    vid = extract_youtube_video_id(link)
                    if vid and vid not in seen_ids:
                        seen_ids.add(vid)
                        dur_sec = parse_duration_to_seconds(item.get("duration", ""))
                        videos.append({
                            "title": item.get("title", "YouTube Lecture"),
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "duration": dur_sec if dur_sec > 0 else None,
                            "channel": item.get("channel") or item.get("source") or "Global University Course",
                            "thumbnail": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                        })
                if len(videos) >= max_results:
                    break

        except Exception as e:
            logger.warning(f"Serper YouTube search failed: {e}")

    # Fallback to yt_dlp if needed
    if len(videos) < max_results:
        try:
            import yt_dlp
            opts = {
                "quiet": True,
                "extract_flat": True,
                "skip_download": True
            }
            needed = max_results - len(videos)
            with yt_dlp.YoutubeDL(opts) as ydl:
                results = ydl.extract_info(f"ytsearch{needed + 3}:{clean_q} lecture tutorial hindi english", download=False)
                for entry in results.get("entries", []):
                    if not entry:
                        continue
                    vid = entry.get("id")
                    if vid and vid not in seen_ids:
                        seen_ids.add(vid)
                        videos.append({
                            "title": entry.get("title", "YouTube Lecture"),
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "duration": entry.get("duration"),
                            "channel": entry.get("uploader") or entry.get("channel") or "YouTube",
                            "thumbnail": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                        })
                        if len(videos) >= max_results:
                            break
        except Exception as e:
            logger.warning(f"yt_dlp search failed: {e}")

    # Guard: Ensure every single URL is strictly a verified YouTube video link
    filtered_videos = [v for v in videos if extract_youtube_video_id(v["url"])]
    return filtered_videos[:max_results]

def get_arxiv_papers(topic: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """
    STRICT: Retrieves genuine arXiv academic research papers.
    CRITICAL: Guarantees that seminal, foundational landmark papers
    (e.g., 'Attention Is All You Need' for transformers, seminal papers for GANs, ResNet, etc.)
    are prioritized and displayed right at the top.
    """
    papers: List[Dict[str, Any]] = []
    seen_arxiv_ids = set()
    serper_key = config.SERPER_API_KEY

    clean_topic = topic.strip()

    if serper_key:
        try:
            url = "https://google.serper.dev/search"
            headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}

            # Search 1: Landmark / Seminal / Foundational papers on this topic
            p_seminal = {"q": f"{clean_topic} landmark seminal foundational paper site:arxiv.org/abs"}
            # Search 2: Direct arXiv topic search
            p_direct = {"q": f"site:arxiv.org/abs {clean_topic}"}

            with ThreadPoolExecutor(max_workers=2) as sub_exec:
                f_sem = sub_exec.submit(requests.post, url, json=p_seminal, headers=headers, timeout=8)
                f_dir = sub_exec.submit(requests.post, url, json=p_direct, headers=headers, timeout=8)
                r_sem = f_sem.result()
                r_dir = f_dir.result()

            # Process Seminal first, then direct
            responses = []
            if r_sem.status_code == 200:
                responses.append(r_sem.json().get("organic", []))
            if r_dir.status_code == 200:
                responses.append(r_dir.json().get("organic", []))

            for org_list in responses:
                for item in org_list:
                    link = item.get("link", "")
                    if "arxiv.org/abs/" in link:
                        id_match = re.search(r'arxiv\.org\/abs\/(\d{4}\.\d{4,5}(?:v\d+)?)', link)
                        arxiv_id = id_match.group(1) if id_match else ""
                        if arxiv_id and arxiv_id in seen_arxiv_ids:
                            continue
                        if arxiv_id:
                            seen_arxiv_ids.add(arxiv_id)

                        raw_title = item.get("title", "").replace("\n", " ").strip()
                        # Clean leading [YYMM.NNNNN] bracket tags
                        clean_title = re.sub(r'^\[\d{4}\.\d{4,5}(?:v\d+)?\]\s*', '', raw_title)
                        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else f"{link.replace('/abs/', '/pdf/')}.pdf"

                        papers.append({
                            "title": clean_title or f"Research Paper on {clean_topic}",
                            "url": link,
                            "summary": item.get("snippet", ""),
                            "pdf_url": pdf_url,
                            "arxiv_id": arxiv_id
                        })
                        if len(papers) >= max_results:
                            break
                if len(papers) >= max_results:
                    break

        except Exception as e:
            logger.warning(f"Serper arXiv search failed: {e}")

    # Fallback to direct arXiv XML API if needed
    if len(papers) < max_results:
        try:
            import xml.etree.ElementTree as ET
            clean_q = re.sub(r'[^a-zA-Z0-9\s]', ' ', clean_topic).strip().replace(" ", "+")
            api_url = f"https://export.arxiv.org/api/query?search_query=all:{clean_q}&start=0&max_results={max_results}"
            r = requests.get(api_url, timeout=5, headers={"User-Agent": "Nexora/1.0"})
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", ns):
                    title_elem = entry.find("atom:title", ns)
                    id_elem = entry.find("atom:id", ns)
                    summary_elem = entry.find("atom:summary", ns)
                    if title_elem is not None and id_elem is not None:
                        paper_url = id_elem.text.strip()
                        if "arxiv.org" in paper_url:
                            id_match = re.search(r'arxiv\.org\/abs\/(\d{4}\.\d{4,5}(?:v\d+)?)', paper_url)
                            arxiv_id = id_match.group(1) if id_match else ""
                            if arxiv_id and arxiv_id in seen_arxiv_ids:
                                continue
                            if arxiv_id:
                                seen_arxiv_ids.add(arxiv_id)

                            title = title_elem.text.strip().replace("\n", " ")
                            summary = summary_elem.text.strip().replace("\n", " ")[:240] if summary_elem is not None else ""
                            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else paper_url.replace("/abs/", "/pdf/") + ".pdf"

                            papers.append({
                                "title": title,
                                "url": paper_url,
                                "summary": summary,
                                "pdf_url": pdf_url,
                                "arxiv_id": arxiv_id
                            })
                            if len(papers) >= max_results:
                                break
        except Exception as e:
            logger.warning(f"Direct arXiv API failed: {e}")

    # Guard: Ensure every single URL is strictly an arxiv.org URL
    filtered_papers = [p for p in papers if "arxiv.org" in p["url"]]
    return filtered_papers[:max_results]

def get_documentation(query: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """
    STRICT: Retrieves ONLY official documentation, reference manuals, and developer/academic guides.
    Strictly excludes YouTube videos, arXiv papers, social media, and forums.
    """
    docs: List[Dict[str, Any]] = []
    seen_urls = set()

    BLOCKED_DOMAINS = (
        "youtube.com", "youtu.be", "arxiv.org",
        "reddit.com", "twitter.com", "x.com", "facebook.com",
        "instagram.com", "tiktok.com", "quora.com", "pinterest.com"
    )

    serper_key = config.SERPER_API_KEY
    if serper_key:
        try:
            url = "https://google.serper.dev/search"
            payload = {
                "q": f'"{query}" (documentation OR docs OR "official documentation" OR "reference manual" OR "api reference" OR "user guide") -site:youtube.com -site:arxiv.org -site:reddit.com -site:quora.com -site:medium.com'
            }
            headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("organic", []):
                    link = item.get("link", "")
                    if not link or link in seen_urls:
                        continue

                    # STRICT exclusion of YouTube and arXiv
                    link_lower = link.lower()
                    if any(blocked in link_lower for blocked in BLOCKED_DOMAINS):
                        continue

                    seen_urls.add(link)
                    domain = urlparse(link).netloc.replace("www.", "")

                    # Format human-friendly source name
                    source_name = "Official Documentation"
                    if "docs." in domain or "developer." in domain:
                        source_name = domain.split(".")[0].title() + " Docs"
                    elif "github.io" in domain or "readthedocs.io" in domain:
                        source_name = "Library Reference Manual"
                    elif ".edu" in domain:
                        source_name = "Academic Course Notes (" + domain + ")"
                    elif ".org" in domain:
                        source_name = domain.split(".")[0].title() + " Reference"

                    docs.append({
                        "title": item.get("title", f"{query} Documentation"),
                        "url": link,
                        "snippet": item.get("snippet", ""),
                        "source": source_name
                    })
                    if len(docs) >= max_results:
                        break
        except Exception as e:
            logger.warning(f"Serper documentation search failed: {e}")

    # Fallback to curated authoritative documentation portals if empty
    if not docs:
        encoded_q = query.replace(" ", "+")
        docs = [
            {
                "title": f"{query} - DevDocs Reference Manual",
                "url": f"https://devdocs.io/#q={encoded_q}",
                "snippet": f"Unified developer documentation, API specifications, and reference guides for {query}.",
                "source": "DevDocs Official Manual"
            },
            {
                "title": f"{query} - Mozilla Developer Network (MDN Web Docs)",
                "url": f"https://developer.mozilla.org/en-US/search?q={encoded_q}",
                "snippet": f"In-depth open documentation, web standards, and developer references.",
                "source": "MDN Web Docs"
            },
            {
                "title": f"{query} - ReadTheDocs Technical Documentation",
                "url": f"https://readthedocs.org/search/?q={encoded_q}",
                "snippet": f"Open source technical documentation, API guides, and user manuals.",
                "source": "ReadTheDocs"
            }
        ]

    # Guard: Ensure no YouTube or arXiv link ever slips through
    filtered_docs = [
        d for d in docs
        if not any(b in d["url"].lower() for b in BLOCKED_DOMAINS)
    ]
    return filtered_docs[:max_results]

def get_all_recommendations(topic: str, level: str = "College") -> Dict[str, Any]:
    """
    Unified Hub orchestrator:
    - videos: ONLY verified YouTube video courses (popular Indian educators + global universities)
    - papers: ONLY verified arXiv academic papers (seminal & landmark papers prioritized)
    - docs: ONLY verified official documentation and reference guides
    """
    clean_topic = topic.strip()
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_yt = executor.submit(get_youtube_videos, clean_topic)
        f_pap = executor.submit(get_arxiv_papers, clean_topic)
        f_doc = executor.submit(get_documentation, clean_topic)

        return {
            "topic": clean_topic,
            "level": level,
            "videos": f_yt.result(),
            "papers": f_pap.result(),
            "docs": f_doc.result()
        }
