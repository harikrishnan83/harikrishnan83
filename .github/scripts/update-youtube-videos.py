#!/usr/bin/env python3
"""
Script to fetch YouTube videos from playlist RSS feed and update README.md
"""

import xml.etree.ElementTree as ET
import urllib.request
import re
from datetime import datetime

# Configuration
PLAYLIST_ID = "PLPK-HeXEV3yB8Nghu1qFgPHd2XvaJhSR_"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?playlist_id={PLAYLIST_ID}"
README_PATH = "README.md"
NUM_VIDEOS = 5

# XML namespaces
ns = {
    'atom': 'http://www.w3.org/2005/Atom',
    'media': 'http://search.yahoo.com/mrss/',
    'yt': 'http://www.youtube.com/xml/schemas/2015'
}

def fetch_rss_feed(url):
    """Fetch RSS feed from URL"""
    try:
        if not url.startswith(('http://', 'https://')):
            print(f"Invalid URL scheme: {url}")
            return None

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (GitHub-Profile-Updater)')

        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get('Content-Type', '')
            if not any(ct in content_type.lower() for ct in ['xml', 'rss', 'atom', 'application/xml', 'text/xml']):
                print(f"Warning: Unexpected content type: {content_type}")

            content = response.read(5 * 1024 * 1024)
            return content.decode('utf-8')
    except urllib.error.HTTPError as e:
        print(f"HTTP Error fetching RSS feed: {e.code} {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URL Error fetching RSS feed: {e.reason}")
        return None
    except Exception as e:
        print(f"Error fetching RSS feed: {e}")
        return None

def parse_youtube_feed(rss_content):
    """Parse YouTube Atom feed and extract video information"""
    try:
        root = ET.fromstring(rss_content)
        videos = []

        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns)
            link = entry.find('atom:link', ns)
            pub_date = entry.find('atom:published', ns)
            media_group = entry.find('media:group', ns)

            if title is not None:
                link_href = ''
                if link is not None and link.get('href'):
                    link_href = link.get('href')

                description = ''
                if media_group is not None:
                    media_desc = media_group.find('media:description', ns)
                    if media_desc is not None and media_desc.text:
                        description = media_desc.text

                video_data = {
                    'title': title.text or '',
                    'link': link_href,
                    'date': parse_date(pub_date.text) if pub_date is not None else 'Unknown',
                    'description': extract_description(description, 150)
                }
                videos.append(video_data)

                if len(videos) >= NUM_VIDEOS:
                    break

        return videos
    except Exception as e:
        print(f"Error parsing feed: {e}")
        import traceback
        traceback.print_exc()
        return []

def parse_date(date_string):
    """Parse ISO date format and return formatted date"""
    try:
        date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return date_obj.strftime('%B %d, %Y')
    except Exception:
        return date_string

def extract_description(text, max_length=150):
    """Extract plain text description"""
    if not text:
        return ''

    text = text[:10000]
    clean_text = re.sub(r'\s+', ' ', text).strip()

    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length].rsplit(' ', 1)[0] + '...'
    return clean_text

def format_video_list(videos):
    """Format videos as markdown"""
    if not videos:
        return "## Latest Videos from Intent Driven Dev\n\n_Unable to fetch videos at this time._\n\n[View all videos](https://www.youtube.com/playlist?list=PLPK-HeXEV3yB8Nghu1qFgPHd2XvaJhSR_)\n"

    markdown = "## Latest Videos from Intent Driven Dev\n\n"
    for video in videos:
        markdown += f"📺 **[{video['title']}]({video['link']})** ({video['date']})\n"
        if video['description']:
            markdown += f"   {video['description']}\n"
        markdown += "\n"

    markdown += "[View all videos](https://www.youtube.com/playlist?list=PLPK-HeXEV3yB8Nghu1qFgPHd2XvaJhSR_)\n"
    return markdown

def update_readme(video_content):
    """Update README.md with video content"""
    try:
        with open(README_PATH, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        start_marker = "<!-- YOUTUBE-VIDEOS-START -->"
        end_marker = "<!-- YOUTUBE-VIDEOS-END -->"

        if start_marker not in readme_content:
            readme_content = readme_content.rstrip()
            if not readme_content.endswith('\n'):
                readme_content += '\n'
            readme_content += f"\n{start_marker}\n{video_content}{end_marker}\n"
        else:
            pattern = re.escape(start_marker) + r'.*?' + re.escape(end_marker)
            readme_content = re.sub(pattern, f"{start_marker}\n{video_content}{end_marker}",
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
    print("Fetching YouTube RSS feed...")
    rss_content = fetch_rss_feed(RSS_URL)

    if not rss_content:
        print("Failed to fetch RSS feed")
        return False

    print(f"Parsing {NUM_VIDEOS} most recent videos...")
    videos = parse_youtube_feed(rss_content)

    if not videos:
        print("No videos found in RSS feed")
        return False

    print(f"Found {len(videos)} videos")
    video_content = format_video_list(videos)

    print("Updating README.md...")
    success = update_readme(video_content)

    if success:
        print("YouTube videos update completed successfully!")

    return success

if __name__ == "__main__":
    main()
