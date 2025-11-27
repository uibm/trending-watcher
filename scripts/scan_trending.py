import requests
from bs4 import BeautifulSoup
import yaml
import os
import time

GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
CHECKED_FILE = "_data/trending_checked.yml"

def get_trending_repos(retries=3):
    """Fetch trending repositories from GitHub with retry logic."""
    for attempt in range(retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TrendingWatcher/1.0)'
            }
            res = requests.get("https://github.com/trending", headers=headers, timeout=10)
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")
            repos = soup.find_all("h2", class_="h3 lh-condensed")

            if not repos:
                print("Warning: No repositories found in trending page")
                return []

            return [repo.text.strip().replace("\n", "").replace(" ", "") for repo in repos]

        except requests.RequestException as e:
            print(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                # Exponential backoff: 2s, 4s, 8s
                wait_time = 2 ** (attempt + 1)
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Failed to fetch trending repos after {retries} attempts")

def load_checked():
    if not os.path.exists(CHECKED_FILE):
        return []
    with open(CHECKED_FILE, "r") as f:
        return yaml.safe_load(f) or []

def save_checked(checked):
    with open(CHECKED_FILE, "w") as f:
        yaml.dump(checked, f)

def create_issue(repo, retries=3):
    """Create a GitHub issue for a trending repository with retry logic."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    body = f"""## 📈 Trending Repository

**Repository:** [{repo}](https://github.com/{repo})

This repository is currently trending on GitHub!

---
*This issue was automatically created by the Trending Watcher project.*
*Powered by GitHub Actions and DeepWiki.*
"""
    data = {
        "title": f"Check trending repo: {repo}",
        "body": body,
        "labels": ["trending"]
    }

    for attempt in range(retries):
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 201:
                print(f"✓ Created issue for {repo}")
                return True
            else:
                print(f"Failed to create issue for {repo}: {response.status_code}")

        except requests.RequestException as e:
            print(f"Attempt {attempt + 1}/{retries} failed for {repo}: {e}")

        if attempt < retries - 1:
            time.sleep(2)

    print(f"✗ Could not create issue for {repo} after {retries} attempts")
    return False

def main():
    trending = get_trending_repos()
    checked = load_checked()
    new = [r for r in trending if r not in checked]

    for repo in new:
        create_issue(repo)
        checked.append(repo)

    save_checked(checked)

if __name__ == "__main__":
    main()
