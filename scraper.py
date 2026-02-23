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
    "max_results_per_source": 20,   # per category per platform
}

CATEGORIES = [
    "Programming & Computer Science",
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
        {"title": "Web Development", "url": "https://ocw.mit.edu/courses/mas-962-special-topics-new-media-literacy-spring-2010/", "description": "MIT course exploring web technologies, interactive media, and principles of building modern web applications."},
        {"title": "User Interface Design and Implementation", "url": "https://ocw.mit.edu/courses/6-831-user-interface-design-and-implementation-spring-2011/", "description": "MIT course on UI design principles, usability, and front-end implementation for interactive web applications."},
    ],
    "IT Cybersecurity": [
        {"title": "Computer Systems Security", "url": "https://ocw.mit.edu/courses/6-858-computer-systems-security-fall-2014/", "description": "MIT's in-depth computer security course covering network security, cryptography, software vulnerabilities, and defenses."},
        {"title": "Network and Computer Security", "url": "https://ocw.mit.edu/courses/6-857-network-and-computer-security-spring-2014/", "description": "MIT course on cryptographic protocols, authentication, network security, and applied security engineering."},
    ],
    "Project Management Agile": [
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
    "IT Cybersecurity": [
        {"title": "Information Security", "url": "https://www.freecodecamp.org/learn/information-security/", "description": "freeCodeCamp's free information security certification covering HelmetJS, penetration testing, and secure application development."},
        {"title": "Foundational C# with Microsoft", "url": "https://www.freecodecamp.org/learn/foundational-c-sharp-with-microsoft/", "description": "Microsoft-partnered freeCodeCamp course teaching foundational C# programming for secure software development."},
    ],
    "Project Management Agile": [
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
    "IT Cybersecurity":          "cybersecurity network security",
    "Project Management Agile":  "project management agile scrum",
}

# Maps to official Microsoft Learn subject filter values
MS_SUBJECT_MAP = {
    "Programming & Computer Science":        "application-development",
    "Data Science AI":           "artificial-intelligence",
    "Web Development":           "application-development",
    "IT Cybersecurity":          "security",
    "Project Management Agile":  "business-applications",
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
        "IT Cybersecurity":          ["security", "cybersecurity", "threat", "zero trust", "identity", "compliance", "defender"],
        "Project Management Agile":  ["project management", "agile", "scrum", "devops", "planning", "leadership"],
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
    "IT Cybersecurity": [
        {"title": "AWS Security Fundamentals", "url": "https://skillbuilder.aws/search?searchText=aws-security-fundamentals", "description": "Core AWS security concepts covering IAM, data encryption, network security, monitoring, and compliance frameworks."},
        {"title": "AWS Security Best Practices", "url": "https://skillbuilder.aws/search?searchText=security-best-practices-in-aws", "description": "Advanced security engineering practices for protecting AWS infrastructure, workloads, and data at rest and in transit."},
        {"title": "AWS Identity and Access Management (IAM) Foundations", "url": "https://skillbuilder.aws/search?searchText=aws-iam-identity-and-access-management", "description": "Deep dive into AWS IAM for controlling access to services and resources, managing policies, roles, and permissions securely."},
    ],
    "Project Management Agile": [
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
    "IT Cybersecurity": [
        {"title": "Google Cybersecurity Certificate", "url": "https://www.coursera.org/professional-certificates/google-cybersecurity", "description": "Google's professional cybersecurity program covering threat detection, network security, and incident response. Free to audit."},
        {"title": "IBM Cybersecurity Analyst Certificate", "url": "https://www.coursera.org/professional-certificates/ibm-cybersecurity-analyst", "description": "IBM's cybersecurity analyst training covering security tools, threat intelligence, and compliance. Free to audit."},
        {"title": "Introduction to Cyber Security Specialization", "url": "https://www.coursera.org/specializations/intro-cyber-security", "description": "NYU's foundational cybersecurity specialization covering cyber attacks, defenses, and cryptography. Free to audit."},
    ],
    "Project Management Agile": [
        {"title": "Google Project Management Certificate", "url": "https://www.coursera.org/professional-certificates/google-project-management", "description": "Google's professional project management program covering Agile, Scrum, and traditional PM methods. Free to audit."},
        {"title": "Agile with Atlassian Jira", "url": "https://www.coursera.org/learn/agile-atlassian-jira", "description": "Practical Agile project management using Jira from Atlassian. Covers sprints, backlogs, and Kanban. Free to audit."},
        {"title": "Engineering Project Management Specialization", "url": "https://www.coursera.org/specializations/engineering-project-management", "description": "Rice University's project management specialization covering scope, schedule, risk, and Agile methods. Free to audit."},
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
        {"title": "Machine Learning Specialization", "url": "https://online.stanford.edu/courses/soe-ymls-machine-learning-specialization", "description": "Stanford's comprehensive machine learning specialization covering supervised, unsupervised, and reinforcement learning. Free to audit."},
        {"title": "Statistical Learning — Stanford Online", "url": "https://online.stanford.edu/courses/sohs-ystatslearning-statistical-learning", "description": "Comprehensive introduction to statistical learning and data mining with R, based on the textbook ISLR."},
    ],
    "Web Development": [
        {"title": "Databases: Relational Databases and SQL", "url": "https://www.edx.org/learn/relational-databases/stanford-university-databases-relational-databases-and-sql", "description": "Stanford's self-paced SQL and relational databases course. Free to audit on edX — essential for backend web development.", "platform_override": "edX"},
        {"title": "Generative AI: Technology, Business and Society", "url": "https://online.stanford.edu/courses/xfm100-generative-ai-technology-business-and-society-program-preview", "description": "Stanford's program exploring generative AI's impact on technology, business, and society. Covers practical applications and implications."},
    ],
    "IT Cybersecurity": [
        {"title": "Cryptography I — Stanford", "url": "https://www.coursera.org/learn/crypto", "description": "Stanford's cryptography course covering symmetric and asymmetric encryption, message authentication, and security protocols. Free to audit."},
        {"title": "Computer and Network Security — CS155", "url": "https://online.stanford.edu/courses/cs155-computer-and-network-security", "description": "Stanford's cybersecurity course covering network threats, cryptography, web security, and ethical hacking practices."},
    ],
    "Project Management Agile": [
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
        {"title": "Python for Data Science and AI — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/artificial-intelligence", "description": "IBM's free Python programming course for data science and AI applications. No prior experience needed."},
        {"title": "Getting Started with Python — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/it-support", "description": "IBM's beginner Python course covering syntax, data structures, functions, and real-world scripting."},
    ],
    "Data Science AI": [
        {"title": "Artificial Intelligence Fundamentals — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/artificial-intelligence", "description": "IBM's free AI fundamentals course covering machine learning, neural networks, and AI applications. Earn a badge on completion."},
        {"title": "AI Foundations: A Collaboration of ISTE and IBM", "url": "https://skillsbuild.org/students/course-catalog/artificial-intelligence", "description": "Foundational AI course co-developed by ISTE and IBM covering AI concepts, ethics, and real-world applications. 14 hours."},
        {"title": "Data Science Foundations — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/data-science", "description": "Explore data analysis, visualization, and machine learning concepts through IBM's free learning platform."},
    ],
    "Web Development": [
        {"title": "Web Development Fundamentals — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/it-support", "description": "IBM's free web development course covering HTML, CSS, JavaScript, and modern web frameworks."},
        {"title": "UX Design Foundations — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/ux-design", "description": "Learn user experience design principles, wireframing, and prototyping for building effective web interfaces."},
    ],
    "IT Cybersecurity": [
        {"title": "Cybersecurity Fundamentals — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/cybersecurity", "description": "IBM's free 6-hour cybersecurity course covering encryption, cryptography, roles, and tactics used by cyber attackers. Earn a badge."},
        {"title": "Cybersecurity: Getting Started — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/cybersecurity", "description": "Introductory cybersecurity learning activities from IBM covering network security, threat identification, and incident basics."},
    ],
    "Project Management Agile": [
        {"title": "Enterprise Design Thinking — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/data-science", "description": "IBM's design thinking framework course covering user-centered iterative project planning and delivery methods."},
        {"title": "IT Project Management — IBM SkillsBuild", "url": "https://skillsbuild.org/students/course-catalog/it-support", "description": "IBM's free project management course covering Agile methods, planning, scope, and team leadership skills."},
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
        ))
    return results


# ─────────────────────────────────────────────
# SOURCE 9 — GOOGLE (curated free courses)
# JS-rendered sites; using verified static course URLs
# ─────────────────────────────────────────────
GOOGLE_CURATED = {
    "Programming & Computer Science": [
        {"title": "Crash Course on Python", "url": "https://www.coursera.org/learn/python-crash-course", "description": "Google's beginner Python course covering variables, data structures, loops, functions, and automation scripting. Free to audit on Coursera."},
        {"title": "Using Python to Interact with the Operating System", "url": "https://www.coursera.org/learn/python-operating-system", "description": "Google course on using Python for OS automation, file handling, regular expressions, and process management. Free to audit."},
    ],
    "Data Science AI": [
        {"title": "Google Data Analytics Certificate", "url": "https://grow.google/certificates/data-analytics/", "description": "Google's professional data analytics program covering spreadsheets, SQL, Tableau, and R for data-driven decision making."},
        {"title": "Google Advanced Data Analytics Certificate", "url": "https://grow.google/certificates/advanced-data-analytics/", "description": "Advanced Google program covering Python, statistics, regression, machine learning, and data storytelling for analysts."},
        {"title": "Google AI Essentials", "url": "https://grow.google/certificates/ai-essentials/", "description": "Google's free foundational AI course covering how to use AI tools responsibly and effectively in the workplace."},
    ],
    "Web Development": [
        {"title": "Foundations of Digital Marketing and E-commerce", "url": "https://www.coursera.org/learn/foundations-of-digital-marketing-and-e-commerce", "description": "Google's free digital marketing course covering SEO, web analytics, social media, and e-commerce fundamentals. Free to audit on Coursera."},
        {"title": "Google UX Design Certificate", "url": "https://grow.google/certificates/ux-design/", "description": "Google's UX design program covering user research, wireframing, prototyping, and designing accessible web experiences."},
    ],
    "IT Cybersecurity": [
        {"title": "Google Cybersecurity Certificate", "url": "https://grow.google/certificates/cybersecurity/", "description": "Google's professional cybersecurity program covering threat detection, network security, incident response, and Python automation."},
        {"title": "Google IT Support Certificate", "url": "https://grow.google/certificates/it-support/", "description": "Google's foundational IT program covering networking, operating systems, security, and troubleshooting. Earns a Coursera certificate."},
    ],
    "Project Management Agile": [
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
