import requests
import yaml
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def load_config(path="config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https")

def crawl(config, url, folder_patterns, file_pattern, depth=0, visited=None, results=None, start_url=None):
    if visited is None:
        visited = set()
    if results is None:
        results = []
    if start_url is None:
        start_url = url

    if url in visited:
        return results
    visited.add(url)

    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return results

    soup = BeautifulSoup(resp.text, "html.parser")
    links = [a.get("href") for a in soup.find_all("a", href=True)]

    for link in links:
        abs_link = urljoin(url, link)
        if not is_valid_url(abs_link) or not abs_link.startswith(start_url):
            continue

        # print(f"Processing link: {abs_link}, link: {link}, depth: {depth}")

        # If no folder_patterns, match files at root
        if not folder_patterns:
            if re.match(file_pattern, link):
                print(f"Found file: {abs_link}")
                results.append(abs_link)
        else:
            if link.endswith('/'):
                if depth < len(folder_patterns) and re.match(folder_patterns[depth], link.strip('/')):
                    crawl(config, abs_link, folder_patterns, file_pattern, depth + 1, visited, results, start_url)
            elif depth == len(folder_patterns) and re.match(file_pattern, link):
                print(f"Found file: {abs_link}")
                results.append(abs_link)
    return results

def extract_repo_links(index_url, pattern=None):
    """Extract repo links from an HTML index page. Optionally filter by pattern.
    Removes index files (e.g., index.html, index_src.html) from the end of repo links.
    Removes duplicates.
    """
    try:
        resp = requests.get(index_url)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {index_url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = [a.get("href") for a in soup.find_all("a", href=True)]
    abs_links = [urljoin(index_url, link) for link in links if is_valid_url(urljoin(index_url, link))]
    if pattern:
        abs_links = [l for l in abs_links if re.search(pattern, l)]
    # Remove index files at the end of the URL
    cleaned_links = []
    for l in abs_links:
        # Remove trailing index files like index.html, index_src.html, etc.
        cleaned = re.sub(r'(index[^/?#]*\.html?)$', '', l.rstrip('/'))
        # Ensure trailing slash if it was removed
        if not cleaned.endswith('/'):
            cleaned += '/'
        cleaned_links.append(cleaned)
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in cleaned_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    return unique_links

def main():
    configs = load_config()
    for conf in configs:
        print(f"Crawling: {conf['title']}")
        # If the start_url is an HTML index, extract repo links first
        if conf.get("extract_repos_from_index"):
            repo_links = extract_repo_links(conf["start_url"], conf.get("repo_link_pattern"))
            for repo_url in repo_links:
                print(f"Found repo link: {repo_url}")
            for repo_url in repo_links:
                print(f"  Found repo: {repo_url}")
                results = crawl(
                    conf,
                    repo_url,
                    conf["folder_patterns"],
                    conf["file_pattern"],
                )
                print(f"  Found {len(results)} files in {repo_url}:")
                for r in results:
                    print(r)
        else:
            results = crawl(
                conf,
                conf["start_url"],
                conf["folder_patterns"],
                conf["file_pattern"],
            )
            print(f"Found {len(results)} files:")
            for r in results:
                print(r)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as e:
        print("Cancelled by user.")