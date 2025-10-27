#!/usr/bin/env python3

import json
import urllib.request
import urllib.error
import re
import os

GITHUB_USERNAME = "harikrishnan83"
README_PATH = "README.md"
NUM_REPOS = 5
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

def make_github_request(url, retry_count=0, max_retries=3):
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
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining and int(rate_limit_remaining) < 10:
                print(f"Warning: Only {rate_limit_remaining} API requests remaining")

            content = response.read(10 * 1024 * 1024)
            return json.loads(content.decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason} for URL: {url}")
        if e.code == 403:
            print("Rate limit exceeded. Check API rate limits.")
            try:
                rate_limit_reset = e.headers.get('X-RateLimit-Reset')
                if rate_limit_reset:
                    import time
                    reset_time = int(rate_limit_reset) - int(time.time())
                    print(f"Rate limit resets in {reset_time} seconds")
            except Exception:
                pass
        elif e.code == 502 or e.code == 503 or e.code == 504:
            if retry_count < max_retries:
                import time
                wait_time = 2 ** retry_count
                print(f"Server error. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return make_github_request(url, retry_count + 1, max_retries)
        return None
    except urllib.error.URLError as e:
        print(f"URL Error for {url}: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error for {url}: {e}")
        return None
    except Exception as e:
        print(f"Error making request to {url}: {e}")
        return None

def fetch_contributed_repos():
    """Fetch all public repositories the user has contributed to"""
    print(f"Fetching contribution data for {GITHUB_USERNAME}...")

    contributed_repos = {}
    page = 1
    max_pages = 10

    while page <= max_pages:
        events_url = f"https://api.github.com/users/{GITHUB_USERNAME}/events/public?page={page}&per_page=100"
        events = make_github_request(events_url)

        if not events or len(events) == 0:
            break

        for event in events:
            if event.get('type') in ['PushEvent', 'PullRequestEvent', 'IssuesEvent', 'IssueCommentEvent', 'PullRequestReviewEvent']:
                repo = event.get('repo', {})
                repo_name = repo.get('name', '')

                if repo_name and repo_name not in contributed_repos:
                    contributed_repos[repo_name] = True

        page += 1

    print(f"Found {len(contributed_repos)} repositories from recent events")

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

    sorted_repos = sorted(repos, key=lambda x: x.get('stars', 0), reverse=True)
    top_repos = sorted_repos[:NUM_REPOS]

    markdown = "## Open Source Contributions\n\n"
    markdown += "Here are a few repos I have contributed to:\n\n"

    for repo in top_repos:
        full_name = repo.get('full_name', 'Unknown')
        html_url = repo.get('html_url', '#')
        stars = repo.get('stars', 0)
        language = repo.get('language', 'Various')

        if not html_url.startswith('https://github.com/'):
            print(f"Warning: Skipping invalid URL: {html_url}")
            continue

        stars_formatted = f"{stars:,}"
        language = language if language else 'Various'

        markdown += f"📦 **[{full_name}]({html_url})** "
        markdown += f"(★ {stars_formatted} | {language})\n"

        description = repo.get('description', 'No description available')
        if description:
            description = description.replace('\n', ' ').replace('\r', ' ')
            if len(description) > 120:
                description = description[:120].rsplit(' ', 1)[0] + '...'
        else:
            description = 'No description available'

        markdown += f"   {description}\n\n"

    return markdown

def update_readme(contributions_content):
    """Update README.md with contributions content"""
    try:
        with open(README_PATH, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        start_marker = "<!-- CONTRIBUTIONS-START -->"
        end_marker = "<!-- CONTRIBUTIONS-END -->"

        if start_marker not in readme_content:
            pattern = r'(\n---\n\n\*\*Learn more by visiting my website)'
            if re.search(pattern, readme_content):
                readme_content = re.sub(
                    pattern,
                    f"\n{start_marker}\n{contributions_content}{end_marker}\n\n---\n\n**Learn more by visiting my website",
                    readme_content
                )
            else:
                readme_content = readme_content.rstrip()
                if not readme_content.endswith('\n'):
                    readme_content += '\n'
                readme_content += f"\n{start_marker}\n{contributions_content}{end_marker}\n"
        else:
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
