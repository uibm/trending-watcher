#!/usr/bin/env python3
"""
Cleanup old repositories from tracking list.
This script removes repositories that haven't been trending recently
to keep the data file manageable.
"""

import yaml
import os
from datetime import datetime, timedelta

CHECKED_FILE = "_data/trending_checked.yml"
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Configuration
MAX_REPOS = 1000  # Maximum number of repos to keep
CLEANUP_AFTER_DAYS = 90  # Archive repos older than this


def load_checked():
    """Load the list of checked repositories."""
    if not os.path.exists(CHECKED_FILE):
        return []

    with open(CHECKED_FILE, "r") as f:
        data = yaml.safe_load(f) or []

    # Handle both list and dict formats
    if isinstance(data, list):
        return data
    return []


def save_checked(repos):
    """Save the cleaned list of repositories."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(CHECKED_FILE), exist_ok=True)

    with open(CHECKED_FILE, "w") as f:
        yaml.dump(repos, f, default_flow_style=False)


def cleanup_by_count(repos, max_count=MAX_REPOS):
    """
    Keep only the most recent max_count repositories.
    Assumes the list is in chronological order (oldest first).
    """
    if len(repos) <= max_count:
        return repos, 0

    # Keep the most recent repos
    kept = repos[-max_count:]
    removed = len(repos) - len(kept)

    print(f"Cleaned up {removed} old repositories (keeping last {max_count})")
    return kept, removed


def remove_duplicates(repos):
    """Remove duplicate entries while preserving order."""
    seen = set()
    unique = []

    for repo in repos:
        if repo not in seen:
            seen.add(repo)
            unique.append(repo)

    duplicates = len(repos) - len(unique)
    if duplicates > 0:
        print(f"Removed {duplicates} duplicate entries")

    return unique, duplicates


def main():
    """Main cleanup function."""
    print("=" * 60)
    print("Trending Watcher - Data Cleanup")
    print("=" * 60)

    # Load current data
    repos = load_checked()
    original_count = len(repos)

    print(f"\nOriginal repository count: {original_count}")

    if original_count == 0:
        print("No repositories to clean up.")
        return

    # Remove duplicates
    repos, dup_count = remove_duplicates(repos)

    # Cleanup by count (keep most recent)
    repos, removed_count = cleanup_by_count(repos, MAX_REPOS)

    # Save cleaned data
    save_checked(repos)

    final_count = len(repos)

    print(f"\nCleanup Summary:")
    print(f"  - Original count: {original_count}")
    print(f"  - Duplicates removed: {dup_count}")
    print(f"  - Old repos removed: {removed_count}")
    print(f"  - Final count: {final_count}")
    print(f"\nCleanup complete! ✓")


if __name__ == "__main__":
    main()
