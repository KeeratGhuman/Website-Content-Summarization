import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse

# Google Custom Search API configuration
GOOGLE_API_KEY = ''
SEARCH_ENGINE_ID = ''

def search_google(query, api_key, cx):
    """
    Use the Google Custom Search API to search for the given query.
    Returns the list of result items (each having a 'link').
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": api_key,
        "cx": cx
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        print("Google search API error:", response.status_code)
        return []

def get_base_url(url):
    """
    Extracts the base URL (scheme + domain) from a full URL.
    e.g. "https://www.example.com/some/path" → "https://www.example.com"
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def get_website_text(url):
    """
    Fetches the given URL, cleans the page with BeautifulSoup by removing scripts and styles,
    and returns the plain text. Returns an empty string on error.
    """
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return ""
        # Set the encoding based on the response's apparent encoding.
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def find_page_via_google(homepage, candidate_phrases, api_key, cx):
    """
    For the given homepage URL, try each candidate phrase by building a query like:
      site:example.com "candidate phrase"
    Return the first result that:
      - Comes from the same domain (and is not simply the homepage)
      - Returns some text content.
    If no candidate yields a valid page, returns (None, None).
    """
    base = get_base_url(homepage)
    for phrase in candidate_phrases:
        query = f"site:{base} {phrase}"
        print("Searching with query:", query)
        results = search_google(query, api_key, cx)
        for result in results:
            url = result.get('link')
            # Make sure the URL is on the same domain and is not the homepage
            if url and get_base_url(url) == base and url != base:
                content = get_website_text(url)
                if content:
                    return url, content
    return None, None

# Define candidate search phrases for each type of page.
about_candidate_phrases = [
    "about us",
    "about-us",
    "about",
    "company info",
    "our story"
]

programs_candidate_phrases = [
    "programs",
    "training",
    "courses",
    "classes",
    "workshops"
]

# List of website homepage URLs you already have.
websites = [
    "https://www.alliance-francaise.ca/",
    "https://www.unionvillecollege.com/",
    # Add more homepage URLs as needed...
]

data = []

for homepage in websites:
    print(f"\nProcessing website: {homepage}")
    
    # Try to find an About Us page via the Google search API.
    about_url, about_content = find_page_via_google(homepage, about_candidate_phrases, GOOGLE_API_KEY, SEARCH_ENGINE_ID)
    if not about_url:
        print("No About page found via search; falling back to homepage.")
        about_url = homepage
        about_content = get_website_text(homepage)
    
    # Try to find a Programs/Training page via the Google search API.
    programs_url, programs_content = find_page_via_google(homepage, programs_candidate_phrases, GOOGLE_API_KEY, SEARCH_ENGINE_ID)
    if not programs_url:
        print("No Programs page found via search; falling back to homepage.")
        programs_url = homepage
        programs_content = get_website_text(homepage)
    
    # Save the results in our data list.
    data.append({
        "Homepage": homepage,
        "About_Page": about_url,
        "About_Content": about_content,
        "Programs_Page": programs_url,
        "Programs_Content": programs_content
    })

# Create a DataFrame and export the results to a CSV file with proper encoding.
df = pd.DataFrame(data)
df.to_csv("scraped_pages_google.csv", index=False, encoding='utf-8-sig')
print("CSV file created successfully!")
