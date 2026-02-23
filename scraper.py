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
from dotenv import load_dotenv

# Load .env FIRST before anything reads os.getenv()
load_dotenv(override=True)

# ─────────────────────────────────────────────
# CONFIGURATION — fill these in before running
# ─────────────────────────────────────────────
CONFIG = {
    "youtube_api_key":   os.getenv("YOUTUBE_API_KEY", ""),
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "output_file":       "resources.json",
    "log_file":          "scraper.log",
    "max_results_per_source": 30,   # per category per platform
}

CATEGORIES = [
    "Programming & Computer Science",
    "Data Science AI",
    "Web Development",
    "UX Design",
    "IT / Cybersecurity",
    "Project Management / Agile / Career Skills",
]

# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"], encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Verify keys loaded correctly
log.info(f"YouTube key loaded: {'YES' if CONFIG['youtube_api_key'] else 'NO - CHECK .env'}")
log.info(f"Anthropic key loaded: {'YES' if CONFIG['anthropic_api_key'] else 'NO - CHECK .env'}")


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
# ─────────────────────────────────────────────
# SOURCE 1b — YOUTUBE CURATED PLAYLISTS
# Hand-picked playlists to guarantee quality coverage
# ─────────────────────────────────────────────
YOUTUBE_CURATED = {
    "Programming & Computer Science": [
        {"title": "TypeScript Training [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUULrJCzLdveKPBEzYC5qPJud", "description": "Comprehensive TypeScript training covering types, interfaces, generics, and modern TypeScript development practices.", "level": "All Levels"},
        {"title": "Go Programming Language Tutorial [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUIxgVSjwbOfWmnGrVWwjYlI", "description": "Full Go programming course covering syntax, concurrency, web APIs, and building production-ready Go applications.", "level": "All Levels"},
        {"title": "Kotlin [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUJ3rGmomS8HNxG4GsR3O68e", "description": "Intermediate Kotlin programming course covering Android development, coroutines, and modern Kotlin features.", "level": "Intermediate"},
        {"title": "Introduction to ASP.NET [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUJ5JWyHUtFXhX6mfQwiVaBs", "description": "Introduction to ASP.NET web development covering MVC, APIs, authentication, and deploying .NET web applications.", "level": "All Levels"},
        {"title": "PHP Training Videos [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUIjP-QLfvICa1TvqTLFvn1b", "description": "PHP programming course covering core syntax, OOP, database integration, and building dynamic web applications.", "level": "All Levels"},
        {"title": "SQL Training Playlist [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUKL3yPbn8yWnatjUg0P0I-Z", "description": "Complete SQL training covering queries, joins, subqueries, stored procedures, and database design fundamentals.", "level": "All Levels"},
    ],
    "Data Science AI": [
        {"title": "TensorFlow Introduction Course [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUK1Gw2Cj7-M0mhk0oLE6jzk", "description": "Hands-on TensorFlow course covering neural networks, model training, deep learning pipelines, and deployment.", "level": "All Levels"},
        {"title": "Business Analytics [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUIhyGLSiEzotDRF0hc1xbiN", "description": "Business analytics course covering data-driven decision making, statistical analysis, visualization, and BI tools.", "level": "All Levels"},
    ],
    "Web Development": [
        {"title": "Introduction to Google Cloud Platform [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUULvVL0SoVmiS1kTiC87W_AG", "description": "Beginner-friendly introduction to Google Cloud Platform covering core services, storage, compute, and deployment.", "level": "Beginner"},
        {"title": "Microsoft Azure Full Course [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUJ-lLsBkEt1CckzIagYNq9S", "description": "Comprehensive Azure cloud course covering virtual machines, storage, networking, security, and Azure DevOps.", "level": "All Levels"},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "Product Management Training Playlist [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUIE8vrshd0pKiYl7PKpINPe", "description": "Complete product management training covering roadmapping, user stories, stakeholder management, and Agile PM practices.", "level": "All Levels"},
        {"title": "Interview Questions & Soft Skills Basics Course [2026]", "url": "https://www.youtube.com/playlist?list=PLEiEAq2VkUUKpolUs6VxIBzWDC_FzbFdH", "description": "Career development course covering interview preparation, soft skills, communication, and professional workplace skills.", "level": "All Levels"},
    ],
}

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
    # Append curated playlists for this category
    existing_urls = {r["url"] for r in results}
    for item in YOUTUBE_CURATED.get(category, []):
        if item["url"] not in existing_urls:
            clean = clean_description(item["title"], item["description"], category)
            results.append(build_resource(
                title=item["title"],
                url=item["url"],
                description=clean,
                platform="YouTube",
                category=category,
                level=item.get("level", "All Levels"),
            ))
    return results


# ─────────────────────────────────────────────
# SOURCE 2 — MIT OPENCOURSEWARE (open JSON feed)
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# SOURCE 2 — MIT OPENCOURSEWARE (curated free courses)
# Scraping blocked by proxy; using verified static course URLs
# ─────────────────────────────────────────────
MITOCW_CURATED = {
    "Programming & Computer Science": [
        {"title": "Introduction to Computer Science and Programming in Python", "url": "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/", "description": "MIT's foundational Python course covering computational thinking, algorithms, and problem solving. No prior programming experience needed."},
        {"title": "Introduction to Computational Thinking and Data Science", "url": "https://ocw.mit.edu/courses/6-0002-introduction-to-computational-thinking-and-data-science-fall-2016/", "description": "Continuation of MIT's intro CS sequence covering Python for optimization, simulation, and statistical thinking."},
        {"title": "A Gentle Introduction to Programming Using Python", "url": "https://ocw.mit.edu/courses/6-189-a-gentle-introduction-to-programming-using-python-january-iap-2011/", "description": "MIT IAP course introducing Python programming concepts to beginners with hands-on problem sets."},
    ],
    "Data Science AI": [
        {"title": "Introduction to Machine Learning", "url": "https://ocw.mit.edu/courses/6-867-machine-learning-fall-2006/", "description": "MIT's core machine learning course covering regression, classification, neural networks, and unsupervised methods."},
        {"title": "Probabilistic Systems Analysis and Applied Probability", "url": "https://ocw.mit.edu/courses/6-041-probabilistic-systems-analysis-and-applied-probability-fall-2010/", "description": "Rigorous MIT course on probability theory, random variables, and statistical inference — essential for data science."},
        {"title": "Statistics for Applications", "url": "https://ocw.mit.edu/courses/18-650-statistics-for-applications-fall-2016/", "description": "MIT statistics course covering estimation, hypothesis testing, regression, and machine learning fundamentals."},
    ],
    "Web Development": [
        {"title": "User Interface Design and Implementation", "url": "https://ocw.mit.edu/courses/6-831-user-interface-design-and-implementation-spring-2011/", "description": "MIT course on UI design principles, usability, and front-end implementation for interactive web applications."},
    ],
    "IT / Cybersecurity": [
        {"title": "Computer Systems Security", "url": "https://ocw.mit.edu/courses/6-858-computer-systems-security-fall-2014/", "description": "MIT's in-depth computer security course covering network security, cryptography, software vulnerabilities, and defenses."},
        {"title": "Network and Computer Security", "url": "https://ocw.mit.edu/courses/6-857-network-and-computer-security-spring-2014/", "description": "MIT course on cryptographic protocols, authentication, network security, and applied security engineering."},
    ],
    "UX Design": [
        {"title": "User Interface Design and Implementation", "url": "https://ocw.mit.edu/courses/6-831-user-interface-design-and-implementation-spring-2011/", "description": "MIT course on UI/UX principles, usability evaluation, and hands-on interface implementation."},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "System and Project Management", "url": "https://ocw.mit.edu/courses/1-040-project-management-spring-2009/", "description": "MIT engineering project management course covering planning, scheduling, risk management, and team coordination."},
        {"title": "Engineering Risk-Benefit Analysis", "url": "https://ocw.mit.edu/courses/esd-72-engineering-risk-benefit-analysis-spring-2007/", "description": "MIT course on decision-making under uncertainty, risk frameworks, and systems analysis for technology projects."},
    ],
}

def fetch_mit_ocw(category: str) -> list:
    log.info(f"[MIT OCW] Fetching: {category}")
    results = []
    for item in MITOCW_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="MIT OpenCourseWare",
            category=category,
        ))
    return results


# ─────────────────────────────────────────────
# SOURCE 3 — FREECODECAMP (GitHub public repo)
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# SOURCE 3 — FREECODECAMP (curated static links)
# Scraper returns generic /learn URL; using verified direct certification links
# ─────────────────────────────────────────────
FCC_CURATED = {
    "Programming & Computer Science": [
        {"title": "Scientific Computing with Python", "url": "https://www.freecodecamp.org/learn/python-v9/", "description": "freeCodeCamp's free Python certification covering variables, functions, data structures, OOP, and algorithms through project-based learning."},
        {"title": "Relational Databases", "url": "https://www.freecodecamp.org/learn/relational-databases-v9/", "description": "Learn PostgreSQL, Bash scripting, and relational database design through interactive projects in a Linux environment."},
    ],
    "Data Science AI": [
        {"title": "Data Analysis with Python", "url": "https://www.freecodecamp.org/learn/data-analysis-with-python/", "description": "freeCodeCamp's free data analysis certification covering NumPy, Pandas, Matplotlib, and data visualization techniques."},
        {"title": "Machine Learning with Python", "url": "https://www.freecodecamp.org/learn/machine-learning-with-python/", "description": "freeCodeCamp's free machine learning certification covering TensorFlow, neural networks, NLP, and reinforcement learning."},
    ],
    "Web Development": [
        {"title": "Responsive Web Design", "url": "https://www.freecodecamp.org/learn/responsive-web-design-v9/", "description": "freeCodeCamp's free web design certification covering HTML, CSS, Flexbox, Grid, and accessibility best practices."},
        {"title": "JavaScript Algorithms and Data Structures", "url": "https://www.freecodecamp.org/learn/javascript-v9/", "description": "freeCodeCamp's free JavaScript certification covering ES6, OOP, functional programming, and algorithm challenges."},
        {"title": "Front End Development Libraries", "url": "https://www.freecodecamp.org/learn/front-end-development-libraries-v9/", "description": "Learn Bootstrap, jQuery, Sass, React, and Redux through freeCodeCamp's free front-end certification program."},
        {"title": "Back End Development and APIs", "url": "https://www.freecodecamp.org/learn/back-end-development-and-apis-v9/", "description": "freeCodeCamp's free back-end certification covering Node.js, Express, MongoDB, and building REST APIs."},
        {"title": "Full Stack Developer", "url": "https://www.freecodecamp.org/learn/full-stack-developer-v9/", "description": "freeCodeCamp's comprehensive full-stack certification covering front-end, back-end, databases, and deployment."},
    ],
    "IT / Cybersecurity": [
        {"title": "Information Security", "url": "https://www.freecodecamp.org/learn/information-security/", "description": "freeCodeCamp's free information security certification covering HelmetJS, penetration testing, and secure application development."},
        {"title": "Foundational C# with Microsoft", "url": "https://www.freecodecamp.org/learn/foundational-c-sharp-with-microsoft/", "description": "Microsoft-partnered freeCodeCamp course teaching foundational C# programming for secure software development."},
    ],
    "UX Design": [
        {"title": "Responsive Web Design Certification", "url": "https://www.freecodecamp.org/learn/responsive-web-design-v9/", "description": "freeCodeCamp certification covering accessible, user-centered design with HTML and CSS. Includes real-world projects."},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "Coding Interview Prep", "url": "https://www.freecodecamp.org/learn/coding-interview-prep/", "description": "freeCodeCamp's comprehensive interview preparation covering algorithms, data structures, and project-based challenges."},
        {"title": "The Odin Project", "url": "https://www.freecodecamp.org/learn/the-odin-project/", "description": "Full-stack web development curriculum covering project planning, Git workflow, and agile development practices."},
    ],
}

def fetch_freecodecamp(category: str) -> list:
    log.info(f"[freeCodeCamp] Fetching: {category}")
    results = []
    for item in FCC_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="freeCodeCamp",
            category=category,
        ))
    return results


# ─────────────────────────────────────────────
# SOURCE 4 — MICROSOFT LEARN (public REST API)
# ─────────────────────────────────────────────
MS_KEYWORD_MAP = {
    "Programming & Computer Science":        "python programming",
    "Data Science AI":           "artificial intelligence machine learning",
    "Web Development":           "web development javascript",
    "IT / Cybersecurity":          "cybersecurity network security",
    "Project Management / Agile / Career Skills":  "project management agile scrum",
}

# Maps to official Microsoft Learn subject filter values
MS_SUBJECT_MAP = {
    "Programming & Computer Science":        "application-development",
    "Data Science AI":           "artificial-intelligence",
    "Web Development":           "application-development",
    "IT / Cybersecurity":          "security",
    "UX Design":                    "design",
    "Project Management / Agile / Career Skills":  "business-applications",
}

def fetch_microsoft_learn(category: str) -> list:
    log.info(f"[Microsoft Learn] Fetching: {category}")
    results  = []
    keyword  = MS_KEYWORD_MAP.get(category, category.lower())
    subject  = MS_SUBJECT_MAP.get(category, "")
    url      = "https://learn.microsoft.com/api/catalog/"
    params   = {
        "term":    keyword,
        "locale":  "en-us",
        "$top":    CONFIG["max_results_per_source"],
    }
    # Keywords that must appear in title or summary to be considered relevant
    MS_RELEVANCE_KEYWORDS = {
        "Programming & Computer Science":        ["python", "programming", "coding", "developer", "script"],
        "Data Science AI":           ["ai", "artificial intelligence", "machine learning", "data science", "deep learning", "neural", "nlp"],
        "Web Development":           ["web", "html", "css", "javascript", "frontend", "backend", "asp.net", "node"],
        "IT / Cybersecurity":          ["security", "cybersecurity", "threat", "zero trust", "identity", "compliance", "defender"],
        "UX Design":                     ["UX design", "user experience design", "UI UX design", "wireframing", "usability"],
        "Project Management / Agile / Career Skills":  ["project management", "agile", "scrum", "career skills", "workplace skills", "leadership"],
    }
    relevant_terms = MS_RELEVANCE_KEYWORDS.get(category, [])

    if subject:
        params["subject"] = subject
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("learningPaths", []) or data.get("modules", []) or data.get("results", [])
        for item in items[:CONFIG["max_results_per_source"] * 3]:  # fetch extra to filter
            title    = item.get("title", "")
            raw_desc = item.get("summary", "")
            # Relevance check — skip if title+desc don't mention any relevant terms
            combined = (title + " " + raw_desc).lower()
            if relevant_terms and not any(t in combined for t in relevant_terms):
                log.debug(f"[Microsoft Learn] Skipping irrelevant: '{title}'")
                continue
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
            if len(results) >= CONFIG["max_results_per_source"]:
                break
    except Exception as e:
        log.error(f"[Microsoft Learn] Error for '{category}': {e}")
    return results


# ─────────────────────────────────────────────
# SOURCE 5 — AWS SKILL BUILDER (public catalog)
# ─────────────────────────────────────────────
# SOURCE 5 — AWS SKILL BUILDER (curated free courses)
# JS-rendered site — static curated list of verified free courses
# ─────────────────────────────────────────────
AWS_CURATED = {
    "Programming & Computer Science": [
        {"title": "AWS Cloud Practitioner Essentials", "url": "https://skillbuilder.aws/search?searchText=aws-cloud-practitioner-essentials", "description": "Introduction to AWS cloud concepts and core services. Includes hands-on labs covering automation and scripting fundamentals for cloud environments."},
        {"title": "AWS Technical Essentials", "url": "https://skillbuilder.aws/search?searchText=aws-technical-essentials", "description": "Foundational AWS course covering core services, infrastructure, and the basics of cloud-based application development and automation."},
    ],
    "Data Science AI": [
        {"title": "Practical Data Science with Amazon SageMaker", "url": "https://skillbuilder.aws/search?searchText=practical-data-science-with-amazon-sagemaker", "description": "Hands-on data science using Amazon SageMaker for building, training, and deploying machine learning models at scale."},
        {"title": "AWS Machine Learning Foundations", "url": "https://skillbuilder.aws/search?searchText=machine-learning-foundations", "description": "Core machine learning concepts including supervised learning, model evaluation, and ML pipelines using AWS services."},
        {"title": "AWS Well-Architected for Machine Learning", "url": "https://skillbuilder.aws/search?searchText=well-architected-for-machine-learning", "description": "Best practices for designing and operating reliable, cost-effective ML workloads on AWS infrastructure."},
    ],
    "Web Development": [
        {"title": "Developing on AWS", "url": "https://skillbuilder.aws/search?searchText=developing-on-aws", "description": "Build cloud-native web applications using AWS SDKs, APIs, Lambda, and developer tools for modern web architectures."},
        {"title": "AWS Cloud Quest: Cloud Practitioner", "url": "https://skillbuilder.aws/search?searchText=aws-cloud-quest-cloud-practitioner", "description": "Gamified, hands-on learning for building and deploying cloud applications and web services on AWS. Free to play."},
    ],
    "IT / Cybersecurity": [
        {"title": "AWS Security Fundamentals", "url": "https://skillbuilder.aws/search?searchText=aws-security-fundamentals", "description": "Core AWS security concepts covering IAM, data encryption, network security, monitoring, and compliance frameworks."},
        {"title": "AWS Security Best Practices", "url": "https://skillbuilder.aws/search?searchText=security-best-practices-in-aws", "description": "Advanced security engineering practices for protecting AWS infrastructure, workloads, and data at rest and in transit."},
        {"title": "AWS Identity and Access Management (IAM) Foundations", "url": "https://skillbuilder.aws/search?searchText=aws-iam-identity-and-access-management", "description": "Deep dive into AWS IAM for controlling access to services and resources, managing policies, roles, and permissions securely."},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "AWS Cloud Adoption Framework Essentials", "url": "https://skillbuilder.aws/search?searchText=aws-cloud-adoption-framework-essentials", "description": "Strategic framework for planning and executing cloud adoption projects using structured agile methodology guidance."},
        {"title": "AWS Well-Architected Foundations", "url": "https://skillbuilder.aws/search?searchText=aws-well-architected-foundations", "description": "Best practices for designing, reviewing, and managing reliable, efficient, and cost-effective cloud projects and workloads."},
    ],
}

def fetch_aws(category: str) -> list:
    log.info(f"[AWS] Fetching: {category}")
    results = []
    for item in AWS_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="AWS Skill Builder",
            category=category,
        ))
    return results


# ─────────────────────────────────────────────
# SOURCE 6 — COURSERA (curated free-to-audit courses)
# Public API returns 405 — using curated list of verified auditable courses
# ─────────────────────────────────────────────
COURSERA_CURATED = {
    "Programming & Computer Science": [
        {"title": "Python for Everybody Specialization", "url": "https://www.coursera.org/specializations/python", "description": "Learn to program and analyze data with Python from University of Michigan. Free to audit."},
        {"title": "Crash Course on Python — Google", "url": "https://www.coursera.org/learn/python-crash-course", "description": "Google's beginner Python course covering automation, scripting, and practical programming. Free to audit."},
        {"title": "Python Basics — University of Michigan", "url": "https://www.coursera.org/learn/python-basics", "description": "Core Python programming concepts including data types, loops, functions, and file handling. Free to audit."},
        {"title": "Using Python to Interact with the Operating System", "url": "https://www.coursera.org/learn/python-operating-system", "description": "Google's course on using Python for OS automation, file handling, regular expressions, and process management. Free to audit."},
    ],
    "Data Science AI": [
        {"title": "IBM Data Science Professional Certificate", "url": "https://www.coursera.org/professional-certificates/ibm-data-science", "description": "Comprehensive data science program covering Python, SQL, machine learning, and data visualization. Free to audit."},
        {"title": "Machine Learning Specialization — Andrew Ng", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "description": "Stanford and DeepLearning.AI's foundational ML course covering supervised, unsupervised, and reinforcement learning. Free to audit."},
        {"title": "Deep Learning Specialization — Andrew Ng", "url": "https://www.coursera.org/specializations/deep-learning", "description": "Master deep learning, neural networks, and AI applications with hands-on projects. Free to audit."},
        {"title": "Google Data Analytics Certificate", "url": "https://www.coursera.org/professional-certificates/google-data-analytics", "description": "Google's professional data analytics program covering analysis, visualization, and SQL. Free to audit."},
    ],
    "Web Development": [
        {"title": "HTML, CSS, and Javascript for Web Developers", "url": "https://www.coursera.org/learn/html-css-javascript-for-web-developers", "description": "Johns Hopkins University course on frontend web development fundamentals. Free to audit."},
        {"title": "Full-Stack Web Development with React", "url": "https://www.coursera.org/specializations/full-stack-react", "description": "Build complete web applications using React, Node.js, and MongoDB from Hong Kong University. Free to audit."},
        {"title": "Meta Front-End Developer Certificate", "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer", "description": "Meta's professional front-end development program covering React, HTML, CSS, and JavaScript. Free to audit."},
    ],
    "IT / Cybersecurity": [
        {"title": "Google Cybersecurity Certificate", "url": "https://www.coursera.org/professional-certificates/google-cybersecurity", "description": "Google's professional cybersecurity program covering threat detection, network security, and incident response. Free to audit."},
        {"title": "IBM Cybersecurity Analyst Certificate", "url": "https://www.coursera.org/professional-certificates/ibm-cybersecurity-analyst", "description": "IBM's cybersecurity analyst training covering security tools, threat intelligence, and compliance. Free to audit."},
        {"title": "Introduction to Cyber Security Specialization", "url": "https://www.coursera.org/specializations/intro-cyber-security", "description": "NYU's foundational cybersecurity specialization covering cyber attacks, defenses, and cryptography. Free to audit."},
    ],
    "UX Design": [
        {"title": "Google UX Design Certificate", "url": "https://www.coursera.org/professional-certificates/google-ux-design", "description": "Google's professional UX design certificate covering the full design process: empathize, define, ideate, prototype, and test. Free to audit."},
        {"title": "UI / UX Design Specialization", "url": "https://www.coursera.org/specializations/ui-ux-design", "description": "CalArts specialization covering interface design, visual design, and UX research fundamentals. Free to audit."},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "Google Project Management Certificate", "url": "https://www.coursera.org/professional-certificates/google-project-management", "description": "Google's professional project management program covering Agile, Scrum, and traditional PM methods. Free to audit."},
        {"title": "Agile with Atlassian Jira", "url": "https://www.coursera.org/learn/agile-atlassian-jira", "description": "Practical Agile project management using Jira from Atlassian. Covers sprints, backlogs, and Kanban. Free to audit."},
        {"title": "Engineering Project Management Specialization", "url": "https://www.coursera.org/specializations/engineering-project-management", "description": "Rice University's project management specialization covering scope, schedule, risk, and Agile methods. Free to audit."},
        {"title": "Foundations of Digital Marketing and E-commerce", "url": "https://www.coursera.org/learn/foundations-of-digital-marketing-and-e-commerce", "description": "Google's digital marketing course covering SEO, web analytics, social media, and e-commerce fundamentals. Free to audit."},
    ],
}

def fetch_coursera(category: str) -> list:
    log.info(f"[Coursera] Fetching: {category}")
    results = []
    for item in COURSERA_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="Coursera",
            category=category,
        ))
    return results


# ─────────────────────────────────────────────
# SOURCE 7 — STANFORD ONLINE (curated free courses)
# Site returns 403 on scraping — using curated list with direct filter URLs provided
# ─────────────────────────────────────────────
STANFORD_CURATED = {
    "Programming & Computer Science": [
        {"title": "Code in Place — Stanford", "url": "https://codeinplace.stanford.edu/", "description": "Stanford's free introductory Python programming course taught by CS106A instructors. Beginner-friendly."},
        {"title": "Computer Science 101 — Stanford", "url": "https://www.edx.org/learn/computer-science/stanford-university-computer-science-101", "description": "Stanford's introductory computer science course covering programming fundamentals and computational thinking. Free to audit on edX.", "platform_override": "edX"},
    ],
    "Data Science AI": [
        {"title": "Machine Learning — CS229", "url": "https://see.stanford.edu/course/cs229", "description": "Stanford's renowned machine learning course covering supervised learning, unsupervised learning, neural networks, and AI foundations."},
        {"title": "Machine Learning Specialization", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "description": "Stanford and DeepLearning.AI's comprehensive ML specialization covering supervised, unsupervised, and reinforcement learning. Free to audit.", "platform_override": "Coursera", "level": "Intermediate"},
        {"title": "Statistical Learning with R", "url": "https://www.edx.org/learn/statistics/stanford-university-statistical-learning", "description": "Comprehensive introduction to statistical learning and data mining with R, based on the textbook ISLR. Free to audit.", "platform_override": "edX", "level": "Beginner"},
    ],
    "Web Development": [
        {"title": "Databases: Relational Databases and SQL", "url": "https://www.edx.org/learn/relational-databases/stanford-university-databases-relational-databases-and-sql", "description": "Stanford's self-paced SQL and relational databases course. Free to audit on edX — essential for backend web development.", "platform_override": "edX"},
        {"title": "Generative AI: Technology, Business and Society", "url": "https://online.stanford.edu/courses/xfm100-generative-ai-technology-business-and-society-program-preview", "description": "Stanford's program exploring generative AI's impact on technology, business, and society. Covers practical applications and implications."},
    ],
    "IT / Cybersecurity": [
        {"title": "Cryptography I", "url": "https://www.coursera.org/learn/crypto", "description": "Stanford's cryptography course covering symmetric and asymmetric encryption, message authentication, and security protocols. Free to audit.", "platform_override": "Coursera", "level": "All Levels"},
        {"title": "Introduction to Internet of Things", "url": "https://online.stanford.edu/courses/xee100-introduction-internet-things", "description": "Stanford's beginner-friendly introduction to IoT devices, sensors, connectivity, and embedded systems design. Free.", "level": "Beginner"},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "Organizational Analysis — Stanford", "url": "https://www.coursera.org/learn/organizational-analysis", "description": "Stanford course on organizational design and management practices applicable to tech project leadership. Free to audit on Coursera."},
        {"title": "Generative AI: Technology, Business and Society", "url": "https://online.stanford.edu/courses/xfm100-generative-ai-technology-business-and-society-program-preview", "description": "Stanford's program on managing AI initiatives across technology and business contexts, covering strategy and governance."},
    ],
}

def fetch_stanford(category: str) -> list:
    log.info(f"[Stanford Online] Fetching: {category}")
    results = []
    for item in STANFORD_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        platform = item.get("platform_override", "Stanford Online")
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform=platform,
            category=category,
        ))
    return results


# ─────────────────────────────────────────────
# SOURCE 8 — IBM SKILLSBUILD (curated free courses)
# Correct URL pattern: skillsbuild.org/students/course-catalog/[topic]
# ─────────────────────────────────────────────
IBM_CURATED = {
    "Programming & Computer Science": [
        {"title": "Information Technology Fundamentals", "url": "https://students.yourlearning.ibm.com/activity/PLAN-189E4B1AF551?channelId=CNL_LCB_1669759135880&utm_source=skillsbuild.org", "description": "Learn the history of computing and essential concepts about computer parts, network connections, hardware, software, security, and troubleshooting, with hands-on practice.", "level": "Beginner"},
        {"title": "Introduction to IT", "url": "https://students.yourlearning.ibm.com/activity/URL-A50A91D08ADC?channelId=CNL_LCB_1669759135880&utm_source=skillsbuild.org", "description": "Beginner overview of the growing IT industry covering foundational concepts as companies become increasingly technology-dependent.", "level": "Beginner"},
        {"title": "Explore Emerging Tech", "url": "https://students.yourlearning.ibm.com/activity/PLAN-AB0C4887AB43", "description": "Introduction to five key emerging technologies transforming industries and creating new career opportunities. No prior tech experience required.", "level": "Beginner"},
        {"title": "Quantum Computing", "url": "https://students.yourlearning.ibm.com/channel/CNL_LCB_1596832013328?utm_source=skillsbuild.org", "description": "Explore how quantum computers use principles of quantum physics rather than traditional logic to solve complex problems in seconds.", "level": "Intermediate"},
    ],
    "Data Science AI": [
        {"title": "AI Foundations", "url": "https://students.yourlearning.ibm.com/activity/PLAN-B2125F145F0E?utm_source=skillsbuild.org", "description": "Foundational AI course created by ISTE and IBM covering AI concepts, applications, and ethics. Designed for high school students and career beginners.", "level": "Beginner"},
        {"title": "Artificial Intelligence Fundamentals", "url": "https://students.yourlearning.ibm.com/activity/PLAN-CC702B39D429?utm_source=skillsbuild.org", "description": "Explore AI history and how it is changing the world. Visualize yourself in an AI career while learning core machine learning and AI concepts.", "level": "All Levels"},
        {"title": "Build Your Own Chatbot", "url": "https://students.yourlearning.ibm.com/activity/SN-COURSE-V1:IBMDEVELOPERSKILLSNETWORK+CB0101EN+V1?utm_source=skillsbuild.org", "description": "Practical introduction to planning, building, and deploying your first AI-powered customer support chatbot using IBM tools.", "level": "All Levels"},
        {"title": "Data Fundamentals", "url": "https://students.yourlearning.ibm.com/activity/PLAN-0EC2BCEA3C39?utm_source=skillsbuild.org", "description": "Learn data science concepts and methods with hands-on practice cleaning, refining, and visualizing data to discover meaningful insights.", "level": "Beginner"},
        {"title": "Data Science Foundations", "url": "https://students.yourlearning.ibm.com/activity/PLAN-F0DF852C4003?utm_source=skillsbuild.org", "description": "Comprehensive data science path covering analysis, visualization, and machine learning concepts through IBM's free learning platform.", "level": "All Levels"},
    ],
    "Web Development": [
        {"title": "Web Development Fundamentals", "url": "https://students.yourlearning.ibm.com/activity/PLAN-43A030B97485?utm_source=skillsbuild.org", "description": "Learn the languages, tools, and processes used to build websites with hands-on practice covering HTML, CSS, JavaScript, and modern frameworks.", "level": "All Levels"},
        {"title": "Cloud Computing Fundamentals", "url": "https://students.yourlearning.ibm.com/activity/PLAN-58FA14F64C9B?utm_source=skillsbuild.org", "description": "Learn cloud computing basics including service models, deployment models, and the many ways businesses benefit from cloud technology.", "level": "All Levels"},
        {"title": "Introduction to Cloud", "url": "https://students.yourlearning.ibm.com/activity/PLAN-4EB23B51588C?utm_source=skillsbuild.org", "description": "Core cloud computing concepts from both business and practitioner perspectives. Foundational knowledge for understanding modern cloud infrastructure.", "level": "Beginner"},
        {"title": "IBM Cloud Essentials", "url": "https://students.yourlearning.ibm.com/activity/PLAN-0F5CA76EE206?utm_source=skillsbuild.org", "description": "Introduction to IBM Cloud offerings and services — the most open and secure public cloud for developers and enterprises.", "level": "All Levels"},
    ],
    "UX Design": [
        {"title": "User Experience Design Fundamentals", "url": "https://students.yourlearning.ibm.com/activity/PLAN-44E67AF54225?focuslmsId=CREDLY-ae2e453d-5311-41a0-be95-b217e0c4670f&utm_source=skillsbuild.org", "description": "Learn UX design concepts and the full design process for crafting digital products that are intuitive, user-friendly, and visually appealing.", "level": "All Levels"},
    ],
    "IT / Cybersecurity": [
        {"title": "Cybersecurity Fundamentals", "url": "https://students.yourlearning.ibm.com/activity/PLAN-805005E992EA?utm_source=skillsbuild.org", "description": "Introduction to cybersecurity covering cyberattackers, their tactics, social engineering, and high-profile case studies from offense and defense perspectives.", "level": "All Levels"},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "Agile Explorer", "url": "https://students.yourlearning.ibm.com/activity/PLAN-0BD5AD484E32?utm_source=skillsbuild.org", "description": "Learn Agile values, principles, and practices that help teams become more innovative and adaptive instead of using linear, inflexible work methods.", "level": "All Levels"},
        {"title": "Design Thinking - Getting Started", "url": "https://students.yourlearning.ibm.com/channel/CNL_LCB_1565755450471?utm_source=skillsbuild.org", "description": "IBM's design thinking framework used by businesses and startups worldwide to solve problems and drive innovation. Applicable to any career path.", "level": "All Levels"},
        {"title": "Customer Engagement Fundamentals", "url": "https://students.yourlearning.ibm.com/activity/PLAN-F77885B0DEE9", "description": "Covers IT customer service and support — one of the highest-demand job areas. Learn skills for customer engagement and support agent roles.", "level": "All Levels"},
        {"title": "Workplace Skills - Helping You Succeed at Work", "url": "https://students.yourlearning.ibm.com/channel/CNL_LCB_1617287332624?utm_source=skillsbuild.org", "description": "Build the many skills needed to find a job and succeed at work, from handling challenges gracefully to seizing career opportunities.", "level": "All Levels"},
        {"title": "Internships - Get a Head Start on Your Career", "url": "https://students.yourlearning.ibm.com/channel/CNL_LCB_1614191131555?utm_source=skillsbuild.org", "description": "Practical guidance on internships for students covering career exploration, skill development, and professional work experience.", "level": "Beginner"},
        {"title": "Lifelong Professional Skills", "url": "https://students.yourlearning.ibm.com/activity/PLAN-EBB88B2618A4?utm_source=skillsbuild.org", "description": "Core capabilities for personal and team success in today's workplace, helping professionals grow as well-rounded, confident contributors.", "level": "Beginner"},
    ],
}

def fetch_ibm(category: str) -> list:
    log.info(f"[IBM SkillsBuild] Fetching: {category}")
    results = []
    for item in IBM_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="IBM SkillsBuild",
            category=category,
            level=item.get("level", "All Levels"),
        ))
    return results


# ─────────────────────────────────────────────
# SOURCE 9 — GOOGLE (curated free courses)
# JS-rendered sites; using verified static course URLs
# ─────────────────────────────────────────────
GOOGLE_CURATED = {
    "Programming & Computer Science": [
        {"title": "Crash Course on Python", "url": "https://www.coursera.org/learn/python-crash-course", "description": "Google's beginner Python course covering variables, data structures, loops, functions, and automation scripting. Free to audit on Coursera."},
    ],
    "Data Science AI": [
        {"title": "Google Data Analytics Certificate", "url": "https://grow.google/certificates/data-analytics/", "description": "Google's professional data analytics program covering spreadsheets, SQL, Tableau, and R for data-driven decision making."},
        {"title": "Google Advanced Data Analytics Certificate", "url": "https://grow.google/certificates/advanced-data-analytics/", "description": "Advanced Google program covering Python, statistics, regression, machine learning, and data storytelling for analysts."},
        {"title": "Google AI Essentials", "url": "https://grow.google/certificates/ai-essentials/", "description": "Google's free foundational AI course covering how to use AI tools responsibly and effectively in the workplace."},
    ],
    "Web Development": [
        {"title": "Google UX Design Certificate", "url": "https://grow.google/certificates/ux-design/", "description": "Google's UX design program covering user research, wireframing, prototyping, and designing accessible web experiences."},
    ],
    "IT / Cybersecurity": [
        {"title": "Google Cybersecurity Certificate", "url": "https://grow.google/certificates/cybersecurity/", "description": "Google's professional cybersecurity program covering threat detection, network security, incident response, and Python automation."},
        {"title": "Google IT Support Certificate", "url": "https://grow.google/certificates/it-support/", "description": "Google's foundational IT program covering networking, operating systems, security, and troubleshooting. Earns a Coursera certificate."},
    ],
    "UX Design": [
        {"title": "Google UX Design Certificate", "url": "https://grow.google/certificates/ux-design/", "description": "Google's career certificate covering UX foundations, wireframing, prototyping, and user research. Free to audit on Coursera."},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "Google Project Management Certificate", "url": "https://grow.google/certificates/project-management/", "description": "Google's professional PM program covering Agile, Scrum, project planning, risk management, and stakeholder communication."},
        {"title": "Google Digital Marketing & E-commerce Certificate", "url": "https://grow.google/certificates/digital-marketing-ecommerce/", "description": "Google's program covering campaign management, analytics, and project execution for digital marketing initiatives."},
    ],
}

def fetch_google(category: str) -> list:
    log.info(f"[Google] Fetching: {category}")
    results = []
    for item in GOOGLE_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="Google",
            category=category,
        ))
    return results


# ─────────────────────────────────────────────
# SOURCE 10 — UNIVERSITY OF HELSINKI MOOC (curated)
# ─────────────────────────────────────────────
HELSINKI_CURATED = {
    "Programming & Computer Science": [
        {"title": "Java Programming I & II", "url": "https://java-programming.mooc.fi/", "description": "University of Helsinki's comprehensive Java programming course covering OOP, algorithms, and data structures. Completely free, no registration required.", "level": "Beginner"},
        {"title": "Python Programming MOOC", "url": "https://programming-26.mooc.fi/", "description": "University of Helsinki's full Python course covering basics through advanced OOP, file handling, and data processing. Completely free and self-paced.", "level": "Beginner"},
        {"title": "Test-Driven Development", "url": "https://tdd.mooc.fi/", "description": "University of Helsinki's advanced course on TDD practices, clean code, and refactoring using modern software engineering techniques. Free.", "level": "Advanced"},
        {"title": "Applied Language Technology", "url": "https://applied-language-technology.mooc.fi/html/index.html", "description": "University of Helsinki's introduction to natural language processing and computational linguistics using Python. Free and self-paced.", "level": "Beginner"},
        {"title": "Hands-on Scientific Computing", "url": "https://handsonscicomp.readthedocs.io/en/latest/", "description": "University of Helsinki's practical guide to scientific computing covering Linux, Python, data tools, and HPC workflows. Free.", "level": "All Levels"},
        {"title": "Computing and Society", "url": "https://courses.mooc.fi/org/uh-cs/courses/computing-and-society-an-introduction-2025-2026", "description": "University of Helsinki's introduction to how computing shapes society, covering digital infrastructure, ethics, and technology's social impact. Free.", "level": "All Levels"},
    ],
    "Data Science AI": [
        {"title": "Introduction to AI", "url": "https://course.elementsofai.com/", "description": "University of Helsinki's globally popular introduction to AI concepts, applications, and limitations. No programming required. Free certificate available.", "level": "All Levels"},
        {"title": "Building AI", "url": "https://buildingai.elementsofai.com/", "description": "University of Helsinki's follow-up covering practical AI building techniques, Python basics, and machine learning methods. Free.", "level": "All Levels"},
        {"title": "Data Analysis with Python", "url": "https://courses.mooc.fi/org/uh-cs/courses/data-analysis-with-python-2024-2025", "description": "University of Helsinki course covering data analysis with NumPy, Pandas, and visualization libraries. Free and self-paced.", "level": "Intermediate"},
        {"title": "Big Data Platforms", "url": "https://big-data-platforms-25.mooc.fi/", "description": "University of Helsinki's advanced course on big data frameworks, cloud computing, and scalable data processing architectures. Free.", "level": "Advanced"},
        {"title": "AI in Society", "url": "https://courses.mooc.fi/org/uh-cs/courses/ai-in-society", "description": "University of Helsinki course exploring how AI affects society, policy, ethics, and everyday life. No technical background required. Free.", "level": "All Levels"},
        {"title": "Ethics of AI", "url": "https://ethics-of-ai.mooc.fi/", "description": "University of Helsinki's dedicated course on the ethical dimensions of AI including fairness, accountability, and societal implications. Free.", "level": "All Levels"},
    ],
    "Web Development": [
        {"title": "Full Stack Open", "url": "https://fullstackopen.com/en/", "description": "University of Helsinki's comprehensive modern web dev curriculum: React, Node.js, MongoDB, GraphQL, and TypeScript. Industry-standard, completely free.", "level": "Intermediate"},
    ],
    "IT / Cybersecurity": [
        {"title": "Cyber Security Base", "url": "https://cybersecuritybase.mooc.fi/", "description": "University of Helsinki's cybersecurity series covering web security, vulnerabilities, cryptography, and ethical hacking. Free, created with F-Secure.", "level": "All Levels"},
        {"title": "Introduction to the Internet of Things", "url": "https://courses.mooc.fi/org/uh-cs/courses/introduction-to-the-internet-of-things-mooc-2025-2026", "description": "University of Helsinki's beginner-friendly introduction to IoT devices, connectivity, sensors, and embedded systems. Free.", "level": "Beginner"},
        {"title": "Core 5G and Beyond", "url": "https://courses.mooc.fi/org/uh-cs/courses/5g-mooc", "description": "University of Helsinki course on 5G network architecture, standards, and next-generation wireless communication technologies. Free.", "level": "Intermediate"},
    ],
    "UX Design": [
        {"title": "Computing and Society", "url": "https://courses.mooc.fi/org/uh-cs/courses/computing-and-society-an-introduction-2025-2026", "description": "University of Helsinki course on how technology shapes human experience, digital ethics, and user-centered design thinking. Free.", "level": "All Levels"},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "DevOps with Docker", "url": "https://devopswithdocker.com/", "description": "University of Helsinki's hands-on Docker and containerization course covering deployment pipelines and orchestration. Free and self-paced.", "level": "Intermediate"},
        {"title": "DevOps with Kubernetes", "url": "https://courses.mooc.fi/org/uh-cs/courses/devops-with-kubernetes", "description": "University of Helsinki's intermediate course on Kubernetes orchestration, scaling, and managing containerized applications in production. Free.", "level": "Intermediate"},
    ],
}


def fetch_helsinki(category: str) -> list:
    log.info(f"[Helsinki MOOC] Fetching: {category}")
    results = []
    for item in HELSINKI_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="Helsinki MOOC",
            category=category,
            level=item.get("level", "All Levels"),
        ))
    return results


# ─────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# SOURCE 11 — KHAN ACADEMY (curated free courses)
# All Khan Academy courses are completely free, no account required
# ─────────────────────────────────────────────
KHAN_CURATED = {
    "Programming & Computer Science": [
        {"title": "Intro to Computer Science - Python", "url": "https://www.khanacademy.org/computing/intro-to-python-fundamentals", "description": "Khan Academy's beginner Python course covering variables, functions, loops, and core programming fundamentals. Completely free.", "level": "Beginner"},
        {"title": "Computer Programming - JavaScript and the Web", "url": "https://www.khanacademy.org/computing/computer-programming", "description": "Interactive JavaScript and web programming course covering HTML, CSS, animations, and databases. Learn by doing in the browser.", "level": "All Levels"},
        {"title": "AP College Computer Science Principles", "url": "https://www.khanacademy.org/computing/ap-computer-science-principles", "description": "College-level computer science covering algorithms, the internet, data, and programming. Aligned to the AP CS Principles exam.", "level": "Beginner"},
        {"title": "Computer Science Theory", "url": "https://www.khanacademy.org/computing/computer-science", "description": "Advanced CS theory covering algorithms, cryptography, information theory, and the mathematical foundations of computer science.", "level": "Advanced"},
    ],
    "IT / Cybersecurity": [
        {"title": "Computers and the Internet", "url": "https://www.khanacademy.org/computing/computers-and-internet", "description": "Beginner-friendly introduction to how computers work, how the internet functions, and the basics of cybersecurity and digital citizenship.", "level": "Beginner"},
    ],
}

def fetch_khan(category: str) -> list:
    log.info(f"[Khan Academy] Fetching: {category}")
    results = []
    for item in KHAN_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="Khan Academy",
            category=category,
            level=item.get("level", "All Levels"),
        ))
    return results


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
    fetch_helsinki,
    fetch_khan,
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
