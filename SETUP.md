# Tech Education Resource Scraper — Setup Guide

## What This Does
Pulls free tech courses from 9 platforms using permitted APIs and public pages,
uses Claude API to clean descriptions, and outputs a `resources.json` file
ready to load into your Bootstrap Studio website.

---

## Step 1 — Get Your API Keys

### YouTube Data API v3 (Free)
1. Go to https://console.cloud.google.com/
2. Create a new project (e.g., "TechEduScraper")
3. Click **APIs & Services → Enable APIs**
4. Search for "YouTube Data API v3" → Enable it
5. Go to **Credentials → Create Credentials → API Key**
6. Copy the key — you'll use it below

**Free quota:** 10,000 units/day (plenty for monthly scraping)

---

### Anthropic (Claude) API Key
1. Go to https://console.anthropic.com/
2. Sign in and go to **API Keys**
3. Click **Create Key**, copy it

**Cost note:** Each description cleaning call uses ~150 tokens.
Estimate: 9 platforms × 5 categories × 10 results × ~150 tokens ≈ ~67,500 tokens/run
At Claude Sonnet pricing (~$3/million tokens), that's roughly **$0.20 per monthly run**.

---

## Step 2 — Install Dependencies

```bash
# Make sure Python 3.9+ is installed
python --version

# Install required packages
pip install -r requirements.txt
```

---

## Step 3 — Set Your API Keys

### Option A: Environment Variables (Recommended)
```bash
# Mac/Linux — add to your ~/.zshrc or ~/.bashrc
export YOUTUBE_API_KEY="your_youtube_key_here"
export ANTHROPIC_API_KEY="your_anthropic_key_here"
source ~/.zshrc  # reload

# Windows (Command Prompt)
setx YOUTUBE_API_KEY "your_youtube_key_here"
setx ANTHROPIC_API_KEY "your_anthropic_key_here"
```

### Option B: Edit the Script Directly
Open `scraper.py` and find the CONFIG section at the top:
```python
CONFIG = {
    "youtube_api_key":   "PASTE_YOUR_YOUTUBE_KEY_HERE",
    "anthropic_api_key": "PASTE_YOUR_ANTHROPIC_KEY_HERE",
    ...
}
```

---

## Step 4 — Run the Scraper

### One-time manual run:
```bash
python scraper.py
```

### Monthly auto-refresh (runs immediately, then every 1st of the month at 6am):
```bash
python scraper.py --schedule
```

### Output:
- `resources.json` — your course data, ready for Bootstrap Studio
- `scraper.log` — run history and any errors

---

## Step 5 — Use resources.json in Bootstrap Studio

In your Bootstrap Studio HTML, load and display the data like this:

```html
<script>
  fetch('resources.json')
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('courses-container');
      data.resources.forEach(course => {
        container.innerHTML += `
          <div class="col-md-4 mb-4">
            <div class="card h-100">
              <div class="card-body">
                <span class="badge bg-primary mb-2">${course.category}</span>
                <span class="badge bg-secondary mb-2">${course.platform}</span>
                <h5 class="card-title">${course.title}</h5>
                <p class="card-text">${course.description}</p>
                <a href="${course.url}" target="_blank" class="btn btn-outline-primary btn-sm">
                  View Course →
                </a>
              </div>
            </div>
          </div>`;
      });
    });
</script>
```

Add a filter by category using Bootstrap's nav-pills for a clean UI.

---

## Platforms Covered & Permissions

| Platform           | Method              | Terms Status     |
|--------------------|---------------------|------------------|
| YouTube            | Official API v3     | ✅ Fully permitted |
| Microsoft Learn    | Official REST API   | ✅ Fully permitted |
| Coursera           | Official catalog API| ✅ Fully permitted |
| MIT OpenCourseWare | Public pages (OCW open license) | ✅ Permitted     |
| freeCodeCamp       | Public pages        | ✅ Open content   |
| AWS Skill Builder  | Public catalog pages| ✅ Public listings |
| Stanford Online    | Public free courses page | ✅ Public listings |
| IBM SkillsBuild    | Public pages        | ✅ Public listings |
| Google             | Public pages (Grow/Skillshop) | ✅ Public listings |

---

## Troubleshooting

**"YouTube API key invalid"** → Double-check the key in Google Cloud Console;
make sure the YouTube Data API v3 is enabled for your project.

**"Claude API error"** → Verify your Anthropic key and check your account has credits.

**"0 results from [platform]"** → The site's HTML structure may have changed.
Check `scraper.log` for details. You can adjust the CSS selectors in the relevant
`fetch_*` function.

**Running on Windows Task Scheduler instead of --schedule:**
Create a .bat file:
```
@echo off
cd C:\path\to\your\script
python scraper.py
```
Schedule it monthly in Task Scheduler.
