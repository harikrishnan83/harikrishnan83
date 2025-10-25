#!/usr/bin/env python3
"""
Script to fetch blog posts from RSS feed and update README.md
"""

import xml.etree.ElementTree as ET
import urllib.request
import re
from datetime import datetime

# Configuration
RSS_URL = "https://blog.harikrishnan.io/feed.xml"
README_PATH = "README.md"
NUM_POSTS = 5

# XML namespaces
ns = {
    'atom': 'http://www.w3.org/2005/Atom',
    'content': 'http://purl.org/rss/1.0/modules/content/'
}

def fetch_rss_feed(url):
    """Fetch RSS feed from URL"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching RSS feed: {e}")
        return None

def parse_rss_feed(rss_content):
    """Parse RSS/Atom feed and extract post information"""
    try:
        root = ET.fromstring(rss_content)
        posts = []

        # Check if it's an Atom feed (has atom namespace)
        if 'http://www.w3.org/2005/Atom' in root.tag:
            # Parse Atom feed
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                link = entry.find('atom:link', ns)
                pub_date = entry.find('atom:published', ns)
                content = entry.find('atom:content', ns)
                summary = entry.find('atom:summary', ns)

                if title is not None:
                    # Get href from link element
                    link_href = ''
                    if link is not None and link.get('href'):
                        link_href = link.get('href')

                    post_data = {
                        'title': title.text or '',
                        'link': link_href,
                        'date': parse_date(pub_date.text) if pub_date is not None else 'Unknown',
                        'summary': extract_summary(
                            summary.text if summary is not None and summary.text else
                            content.text if content is not None and content.text else '',
                            150
                        )
                    }
                    posts.append(post_data)

                    if len(posts) >= NUM_POSTS:
                        break
        else:
            # Parse RSS feed (fallback)
            for item in root.findall('.//item'):
                title = item.find('title')
                link = item.find('link')
                pub_date = item.find('pubDate')
                description = item.find('description')
                content = item.find('content:encoded', ns)

                if title is not None and link is not None:
                    post_data = {
                        'title': title.text or '',
                        'link': link.text or '',
                        'date': parse_date(pub_date.text) if pub_date is not None else 'Unknown',
                        'summary': extract_summary(description.text or content.text or '', 150)
                    }
                    posts.append(post_data)

                    if len(posts) >= NUM_POSTS:
                        break

        return posts
    except Exception as e:
        print(f"Error parsing feed: {e}")
        import traceback
        traceback.print_exc()
        return []

def parse_date(date_string):
    """Parse RFC 2822 date format and return formatted date"""
    try:
        # Parse RFC 2822 format
        date_obj = datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %z')
        return date_obj.strftime('%B %d, %Y')
    except Exception:
        try:
            # Try ISO format
            date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return date_obj.strftime('%B %d, %Y')
        except Exception:
            return date_string

def extract_summary(html_text, max_length=150):
    """Extract plain text summary from HTML"""
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_text)
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    # Truncate to max length
    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length].rsplit(' ', 1)[0] + '...'
    return clean_text

def format_blog_roll(posts):
    """Format blog posts as markdown"""
    if not posts:
        return "## Latest from My Blog\n\n_Unable to fetch blog posts at this time._\n"

    markdown = "## Latest from My Blog\n\n"
    for post in posts:
        markdown += f"📝 **[{post['title']}]({post['link']})** ({post['date']})\n"
        markdown += f"   {post['summary']}\n\n"

    return markdown

def update_readme(blog_content):
    """Update README.md with blog roll content"""
    try:
        with open(README_PATH, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        # Define markers for blog section
        start_marker = "<!-- BLOG-POSTS-START -->"
        end_marker = "<!-- BLOG-POSTS-END -->"

        # Check if markers exist
        if start_marker not in readme_content:
            # Add blog section at the end before the website link
            readme_content = readme_content.rstrip()
            if not readme_content.endswith('\n'):
                readme_content += '\n'
            readme_content += f"\n{start_marker}\n{blog_content}{end_marker}\n"
        else:
            # Replace existing blog section
            pattern = re.escape(start_marker) + r'.*?' + re.escape(end_marker)
            readme_content = re.sub(pattern, f"{start_marker}\n{blog_content}{end_marker}",
                                   readme_content, flags=re.DOTALL)

        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print("README.md updated successfully")
        return True
    except Exception as e:
        print(f"Error updating README: {e}")
        return False

def main():
    """Main function"""
    print("Fetching RSS feed...")
    rss_content = fetch_rss_feed(RSS_URL)

    if not rss_content:
        print("Failed to fetch RSS feed")
        return False

    print(f"Parsing {NUM_POSTS} most recent posts...")
    posts = parse_rss_feed(rss_content)

    if not posts:
        print("No posts found in RSS feed")
        return False

    print(f"Found {len(posts)} posts")
    blog_content = format_blog_roll(posts)

    print("Updating README.md...")
    success = update_readme(blog_content)

    if success:
        print("Blog roll update completed successfully!")

    return success

if __name__ == "__main__":
    main()
