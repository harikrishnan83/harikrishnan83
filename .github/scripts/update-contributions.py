#!/usr/bin/env python3
"""
Script to fetch repositories contributed to and update README.md

GitHub Token Requirements:
--------------------------
This script uses the GITHUB_TOKEN environment variable for authentication.

When running in GitHub Actions:
  - The token is automatically provided via secrets.GITHUB_TOKEN
  - No manual setup required
  - Has read access to public repositories
  - Higher API rate limits (5,000 requests/hour vs 60 unauthenticated)

Required token permissions:
  - public_repo (read access to public repositories)
  - read:user (read user profile data)

When running locally:
  - Set GITHUB_TOKEN environment variable with a Personal Access Token (PAT)
  - Create PAT at: https://github.com/settings/tokens
  - Select scopes: public_repo, read:user
  - Or run without token (lower rate limits apply)
"""

import json
import urllib.request
import urllib.error
import re
import os

# Configuration
GITHUB_USERNAME = "harikrishnan83"
README_PATH = "README.md"
NUM_REPOS = 5

# GitHub token for authentication (automatically provided in GitHub Actions)
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

def make_github_request(url):
    """Make authenticated GitHub API request"""
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'GitHub-Profile-Updater'
    }
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason} for URL: {url}")
        if e.code == 403:
            print("Rate limit may have been exceeded. Check API rate limits.")
        return None
    except Exception as e:
        print(f"Error making request to {url}: {e}")
        return None

def fetch_contributed_repos():
    """Fetch all public repositories the user has contributed to"""
    print(f"Fetching contribution data for {GITHUB_USERNAME}...")

    # Get user's public events (last 90 days of activity)
    contributed_repos = {}
    page = 1
    max_pages = 10  # Limit to prevent excessive API calls

    while page <= max_pages:
        events_url = f"https://api.github.com/users/{GITHUB_USERNAME}/events/public?page={page}&per_page=100"
        events = make_github_request(events_url)

        if not events or len(events) == 0:
            break

        for event in events:
            # Look for push events, pull request events, and issue events
            if event.get('type') in ['PushEvent', 'PullRequestEvent', 'IssuesEvent', 'IssueCommentEvent', 'PullRequestReviewEvent']:
                repo = event.get('repo', {})
                repo_name = repo.get('name', '')

                if repo_name and repo_name not in contributed_repos:
                    contributed_repos[repo_name] = True

        page += 1

    print(f"Found {len(contributed_repos)} repositories from recent events")

    # Also get repositories where user has made commits (search commits)
    search_url = f"https://api.github.com/search/commits?q=author:{GITHUB_USERNAME}+is:public&sort=committer-date&order=desc&per_page=100"
    headers = {
        'Accept': 'application/vnd.github.cloak-preview+json',
        'User-Agent': 'GitHub-Profile-Updater'
    }
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'

    try:
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            search_results = json.loads(response.read().decode('utf-8'))
            commits = search_results.get('items', [])

            for commit in commits:
                repo_url = commit.get('repository', {}).get('full_name', '')
                if repo_url and repo_url not in contributed_repos:
                    contributed_repos[repo_url] = True

            print(f"Found {len(commits)} commits, total unique repos: {len(contributed_repos)}")
    except Exception as e:
        print(f"Could not search commits (this is optional): {e}")

    return list(contributed_repos.keys())

def fetch_repo_details(repo_names):
    """Fetch detailed information for each repository"""
    repos_with_details = []

    for repo_name in repo_names:
        print(f"Fetching details for {repo_name}...")
        repo_url = f"https://api.github.com/repos/{repo_name}"
        repo_data = make_github_request(repo_url)

        if repo_data and not repo_data.get('private', False):
            repos_with_details.append({
                'name': repo_data.get('name', ''),
                'full_name': repo_data.get('full_name', ''),
                'description': repo_data.get('description', 'No description available'),
                'html_url': repo_data.get('html_url', ''),
                'stars': repo_data.get('stargazers_count', 0),
                'forks': repo_data.get('forks_count', 0),
                'language': repo_data.get('language', 'Unknown'),
                'is_fork': repo_data.get('fork', False)
            })

    return repos_with_details

def format_contributions(repos):
    """Format repositories as markdown"""
    if not repos:
        return "## Open Source Contributions\n\n_Unable to fetch contributions at this time._\n"

    # Sort by stars (descending)
    sorted_repos = sorted(repos, key=lambda x: x['stars'], reverse=True)

    # Take top N
    top_repos = sorted_repos[:NUM_REPOS]

    markdown = "## Open Source Contributions\n\n"
    markdown += f"Top {len(top_repos)} repositories I've contributed to (by GitHub stars):\n\n"

    for repo in top_repos:
        # Format: ⭐ **[repo-name](url)** - Description (★ stars | language)
        stars_formatted = f"{repo['stars']:,}"
        language = repo['language'] if repo['language'] else 'Various'

        markdown += f"⭐ **[{repo['full_name']}]({repo['html_url']})** "
        markdown += f"(★ {stars_formatted} | {language})\n"

        # Add description with indentation
        description = repo['description'] if repo['description'] else 'No description available'
        # Truncate long descriptions
        if len(description) > 120:
            description = description[:120].rsplit(' ', 1)[0] + '...'
        markdown += f"   {description}\n\n"

    return markdown

def update_readme(contributions_content):
    """Update README.md with contributions content"""
    try:
        with open(README_PATH, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        # Define markers for contributions section
        start_marker = "<!-- CONTRIBUTIONS-START -->"
        end_marker = "<!-- CONTRIBUTIONS-END -->"

        # Check if markers exist
        if start_marker not in readme_content:
            # Add contributions section before the website link at the end
            # Find the position before the last "---" or before "Learn more" section
            pattern = r'(\n---\n\n\*\*Learn more by visiting my website)'
            if re.search(pattern, readme_content):
                readme_content = re.sub(
                    pattern,
                    f"\n{start_marker}\n{contributions_content}{end_marker}\n\n---\n\n**Learn more by visiting my website",
                    readme_content
                )
            else:
                # Fallback: add at the end
                readme_content = readme_content.rstrip()
                if not readme_content.endswith('\n'):
                    readme_content += '\n'
                readme_content += f"\n{start_marker}\n{contributions_content}{end_marker}\n"
        else:
            # Replace existing contributions section
            pattern = re.escape(start_marker) + r'.*?' + re.escape(end_marker)
            readme_content = re.sub(
                pattern,
                f"{start_marker}\n{contributions_content}{end_marker}",
                readme_content,
                flags=re.DOTALL
            )

        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print("README.md updated successfully")
        return True
    except Exception as e:
        print(f"Error updating README: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN not set. API rate limits will be restrictive.")

    # Fetch contributed repositories
    repo_names = fetch_contributed_repos()

    if not repo_names:
        print("No contributed repositories found")
        return False

    # Fetch detailed information
    repos = fetch_repo_details(repo_names)

    if not repos:
        print("Could not fetch repository details")
        return False

    print(f"Successfully fetched details for {len(repos)} repositories")

    # Format as markdown
    contributions_content = format_contributions(repos)

    # Update README
    success = update_readme(contributions_content)

    if success:
        print("Contributions update completed successfully!")

    return success

if __name__ == "__main__":
    main()
