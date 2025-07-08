import requests
from bs4 import BeautifulSoup
import yaml
import os

GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
CHECKED_FILE = "_data/trending_checked.yml"

def get_trending_repos():
    res = requests.get("https://github.com/trending")
    soup = BeautifulSoup(res.text, "html.parser")
    repos = soup.find_all("h2", class_="h3 lh-condensed")
    return [repo.text.strip().replace("\n", "").replace(" ", "") for repo in repos]

def load_checked():
    if not os.path.exists(CHECKED_FILE):
        return []
    with open(CHECKED_FILE, "r") as f:
        return yaml.safe_load(f) or []

def save_checked(checked):
    with open(CHECKED_FILE, "w") as f:
        yaml.dump(checked, f)

def create_issue(repo):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "title": f"Check trending repo: {repo}",
        "body": f"GitHub Trending repo: https://github.com/{repo}",
        "labels": ["trending"]
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 201:
        print(f"Failed to create issue for {repo}: {response.status_code} {response.text}")

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
