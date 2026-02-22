"""
Tech Education Resource Scraper
================================
Pulls free tech courses from permitted sources using official APIs
and public/open data, then uses Claude API to clean descriptions.
Outputs a structured JSON file for Bootstrap Studio.

Platforms covered:
  - YouTube Data API v3
  - MIT OpenCourseWare (open data)
  - freeCodeCamp (public GitHub)
  - Google (open learning catalog)
  - Microsoft Learn (public API)
  - IBM SkillsBuild (web scraping permitted)
  - AWS Skill Builder (public catalog)
  - Coursera (public catalog API)
  - Stanford Online (public course listings)

Categories:
  - Python / Programming
  - Data Science / AI
  - Web Development
  - IT / Cybersecurity
  - Project Management / Agile
"""

import os
import json
import time
import logging
import schedule
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import anthropic

# ─────────────────────────────────────────────
# CONFIGURATION — fill these in before running
# ─────────────────────────────────────────────
CONFIG = {
    "youtube_api_key":   os.getenv("YOUTUBE_API_KEY", ""),
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "output_file":       "resources.json",
    "log_file":          "scraper.log",
    "max_results_per_source": 10,   # per category per platform
}

CATEGORIES = [
    "Python Programming",
    "Data Science AI",
    "Web Development",
    "IT Cybersecurity",
    "Project Management Agile",
]

# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CLAUDE API — DESCRIPTION CLEANER
# ─────────────────────────────────────────────
def clean_description(title: str, raw_description: str, category: str) -> str:
    """Uses Claude API to generate a clean, concise 2-sentence description."""
    try:
        client = anthropic.Anthropic(api_key=CONFIG["anthropic_api_key"])
        prompt = (
            f"You are helping catalog free tech education resources. "
            f"Given the course title and raw description below, write a clean, "
            f"engaging 2-sentence summary (max 50 words) suitable for a resource "
            f"directory. Focus on what the learner will gain. Be concise and clear.\n\n"
            f"Category: {category}\n"
            f"Title: {title}\n"
            f"Raw Description: {raw_description}\n\n"
            f"Return only the 2-sentence summary, nothing else."
        )
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        log.warning(f"Claude API error for '{title}': {e}")
        return raw_description[:200] if raw_description else "No description available."


# ─────────────────────────────────────────────
# HELPER — BUILD RESOURCE DICT
# ─────────────────────────────────────────────
def build_resource(title, url, description, platform, category, level="All Levels", free=True):
    return {
        "title":       title,
        "url":         url,
        "description": description,
        "platform":    platform,
        "category":    category,
        "level":       level,
        "free":        free,
        "retrieved":   datetime.today().strftime("%Y-%m-%d"),
    }


# ─────────────────────────────────────────────
# SOURCE 1 — YOUTUBE DATA API v3
# ─────────────────────────────────────────────
def fetch_youtube(category: str) -> list:
    log.info(f"[YouTube] Fetching: {category}")
    results = []
    search_query = f"free {category} tutorial course"
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part":       "snippet",
        "q":          search_query,
        "type":       "playlist",
        "maxResults": CONFIG["max_results_per_source"],
        "key":        CONFIG["youtube_api_key"],
        "relevanceLanguage": "en",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("items", []):
            snippet    = item["snippet"]
            playlist_id = item["id"].get("playlistId", "")
            if not playlist_id:
                continue
            raw_desc = snippet.get("description", "")
            clean    = clean_description(snippet["title"], raw_desc, category)
            results.append(build_resource(
                title=snippet["title"],
                url=f"https://www.youtube.com/playlist?list={playlist_id}",
                description=clean,
                platform="YouTube",
                category=category,
            ))
    except Exception as e:
        log.error(f"[YouTube] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 2 — MIT OPENCOURSEWARE (open JSON feed)
# ─────────────────────────────────────────────
MITOCW_KEYWORD_MAP = {
    "Python Programming":        "python",
    "Data Science AI":           "machine learning",
    "Web Development":           "web",
    "IT Cybersecurity":          "security",
    "Project Management Agile":  "management",
}

def fetch_mit_ocw(category: str) -> list:
    log.info(f"[MIT OCW] Fetching: {category}")
    results = []
    keyword  = MITOCW_KEYWORD_MAP.get(category, category.lower())
    # MIT OCW has a public search endpoint
    url = "https://ocw.mit.edu/search/"
    params = {"q": keyword, "f_format": "Online Textbook"}
    headers = {"User-Agent": "TechEduScraper/1.0 (educational, non-commercial)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.course-card")[:CONFIG["max_results_per_source"]]
        for card in cards:
            title_el = card.select_one("h3, h2, .course-title")
            link_el  = card.select_one("a[href]")
            desc_el  = card.select_one("p, .course-description")
            if not title_el or not link_el:
                continue
            title    = title_el.get_text(strip=True)
            href     = link_el["href"]
            full_url = href if href.startswith("http") else f"https://ocw.mit.edu{href}"
            raw_desc = desc_el.get_text(strip=True) if desc_el else ""
            clean    = clean_description(title, raw_desc, category)
            results.append(build_resource(
                title=title, url=full_url,
                description=clean,
                platform="MIT OpenCourseWare",
                category=category,
            ))
    except Exception as e:
        log.error(f"[MIT OCW] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 3 — FREECODECAMP (GitHub public repo)
# ─────────────────────────────────────────────
FCC_CATEGORY_MAP = {
    "Python Programming":        "Scientific Computing with Python",
    "Data Science AI":           "Data Analysis with Python",
    "Web Development":           "Responsive Web Design",
    "IT Cybersecurity":          "Information Security",
    "Project Management Agile":  "College Algebra with Python",  # closest available
}

def fetch_freecodecamp(category: str) -> list:
    log.info(f"[freeCodeCamp] Fetching: {category}")
    # freeCodeCamp curriculum is open on GitHub; we use their public site structure
    cert_name = FCC_CATEGORY_MAP.get(category, "")
    if not cert_name:
        return []
    results = []
    url = "https://www.freecodecamp.org/learn/"
    headers = {"User-Agent": "TechEduScraper/1.0 (educational, non-commercial)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Look for the matching certification block
        for block in soup.find_all(["h2", "h3", "a"]):
            text = block.get_text(strip=True)
            if cert_name.lower() in text.lower():
                href = block.get("href", "/learn")
                full_url = href if href.startswith("http") else f"https://www.freecodecamp.org{href}"
                clean = clean_description(
                    text,
                    f"Free certification curriculum: {text}",
                    category
                )
                results.append(build_resource(
                    title=text,
                    url=full_url,
                    description=clean,
                    platform="freeCodeCamp",
                    category=category,
                ))
                break
        # Always add the main freeCodeCamp page for this cert as a fallback
        if not results:
            results.append(build_resource(
                title=f"freeCodeCamp — {cert_name}",
                url="https://www.freecodecamp.org/learn/",
                description=clean_description(cert_name, f"Free curriculum covering {cert_name}", category),
                platform="freeCodeCamp",
                category=category,
            ))
    except Exception as e:
        log.error(f"[freeCodeCamp] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 4 — MICROSOFT LEARN (public REST API)
# ─────────────────────────────────────────────
MS_KEYWORD_MAP = {
    "Python Programming":        "python",
    "Data Science AI":           "azure ai machine learning",
    "Web Development":           "web development",
    "IT Cybersecurity":          "security",
    "Project Management Agile":  "devops agile",
}

def fetch_microsoft_learn(category: str) -> list:
    log.info(f"[Microsoft Learn] Fetching: {category}")
    results  = []
    keyword  = MS_KEYWORD_MAP.get(category, category.lower())
    url      = "https://learn.microsoft.com/api/catalog/"
    params   = {
        "term":   keyword,
        "locale": "en-us",
        "type":   "learningPath",
        "$top":   CONFIG["max_results_per_source"],
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("learningPaths", [])[:CONFIG["max_results_per_source"]]:
            title    = item.get("title", "")
            raw_desc = item.get("summary", "")
            item_url = item.get("url", "https://learn.microsoft.com")
            if not item_url.startswith("http"):
                item_url = f"https://learn.microsoft.com{item_url}"
            clean = clean_description(title, raw_desc, category)
            results.append(build_resource(
                title=title, url=item_url,
                description=clean,
                platform="Microsoft Learn",
                category=category,
                level=item.get("levels", ["All Levels"])[0].capitalize() if item.get("levels") else "All Levels",
            ))
    except Exception as e:
        log.error(f"[Microsoft Learn] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 5 — AWS SKILL BUILDER (public catalog)
# ─────────────────────────────────────────────
AWS_KEYWORD_MAP = {
    "Python Programming":        "python developer",
    "Data Science AI":           "machine learning",
    "Web Development":           "cloud web",
    "IT Cybersecurity":          "security",
    "Project Management Agile":  "cloud practitioner",
}

def fetch_aws(category: str) -> list:
    log.info(f"[AWS] Fetching: {category}")
    results = []
    keyword = AWS_KEYWORD_MAP.get(category, category.lower())
    # AWS Skill Builder public search
    url = "https://explore.skillbuilder.aws/learn/catalog"
    params = {"searchText": keyword, "format": "Digital"}
    headers = {"User-Agent": "TechEduScraper/1.0 (educational, non-commercial)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.catalog-item, div.course-card, article")[:CONFIG["max_results_per_source"]]
        for card in cards:
            title_el = card.select_one("h3, h2, .title")
            link_el  = card.select_one("a[href]")
            desc_el  = card.select_one("p, .description")
            if not title_el:
                continue
            title    = title_el.get_text(strip=True)
            href     = link_el["href"] if link_el else url
            full_url = href if href.startswith("http") else f"https://explore.skillbuilder.aws{href}"
            raw_desc = desc_el.get_text(strip=True) if desc_el else ""
            clean    = clean_description(title, raw_desc, category)
            results.append(build_resource(
                title=title, url=full_url,
                description=clean,
                platform="AWS Skill Builder",
                category=category,
            ))
    except Exception as e:
        log.error(f"[AWS] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 6 — COURSERA (public catalog API)
# ─────────────────────────────────────────────
COURSERA_KEYWORD_MAP = {
    "Python Programming":        "python programming",
    "Data Science AI":           "data science machine learning",
    "Web Development":           "web development html css",
    "IT Cybersecurity":          "cybersecurity",
    "Project Management Agile":  "project management agile",
}

def fetch_coursera(category: str) -> list:
    log.info(f"[Coursera] Fetching: {category}")
    results = []
    keyword = COURSERA_KEYWORD_MAP.get(category, category.lower())
    # Coursera public catalog — free courses filter
    url = "https://api.coursera.org/api/courses.v1"
    params = {
        "q":      "search",
        "query":  keyword,
        "limit":  CONFIG["max_results_per_source"],
        "fields": "name,slug,description,domainTypes",
        "includes": "v2Fields",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("elements", []):
            title    = item.get("name", "")
            slug     = item.get("slug", "")
            raw_desc = item.get("description", "")
            course_url = f"https://www.coursera.org/learn/{slug}"
            clean    = clean_description(title, raw_desc, category)
            results.append(build_resource(
                title=title,
                url=course_url,
                description=clean,
                platform="Coursera",
                category=category,
            ))
    except Exception as e:
        log.error(f"[Coursera] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 7 — STANFORD ONLINE (public listings)
# ─────────────────────────────────────────────
STANFORD_KEYWORD_MAP = {
    "Python Programming":        "programming",
    "Data Science AI":           "artificial intelligence",
    "Web Development":           "computer science",
    "IT Cybersecurity":          "cybersecurity",
    "Project Management Agile":  "management",
}

def fetch_stanford(category: str) -> list:
    log.info(f"[Stanford Online] Fetching: {category}")
    results = []
    keyword = STANFORD_KEYWORD_MAP.get(category, category.lower())
    url     = "https://online.stanford.edu/free-courses"
    headers = {"User-Agent": "TechEduScraper/1.0 (educational, non-commercial)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup  = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.course-card, article.course, div.views-row")
        count = 0
        for card in cards:
            if count >= CONFIG["max_results_per_source"]:
                break
            title_el = card.select_one("h3, h2, .course-title, .field-content a")
            link_el  = card.select_one("a[href]")
            desc_el  = card.select_one("p, .course-description, .field-body")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if keyword.lower() not in title.lower() and keyword.lower() not in card.get_text().lower():
                continue
            href     = link_el["href"] if link_el else url
            full_url = href if href.startswith("http") else f"https://online.stanford.edu{href}"
            raw_desc = desc_el.get_text(strip=True) if desc_el else ""
            clean    = clean_description(title, raw_desc, category)
            results.append(build_resource(
                title=title, url=full_url,
                description=clean,
                platform="Stanford Online",
                category=category,
            ))
            count += 1
    except Exception as e:
        log.error(f"[Stanford Online] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 8 — IBM SKILLSBUILD (public listings)
# ─────────────────────────────────────────────
IBM_KEYWORD_MAP = {
    "Python Programming":        "python",
    "Data Science AI":           "data science",
    "Web Development":           "web development",
    "IT Cybersecurity":          "cybersecurity",
    "Project Management Agile":  "project management",
}

def fetch_ibm(category: str) -> list:
    log.info(f"[IBM SkillsBuild] Fetching: {category}")
    results = []
    keyword = IBM_KEYWORD_MAP.get(category, category.lower())
    url     = f"https://skillsbuild.org/adult-learners"
    headers = {"User-Agent": "TechEduScraper/1.0 (educational, non-commercial)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup  = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.course-card, article, div.bx--tile")[:CONFIG["max_results_per_source"]]
        for card in cards:
            text = card.get_text().lower()
            if keyword.lower() not in text:
                continue
            title_el = card.select_one("h3, h2, .title")
            link_el  = card.select_one("a[href]")
            desc_el  = card.select_one("p")
            if not title_el:
                continue
            title    = title_el.get_text(strip=True)
            href     = link_el["href"] if link_el else url
            full_url = href if href.startswith("http") else f"https://skillsbuild.org{href}"
            raw_desc = desc_el.get_text(strip=True) if desc_el else ""
            clean    = clean_description(title, raw_desc, category)
            results.append(build_resource(
                title=title, url=full_url,
                description=clean,
                platform="IBM SkillsBuild",
                category=category,
            ))
    except Exception as e:
        log.error(f"[IBM SkillsBuild] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 9 — GOOGLE (via Google Digital Garage / Skillshop public listings)
# ─────────────────────────────────────────────
def fetch_google(category: str) -> list:
    """
    Google doesn't have one open API for all its learning resources,
    so we pull from Google Digital Garage and Skillshop public pages.
    """
    log.info(f"[Google] Fetching: {category}")
    results  = []
    sources  = [
        ("https://grow.google/certificates/", "Google Career Certificates"),
        ("https://skillshop.withgoogle.com/", "Google Skillshop"),
    ]
    headers  = {"User-Agent": "TechEduScraper/1.0 (educational, non-commercial)"}
    keywords = category.lower().split()

    for source_url, platform_name in sources:
        try:
            resp = requests.get(source_url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("div.card, article, div.course-item, li.course")
            for card in cards[:CONFIG["max_results_per_source"]]:
                text = card.get_text().lower()
                if not any(kw in text for kw in keywords):
                    continue
                title_el = card.select_one("h3, h2, .title, strong")
                link_el  = card.select_one("a[href]")
                desc_el  = card.select_one("p")
                if not title_el:
                    continue
                title    = title_el.get_text(strip=True)
                href     = link_el["href"] if link_el else source_url
                full_url = href if href.startswith("http") else f"https://grow.google{href}"
                raw_desc = desc_el.get_text(strip=True) if desc_el else ""
                clean    = clean_description(title, raw_desc, category)
                results.append(build_resource(
                    title=title, url=full_url,
                    description=clean,
                    platform=platform_name,
                    category=category,
                ))
        except Exception as e:
            log.error(f"[Google - {platform_name}] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────
FETCHERS = [
    fetch_youtube,
    fetch_mit_ocw,
    fetch_freecodecamp,
    fetch_microsoft_learn,
    fetch_aws,
    fetch_coursera,
    fetch_stanford,
    fetch_ibm,
    fetch_google,
]

def run_scraper():
    log.info("=" * 50)
    log.info(f"Starting scrape run: {datetime.now().isoformat()}")
    log.info("=" * 50)

    all_resources = []

    for category in CATEGORIES:
        log.info(f"\n── Category: {category} ──")
        for fetcher in FETCHERS:
            resources = fetcher(category)
            all_resources.extend(resources)
            log.info(f"   {fetcher.__name__}: {len(resources)} items")
            time.sleep(1)  # polite delay between requests

    # Deduplicate by URL
    seen_urls = set()
    unique    = []
    for r in all_resources:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique.append(r)

    # Build final JSON structure for Bootstrap Studio
    output = {
        "generated":  datetime.today().strftime("%Y-%m-%d"),
        "total":      len(unique),
        "categories": CATEGORIES,
        "resources":  unique,
    }

    with open(CONFIG["output_file"], "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    log.info(f"\n✅ Done! {len(unique)} unique resources saved to {CONFIG['output_file']}")
    return output


# ─────────────────────────────────────────────
# SCHEDULER — monthly refresh on the 1st at 6am
# ─────────────────────────────────────────────
def start_scheduler():
    log.info("Scheduler started — will run on the 1st of each month at 6:00 AM.")
    schedule.every().month.do(run_scraper)  # runs on day 1 of each month
    # For testing: schedule.every(1).minutes.do(run_scraper)
    while True:
        schedule.run_pending()
        time.sleep(60)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if "--schedule" in sys.argv:
        run_scraper()          # run once immediately, then schedule
        start_scheduler()
    else:
        run_scraper()          # one-time manual run
