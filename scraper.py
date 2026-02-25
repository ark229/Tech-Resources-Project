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
  - Stanford Online (public course listings)

Categories:
  - Python / Programming
  - Data Science / AI
  - Web Development
  - IT / Cybersecurity
  - UX Design
  - Project Management / Agile / Career Skills
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
        {"title": "AWS Cloud Practitioner Essentials", "url": "https://skillbuilder.aws/learn/94T2BEN85A/aws-cloud-practitioner-essentials/8D79F3AVR7", "description": "Introduction to AWS cloud concepts, core services, and global infrastructure. The starting point for any AWS learning journey.", "level": "Beginner"},
        {"title": "AWS Technical Essentials", "url": "https://skillbuilder.aws/learn/K8C2FNZM6X/aws-technical-essentials/N7Q3SXQCDY", "description": "Foundational AWS course covering core services, infrastructure, and the basics of cloud-based application development.", "level": "Beginner"},
        {"title": "Introduction to AWS Solutions", "url": "https://skillbuilder.aws/learn/FH7PU4852Z/introduction-to-aws-solutions/RGZ7RBAJD9", "description": "Overview of AWS solution categories and how cloud services can be combined to solve real-world technical challenges.", "level": "Beginner"},
        {"title": "Building Games with AWS Services", "url": "https://skillbuilder.aws/learn/72B872B4H2/building-games-with-aws-services/4GUU1DZK1G", "description": "Hands-on introduction to building games using AWS cloud services including compute, storage, and multiplayer backends.", "level": "Beginner"},
        {"title": "Getting Started with DevOps on AWS", "url": "https://skillbuilder.aws/learn/R4B13K95YQ/getting-started-with-devops-on-aws/38NHHYRV1R", "description": "Introduction to DevOps practices on AWS covering CI/CD pipelines, automation, infrastructure as code, and deployment strategies.", "level": "Beginner"},
        {"title": "Developer Learning Plan (includes Labs)", "url": "https://skillbuilder.aws/learning-plan/2MB11RS27E/developer-learning-plan-includes-labs/BT3ARXRZY3", "description": "Comprehensive developer learning path covering AWS SDKs, serverless, APIs, and hands-on labs for building cloud applications.", "level": "Advanced"},
        {"title": "Deploying Serverless Applications", "url": "https://skillbuilder.aws/learn/M531VCW415/deploying-serverless-applications/SMY21G7FYZ", "description": "Learn to build and deploy serverless applications using AWS Lambda, API Gateway, and related services.", "level": "Intermediate"},
        {"title": "AWS Solutions Architect - Fundamentals of Architecting on AWS", "url": "https://skillbuilder.aws/learn/ACYHAC5Q6K/aws-solutions-architect--fundamentals-of-architecting-on-aws/HNFECXKH8Q", "description": "Foundational architecting concepts for designing scalable, reliable, and cost-effective solutions on AWS.", "level": "Intermediate"},
    ],
    "Data Science AI": [
        {"title": "Introduction to Amazon SageMaker", "url": "https://skillbuilder.aws/learn/E1TZFJG8AG/introduction-to-amazon-sagemaker/GK2ESQYCR3", "description": "Beginner introduction to Amazon SageMaker for building, training, and deploying machine learning models on AWS.", "level": "Beginner"},
        {"title": "AWS Foundations: Machine Learning Basics", "url": "https://skillbuilder.aws/learn/5F9VWPE59T/aws-foundations-machine-learning-basics/3MPXBM59YU", "description": "Core machine learning concepts including supervised learning, model evaluation, and ML pipelines using AWS services.", "level": "Beginner"},
        {"title": "Machine Learning - Learning Plan", "url": "https://skillbuilder.aws/learning-plan/MVQZ8QE1WJ/machine-learning-learning-plan/2PW43AVTYR", "description": "Structured AWS learning path covering the full machine learning workflow from data preparation to model deployment.", "level": "Beginner"},
        {"title": "Developing Generative Artificial Intelligence Solutions", "url": "https://skillbuilder.aws/learn/PWJCMNXWHT/developing-generative-artificial-intelligence-solutions/JFB95SXNPF", "description": "Build generative AI applications on AWS using foundation models, Amazon Bedrock, and responsible AI practices.", "level": "Beginner"},
        {"title": "Responsible AI Practices on AWS", "url": "https://skillbuilder.aws/learning-plan/DE7RY2BTMR/responsible-ai-practices-on-aws/7F3XMDWRBM", "description": "Advanced course on building ethical, fair, and accountable AI systems using AWS tools and governance frameworks.", "level": "Advanced"},
        {"title": "Planning a Generative AI Project", "url": "https://skillbuilder.aws/learn/HU1FQRGDDZ/planning-a-generative-ai-project/SYR3SCPSHC", "description": "Learn how to scope, plan, and evaluate generative AI projects including use case selection and risk assessment.", "level": "Beginner"},
        {"title": "Making Better Decisions with Data for Small Business Owners", "url": "https://skillbuilder.aws/learn/AV6CRJ8AP1/making-better-decisions-with-data-for-small-business-owners/RAXPG2AXAC", "description": "Practical data-driven decision making for small business owners using AWS analytics and business intelligence tools.", "level": "Beginner"},
        {"title": "Data Engineering on AWS - Foundations", "url": "https://skillbuilder.aws/learn/6BP61KB1FJ/data-engineering-on-aws--foundations/KXCN4PJD9Y", "description": "Foundational data engineering concepts covering AWS data pipelines, storage, transformation, and analytics services.", "level": "Beginner"},
        {"title": "Data Analytics Learning Plan", "url": "https://skillbuilder.aws/learning-plan/J38YWQY59M/data-analytics-learning-plan-includes-labs/Z2QZR9T77Q", "description": "Comprehensive learning path for AWS data analytics covering data lakes, warehousing, visualization, and hands-on labs.", "level": "Beginner"},
    ],
    "Web Development": [
        {"title": "AWS Cloud Quest: Cloud Practitioner", "url": "https://skillbuilder.aws/learn/FU5WCYVGKY/aws-cloud-quest-cloud-practitioner/JF9TKU68GT", "description": "Gamified, hands-on cloud learning game for building and deploying cloud applications and web services on AWS.", "level": "Beginner"},
        {"title": "AWS Well-Architected Foundations", "url": "https://skillbuilder.aws/learn/U89MJTNSM8/aws-wellarchitected-foundations/RCY5NFM8R9", "description": "Best practices for designing reliable, secure, and cost-effective architectures using the AWS Well-Architected Framework.", "level": "Intermediate"},
        {"title": "Building Your Agentic Applications the Well-Architected Way", "url": "https://skillbuilder.aws/learn/R44Y8PRVRW/building-your-agentic-applications-the-wellarchitected-way/8W5HD7KWJ4", "description": "Design and build AI agent applications on AWS following Well-Architected best practices for reliability and security.", "level": "Intermediate"},
        {"title": "Cloud for Small Business Owners", "url": "https://skillbuilder.aws/learn/EMN6QJSA7Q/cloud-for-small-business-owners/7PXBKPD8RJ", "description": "Beginner-friendly introduction to cloud computing benefits, AWS services, and how to get started as a small business.", "level": "Beginner"},
    ],
    "IT / Cybersecurity": [
        {"title": "AWS Security Fundamentals", "url": "https://skillbuilder.aws/learn/S2N5PM41ZK/aws-security-fundamentals-second-edition/E71QQGTCRZ", "description": "Core AWS security concepts covering IAM, data encryption, network security, monitoring, and compliance frameworks.", "level": "Intermediate"},
        {"title": "Introduction to AWS Identity and Access Management (IAM)", "url": "https://skillbuilder.aws/learn/M1QWQ1MURQ/introduction-to-aws-identity-and-access-management-iam/W4W2NQF2AR", "description": "Beginner introduction to AWS IAM for controlling access to services and resources, managing policies, roles, and permissions.", "level": "Beginner"},
        {"title": "AWS Security - Encryption Fundamentals", "url": "https://skillbuilder.aws/learn/F3VJ5VSAK6/aws-security--encryption-fundamentals/CZREZ5H8QM", "description": "Introduction to encryption concepts and AWS encryption services for protecting data at rest and in transit.", "level": "Beginner"},
        {"title": "AWS Security Best Practices: Computing", "url": "https://skillbuilder.aws/learn/MSP6X2ZRWV/aws-security-best-practices-computing/NYUMMV4ZCC", "description": "Security best practices for AWS compute services including EC2, Lambda, and containers to protect cloud workloads.", "level": "Intermediate"},
        {"title": "AWS Security: Securing Generative AI on AWS", "url": "https://skillbuilder.aws/learn/ES7A9MKPBZ/aws-security-securing-generative-ai-on-aws/DTAJFXQSUY", "description": "Security considerations and best practices for building and deploying generative AI applications responsibly on AWS.", "level": "Intermediate"},
        {"title": "Cybersecurity for Small Business Owners", "url": "https://skillbuilder.aws/learn/WMRGRX7FM1/cybersecurity-for-small-business-owners/AMZFB5K7RX", "description": "Practical cybersecurity fundamentals for small business owners covering threats, protections, and AWS security tools.", "level": "Beginner"},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "Introduction to the AWS Cloud Adoption Framework (CAF)", "url": "https://skillbuilder.aws/learn/QBZU3QPADC/introduction-to-the-aws-cloud-adoption-framework-caf/7GFPVKU3F8", "description": "Strategic framework for planning and executing cloud adoption projects across business, people, governance, and technology.", "level": "Beginner"},
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
            level=item.get("level", "All Levels"),
        ))
    return results


# ─────────────────────────────────────────────
# Public API returns 405 — using curated list of verified auditable courses
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# SOURCE 6 — edX (curated free-to-audit courses)
# All courses free to audit — certificate requires payment
# ─────────────────────────────────────────────
EDX_CURATED = {
    "Programming & Computer Science": [
        {"title": "Programming for Everybody (Getting Started with Python)", "url": "https://www.edx.org/learn/python/the-university-of-michigan-programming-for-everybody-getting-started-with-python", "description": "University of Michigan's beginner Python course covering variables, loops, functions, and basic programming. Free to audit.", "level": "Beginner"},
        {"title": "Python Data Structures — University of Michigan", "url": "https://www.edx.org/learn/python/the-university-of-michigan-python-data-structures", "description": "The second Python for Everybody course covering strings, lists, dictionaries, and tuples. Free to audit.", "level": "Beginner"},
        {"title": "CS50's Introduction to Computer Science", "url": "https://www.edx.org/learn/computer-science/harvard-university-cs50-s-introduction-to-computer-science", "description": "Harvard's legendary intro CS course covering algorithms, data structures, web development, and more. Free to audit.", "level": "Beginner"},
        {"title": "CS50's Introduction to Programming with Python", "url": "https://www.edx.org/learn/python/harvard-university-cs50-s-introduction-to-programming-with-python", "description": "Harvard's Python-focused CS50 course covering functions, libraries, file I/O, and object-oriented programming. Free to audit.", "level": "Beginner"},
    ],
    "Data Science AI": [
        {"title": "CS50's Introduction to Artificial Intelligence with Python", "url": "https://www.edx.org/learn/artificial-intelligence/harvard-university-cs50-s-introduction-to-artificial-intelligence-with-python", "description": "Harvard's AI course covering search algorithms, machine learning, neural networks, and NLP using Python. Free to audit.", "level": "Intermediate"},
    ],
    "Web Development": [
        {"title": "CS50's Web Programming with Python and JavaScript", "url": "https://www.edx.org/learn/web-development/harvard-university-cs50-s-web-programming-with-python-and-javascript", "description": "Harvard's full-stack web development course covering Django, JavaScript, React, Git, and databases. Free to audit.", "level": "Intermediate"},
        {"title": "IBM: Developing Front End Apps with React", "url": "https://www.edx.org/learn/react-native/ibm-developing-front-end-apps-with-react", "description": "IBM's hands-on React course covering components, state management, hooks, and building interactive web applications. Free to audit.", "level": "Intermediate"},
    ],
    "IT / Cybersecurity": [
        {"title": "CS50's Introduction to Cybersecurity", "url": "https://www.edx.org/learn/cybersecurity/harvard-university-cs50-s-introduction-to-cybersecurity", "description": "Harvard's accessible cybersecurity course for technical and non-technical learners covering threats, defense, and best practices. Free to audit.", "level": "Beginner"},
    ],
    "Project Management / Agile / Career Skills": [
    ],
}

def fetch_edx(category: str) -> list:
    log.info(f"[edX] Fetching: {category}")
    results = []
    for item in EDX_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="edX",
            category=category,
            level=item.get("level", "All Levels"),
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
        {"title": "Statistical Learning with R", "url": "https://www.edx.org/learn/statistics/stanford-university-statistical-learning", "description": "Comprehensive introduction to statistical learning and data mining with R, based on the textbook ISLR. Free to audit.", "platform_override": "edX", "level": "Beginner"},
    ],
    "Web Development": [
        {"title": "Databases: Relational Databases and SQL", "url": "https://www.edx.org/learn/relational-databases/stanford-university-databases-relational-databases-and-sql", "description": "Stanford's self-paced SQL and relational databases course. Free to audit on edX — essential for backend web development.", "platform_override": "edX"},
        {"title": "Generative AI: Technology, Business and Society", "url": "https://online.stanford.edu/courses/xfm100-generative-ai-technology-business-and-society-program-preview", "description": "Stanford's program exploring generative AI's impact on technology, business, and society. Covers practical applications and implications."},
    ],
    "IT / Cybersecurity": [
        {"title": "Introduction to Internet of Things", "url": "https://online.stanford.edu/courses/xee100-introduction-internet-things", "description": "Stanford's beginner-friendly introduction to IoT devices, sensors, connectivity, and embedded systems design. Free.", "level": "Beginner"},
    ],
    "Project Management / Agile / Career Skills": [
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
# ─────────────────────────────────────────────
# SOURCE 9 — GOOGLE (curated free courses)
# Google Skillshop + Google ML Education — all completely free
# ─────────────────────────────────────────────
GOOGLE_CURATED = {
    "Data Science AI": [
        {"title": "Google Introduction to Machine Learning", "url": "https://developers.google.com/machine-learning/intro-to-ml", "description": "Google's beginner introduction to machine learning concepts, supervised learning, and how ML models are trained. Completely free.", "level": "Beginner"},
        {"title": "Machine Learning Problem Framing", "url": "https://developers.google.com/machine-learning/problem-framing", "description": "Google's guide to framing real-world problems as machine learning tasks, including defining goals and evaluating feasibility.", "level": "All Levels"},
        {"title": "Google Machine Learning Crash Course", "url": "https://developers.google.com/machine-learning/crash-course", "description": "Google's fast-paced, practical ML course covering linear regression, neural networks, training, and evaluation with TensorFlow. Completely free.", "level": "Intermediate"},
        {"title": "Managing Machine Learning Projects", "url": "https://developers.google.com/machine-learning/managing-ml-projects", "description": "Google's guide to planning, scoping, and managing machine learning projects from problem definition to deployment.", "level": "All Levels"},
        {"title": "Decision Forests", "url": "https://developers.google.com/machine-learning/decision-forests", "description": "Google's advanced course on decision tree algorithms, random forests, and gradient boosted trees for classification and regression.", "level": "Advanced"},
        {"title": "Recommendation Systems", "url": "https://developers.google.com/machine-learning/recommendation", "description": "Google's advanced guide to building recommendation systems including collaborative filtering, content-based, and deep neural network approaches.", "level": "Advanced"},
        {"title": "Clustering", "url": "https://developers.google.com/machine-learning/clustering", "description": "Google's advanced course on unsupervised clustering algorithms including k-means, hierarchical clustering, and quality metrics.", "level": "Advanced"},
        {"title": "Generative Adversarial Networks (GANs)", "url": "https://developers.google.com/machine-learning/gan", "description": "Google's advanced course on GANs covering generator and discriminator networks, training challenges, and real-world applications.", "level": "Advanced"},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "Get Started Using Google Analytics", "url": "https://skillshop.docebosaas.com/learn/courses/8108/get-started-using-google-analytics", "description": "Google Skillshop's beginner course on setting up and navigating Google Analytics 4, understanding properties, and basic reporting.", "level": "Beginner"},
        {"title": "Manage GA Data and Learn to Read Reports", "url": "https://skillshop.docebosaas.com/learn/courses/7538/Use%20Google%20Analytics%20for%20Your%20Business", "description": "Google Skillshop course on using Google Analytics for business decisions, reading key reports, and understanding audience data.", "level": "Beginner"},
        {"title": "Dive Deeper Into GA4 Data and Reports", "url": "https://skillshop.docebosaas.com/learn/courses/18104/dive-deeper-into-ga4-data-and-reports", "description": "Intermediate Google Analytics 4 course covering advanced reports, explorations, custom dimensions, and deeper data analysis.", "level": "Intermediate"},
        {"title": "Use GA with Other Tools and Data Sources", "url": "https://skillshop.docebosaas.com/learn/courses/18105/go-further-with-advanced-features-in-google-analytics", "description": "Advanced Google Analytics course covering integrations with Google Ads, BigQuery, and other data sources for cross-platform analysis.", "level": "Intermediate"},
        {"title": "Google Analytics Certification", "url": "https://skillshop.docebosaas.com/learn/courses/14810/google-analytics-certification", "description": "Google's official GA4 certification course and exam. Earn a free, shareable Google Analytics certification credential.", "level": "Intermediate"},
        {"title": "AI-Powered Performance Ads Certification", "url": "https://skillshop.docebosaas.com/learn/courses/8510/ai-powered-performance-ads-certification", "description": "Google Skillshop's certification course on using AI-powered tools in Google Ads campaigns for performance marketing.", "level": "Beginner"},
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
            level=item.get("level", "All Levels"),
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


# ─────────────────────────────────────────────
# SOURCE 12 — SAYLOR ACADEMY (curated free courses with free certificates)
# All courses 100% free with free completion certificates
# ─────────────────────────────────────────────
SAYLOR_CURATED = {
    "Programming & Computer Science": [
        {"title": "CS101: Introduction to Computer Science I", "url": "https://learn.saylor.org/course/view.php?id=1146", "description": "Saylor Academy's introduction to programming fundamentals covering algorithms, problem solving, and core CS concepts. Free certificate.", "level": "Beginner"},
        {"title": "CS102: Introduction to Computer Science II", "url": "https://learn.saylor.org/course/view.php?id=64", "description": "Continuation of CS fundamentals covering object-oriented programming, data structures, and algorithm analysis. Free certificate.", "level": "Intermediate"},
        {"title": "CS105: Introduction to Python", "url": "https://learn.saylor.org/course/view.php?id=439", "description": "Saylor Academy's beginner Python programming course covering syntax, data types, control flow, and functions. Free certificate.", "level": "Beginner"},
        {"title": "CS107: C++ Programming", "url": "https://learn.saylor.org/course/view.php?id=65", "description": "Introduction to C++ programming covering variables, loops, functions, pointers, and object-oriented concepts. Free certificate.", "level": "Beginner"},
        {"title": "CS120: Bitcoin for Developers I", "url": "https://learn.saylor.org/course/view.php?id=500", "description": "Introduction to Bitcoin and blockchain development covering cryptographic foundations, transactions, and protocol fundamentals. Free certificate.", "level": "Beginner"},
        {"title": "CS201: Elementary Data Structures", "url": "https://learn.saylor.org/course/view.php?id=1307", "description": "Foundational data structures including arrays, linked lists, stacks, queues, trees, and basic algorithm complexity. Free certificate.", "level": "Beginner"},
        {"title": "CS202: Discrete Structures", "url": "https://learn.saylor.org/course/view.php?id=67", "description": "Mathematical foundations of computer science covering logic, sets, combinatorics, graphs, and proofs. Free certificate.", "level": "Beginner"},
        {"title": "CS301: Computer Architecture", "url": "https://learn.saylor.org/course/view.php?id=71", "description": "Deep dive into how computers work covering CPU design, memory hierarchy, instruction sets, and performance optimization. Free certificate.", "level": "Intermediate"},
        {"title": "PRDV401: Introduction to JavaScript I", "url": "https://learn.saylor.org/course/view.php?id=502", "description": "Beginner JavaScript course covering variables, functions, DOM manipulation, and basic web interactivity. Free certificate.", "level": "Beginner"},
        {"title": "PRDV402: Introduction to JavaScript II", "url": "https://learn.saylor.org/course/view.php?id=750", "description": "Continuation of JavaScript covering arrays, objects, error handling, and more advanced programming patterns. Free certificate.", "level": "Beginner"},
        {"title": "PRDV420: Introduction to R Programming", "url": "https://learn.saylor.org/course/view.php?id=671", "description": "Introduction to R programming for data analysis covering syntax, data frames, visualization, and statistical computing. Free certificate.", "level": "Intermediate"},
        {"title": "PHIL102: Introduction to Critical Thinking and Logic", "url": "https://learn.saylor.org/course/view.php?id=1255", "description": "Foundational course on logical reasoning, argument analysis, fallacies, and critical thinking skills essential for CS and beyond. Free certificate.", "level": "Beginner"},
    ],
    "Data Science AI": [
        {"title": "CS205: Building with Artificial Intelligence", "url": "https://learn.saylor.org/course/view.php?id=777", "description": "Intermediate course on building AI applications covering machine learning workflows, model selection, and practical AI implementation. Free certificate.", "level": "Intermediate"},
        {"title": "CS207: Fundamentals of Machine Learning", "url": "https://learn.saylor.org/course/view.php?id=1267", "description": "Beginner introduction to machine learning covering supervised and unsupervised learning, model evaluation, and core algorithms. Free certificate.", "level": "Beginner"},
        {"title": "CS250: Python for Data Science", "url": "https://learn.saylor.org/course/view.php?id=504", "description": "Intermediate course on using Python for data science covering NumPy, Pandas, data cleaning, and visualization. Free certificate.", "level": "Intermediate"},
        {"title": "BUS204: Business Statistics", "url": "https://learn.saylor.org/course/view.php?id=1247", "description": "Introduction to business statistics covering descriptive statistics, probability, hypothesis testing, and regression analysis. Free certificate.", "level": "Beginner"},
        {"title": "BUS250: Introduction to Business Intelligence and Analytics", "url": "https://learn.saylor.org/course/view.php?id=869", "description": "Beginner course covering BI tools, data warehousing, dashboards, and using analytics for business decision making. Free certificate.", "level": "Beginner"},
        {"title": "BUS607: Data-Driven Decision-Making", "url": "https://learn.saylor.org/course/view.php?id=737", "description": "Advanced course on applying data analytics to strategic business decisions, including frameworks and case studies. Free certificate.", "level": "Advanced"},
        {"title": "BUS610: Advanced Business Intelligence and Analytics", "url": "https://learn.saylor.org/course/view.php?id=741", "description": "Advanced BI course covering data mining, predictive analytics, and enterprise-level analytics strategy. Free certificate.", "level": "Advanced"},
        {"title": "BUS611: Data Management", "url": "https://learn.saylor.org/course/view.php?id=725", "description": "Advanced course on data governance, database management, data quality, and enterprise data strategy. Free certificate.", "level": "Advanced"},
        {"title": "BUS612: Data-Driven Communications", "url": "https://learn.saylor.org/course/view.php?id=759", "description": "Advanced course on communicating data insights effectively through storytelling, visualization, and presentation strategies. Free certificate.", "level": "Advanced"},
        {"title": "PRDV200: Communicating with Data", "url": "https://learn.saylor.org/course/view.php?id=868", "description": "Beginner course on presenting data clearly and effectively using charts, visuals, and data storytelling techniques. Free certificate.", "level": "Beginner"},
        {"title": "PRDV430: AI for Business Applications", "url": "https://learn.saylor.org/course/view.php?id=1254", "description": "Intermediate course on applying AI tools to business workflows, automation, and decision support. Free certificate.", "level": "Intermediate"},
        {"title": "PRDV433: Enhancing Spreadsheets with Generative AI", "url": "https://learn.saylor.org/course/view.php?id=1312", "description": "Beginner course on using generative AI tools to enhance spreadsheet productivity, automate tasks, and analyze data. Free certificate.", "level": "Beginner"},
    ],
    "IT / Cybersecurity": [
        {"title": "CS260: Introduction to Cryptography and Network Security", "url": "https://learn.saylor.org/course/view.php?id=805", "description": "Intermediate course covering cryptographic algorithms, network security protocols, authentication, and practical security applications. Free certificate.", "level": "Intermediate"},
        {"title": "CS406: Information Security", "url": "https://learn.saylor.org/course/view.php?id=453", "description": "Intermediate information security course covering risk management, access control, security policies, and defensive strategies. Free certificate.", "level": "Intermediate"},
        {"title": "BUS206: Management Information Systems", "url": "https://learn.saylor.org/course/view.php?id=41", "description": "Introduction to MIS covering how organizations use information systems, IT infrastructure, and technology strategy. Free certificate.", "level": "Beginner"},
        {"title": "BUS303: Strategic Information Technology", "url": "https://learn.saylor.org/course/view.php?id=1270", "description": "Intermediate course on aligning IT strategy with business goals, enterprise architecture, and digital transformation planning. Free certificate.", "level": "Intermediate"},
        {"title": "BUS642: Applications of Management Information Systems", "url": "https://learn.saylor.org/course/view.php?id=1283", "description": "Advanced course on applying MIS in real organizations covering ERP, CRM, business intelligence, and emerging tech. Free certificate.", "level": "Advanced"},
        {"title": "PRDV201: Information Literacy", "url": "https://learn.saylor.org/course/view.php?id=893", "description": "Beginner course on finding, evaluating, and using digital information responsibly — essential skills for any tech professional. Free certificate.", "level": "Beginner"},
    ],
    "Project Management / Agile / Career Skills": [
        {"title": "BUS402: Introduction to Project Management", "url": "https://learn.saylor.org/course/view.php?id=1147", "description": "Intermediate introduction to project management covering scope, schedule, cost, risk, and stakeholder management fundamentals. Free certificate.", "level": "Intermediate"},
        {"title": "BUS604: Innovation and Sustainability", "url": "https://learn.saylor.org/course/view.php?id=688", "description": "Advanced course on driving innovation within organizations while maintaining sustainable business practices. Free certificate.", "level": "Advanced"},
        {"title": "BUS605: Strategic Project Management", "url": "https://learn.saylor.org/course/view.php?id=736", "description": "Advanced project management course covering portfolio management, program governance, and strategic alignment. Free certificate.", "level": "Advanced"},
        {"title": "BUS632: Digital Marketing and Advertising", "url": "https://learn.saylor.org/course/view.php?id=1266", "description": "Advanced course on digital marketing strategies, advertising platforms, SEO, and campaign management. Free certificate.", "level": "Advanced"},
        {"title": "BUS653: Innovation and Entrepreneurship Launch", "url": "https://learn.saylor.org/course/view.php?id=1301", "description": "Advanced course on launching new ventures covering ideation, validation, business modeling, and entrepreneurial strategy. Free certificate.", "level": "Advanced"},
        {"title": "BUS654: Entrepreneurship Seminar", "url": "https://learn.saylor.org/course/view.php?id=1305", "description": "Advanced entrepreneurship seminar covering funding, scaling, legal considerations, and building sustainable businesses. Free certificate.", "level": "Advanced"},
        {"title": "PRDV224: Leadership and Teams", "url": "https://learn.saylor.org/course/view.php?id=1286", "description": "Beginner course on leadership fundamentals, team dynamics, communication, and conflict resolution for professionals. Free certificate.", "level": "Beginner"},
        {"title": "PRDV227: Introduction to Business Planning and Strategy", "url": "https://learn.saylor.org/course/view.php?id=1298", "description": "Beginner course on creating business plans, defining strategy, and understanding market analysis and competitive positioning. Free certificate.", "level": "Beginner"},
        {"title": "PRDV003: Word Processing", "url": "https://learn.saylor.org/course/view.php?id=890", "description": "Beginner course on professional word processing skills including document formatting, templates, and advanced features. Free certificate.", "level": "Beginner"},
        {"title": "PRDV004: Spreadsheets", "url": "https://learn.saylor.org/course/view.php?id=1263", "description": "Beginner spreadsheet course covering formulas, functions, charts, and organizing data for business use. Free certificate.", "level": "Beginner"},
        {"title": "PRDV006: Spreadsheets II - Formatting and Functions", "url": "https://learn.saylor.org/course/view.php?id=876", "description": "Beginner course expanding spreadsheet skills with advanced formatting, logical functions, and data validation. Free certificate.", "level": "Beginner"},
        {"title": "PRDV007: Spreadsheets III - Presenting Data", "url": "https://learn.saylor.org/course/view.php?id=877", "description": "Beginner course on creating professional charts, pivot tables, and data presentations in spreadsheets. Free certificate.", "level": "Beginner"},
        {"title": "PRDV002: Professional Writing", "url": "https://learn.saylor.org/course/view.php?id=729", "description": "Beginner course on professional business writing including emails, reports, proposals, and clear workplace communication. Free certificate.", "level": "Beginner"},
        {"title": "PRDV102: Resume Writing", "url": "https://learn.saylor.org/course/view.php?id=864", "description": "Beginner course on crafting effective resumes, tailoring applications, and presenting skills to employers. Free certificate.", "level": "Beginner"},
        {"title": "PRDV103: Interviewing Skills", "url": "https://learn.saylor.org/course/view.php?id=873", "description": "Beginner course on interview preparation, answering common questions, and presenting yourself confidently to employers. Free certificate.", "level": "Beginner"},
    ],
}

def fetch_saylor(category: str) -> list:
    log.info(f"[Saylor Academy] Fetching: {category}")
    results = []
    for item in SAYLOR_CURATED.get(category, []):
        clean = clean_description(item["title"], item["description"], category)
        results.append(build_resource(
            title=item["title"],
            url=item["url"],
            description=clean,
            platform="Saylor Academy",
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
    fetch_edx,
    fetch_stanford,
    fetch_ibm,
    fetch_google,
    fetch_helsinki,
    fetch_khan,
    fetch_saylor,
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
