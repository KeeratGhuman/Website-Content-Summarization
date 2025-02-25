import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse
import time
import re

# Import SeleniumBase's SB manager for UC Mode
from seleniumbase import SB

# Google Custom Search API configuration
GOOGLE_API_KEY = "AIzaSyCYtY13p3-ofE0XH6ouOLVdY59v4NUFqnY"
SEARCH_ENGINE_ID = "90158360fb94b4675"

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
        data = response.json()
        print("\n🔍 Google API Response:", data)
        return data.get("items", [])
    else:
        print("❌ Google search API error:", response.status_code, response.text)
        return []

def get_base_url(url):
    """
    Extracts the base domain from a URL.
    Example: "https://www.example.com/some/path" → "example.com"
    """
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")

def get_website_text(url):
    """
    Attempts to fetch a webpage using requests.
    If a Cloudflare challenge or other issue is detected, it falls back to SeleniumBase UC mode.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, timeout=10, headers=headers)
        
        # If the status is not OK, fall back to SeleniumBase UC mode.
        if response.status_code != 200:
            print(f"❌ Error {response.status_code} fetching {url}. Falling back to SeleniumBase UC mode.")
            return get_website_text_selenium(url)
        
        response.encoding = response.apparent_encoding

        # Check for typical Cloudflare challenge indicators.
        lower_text = response.text.lower()
        if ("verify you are human" in lower_text or 
            "cf-browser-verification" in response.text or 
            "attention required" in lower_text):
            print(f"⚠️ Cloudflare challenge detected for {url}. Using SeleniumBase UC mode.")
            return get_website_text_selenium(url)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        
        # If the text seems too short, it might be that the real content is loaded dynamically.
        if len(text) < 50:
            print(f"⚠️ Content too short for {url}. Possibly dynamic content. Using SeleniumBase UC mode.")
            return get_website_text_selenium(url)
        
        print(f"📝 Extracted {len(text)} characters from {url} using requests.")
        return text
    except Exception as e:
        print(f"⚠️ Exception during requests for {url}: {e}. Using SeleniumBase UC mode.")
        return get_website_text_selenium(url)

def get_website_text_selenium(url):
    """
    Uses SeleniumBase in UC Mode (Undetected-Chromedriver) in headless mode
    to fetch page content, bypassing anti-bot measures and Cloudflare challenges.
    
    The headless mode means that Chrome runs in the background without opening any windows.
    """
    print(f"🌐 Using SeleniumBase UC mode (headless) to fetch {url}...")
    with SB(uc=True, headless=True, test=True) as sb:
        try:
            sb.uc_open_with_reconnect(url, reconnect_time=4)
        except Exception as e:
            print(f"❌ Error connecting with SeleniumBase UC mode for {url}: {e}")
            return ""
        
        try:
            sb.uc_gui_handle_captcha()
        except Exception as e:
            print("ℹ️ No captcha handling required or encountered an issue:", e)
        
        text = sb.get_text("body")
        print(f"📝 Extracted {len(text)} characters using SeleniumBase UC mode for {url}")
        return text

def summarize_text(text, num_sentences=2):
    """
    Cleans up the text by collapsing multiple spaces and returns the first couple of sentences.
    """
    # Collapse whitespace and strip leading/trailing spaces.
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    # Split text into sentences using a simple regex.
    sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
    if len(sentences) < num_sentences:
        return cleaned_text
    return " ".join(sentences[:num_sentences])

def find_page_via_google(homepage, candidate_phrases, api_key, cx):
    """
    Searches Google for relevant pages (e.g., About Us, Programs).
    Returns the first valid URL and its content.
    """
    base_domain = get_base_url(homepage)

    for phrase in candidate_phrases:
        query = f"site:{base_domain} {phrase}"
        print(f"🔎 Searching Google for: {query}")
        
        results = search_google(query, api_key, cx)
        if not results:
            print(f"⚠️ No results found for: {query}")
            continue
        
        for result in results:
            url = result.get("link")
            print(f"✅ Checking URL: {url}")
            
            if url and get_base_url(url) == base_domain and url != homepage:
                content = get_website_text(url)
                if content:
                    print(f"🎯 Found valid page: {url}")
                    return url, content

    return None, None

# Candidate search phrases for each type of page.
about_candidate_phrases = ["about us", "about-us", "about", "company info", "our story"]
programs_candidate_phrases = ["programs", "training", "courses", "classes", "workshops"]

# List of website homepage URLs.
websites = [
    "https://www.yips.com/",
    "https://www.unionvillecollege.com/",
    "https://www.alliance-francaise.ca/",
    "https://www.hwmusic.ca/", 
    # Add more homepage URLs as needed...
]

data = []

for homepage in websites:
    print(f"\n🏠 Processing website: {homepage}")
    
    # Find About Us page
    about_url, about_content = find_page_via_google(homepage, about_candidate_phrases, GOOGLE_API_KEY, SEARCH_ENGINE_ID)
    if not about_url:
        print("⚠️ No About page found via search; using homepage instead.")
        about_url = homepage
        about_content = get_website_text(homepage)
    
    # Find Programs/Training page
    programs_url, programs_content = find_page_via_google(homepage, programs_candidate_phrases, GOOGLE_API_KEY, SEARCH_ENGINE_ID)
    if not programs_url:
        print("⚠️ No Programs page found via search; using homepage instead.")
        programs_url = homepage
        programs_content = get_website_text(homepage)
    
    # Clean up and summarize the content into a couple of sentences
    about_summary = summarize_text(about_content, num_sentences=2)
    programs_summary = summarize_text(programs_content, num_sentences=2)
    
    # Store results
    data.append({
        "Homepage": homepage,
        "About_Page": about_url,
        "About_Content": about_summary,
        "Programs_Page": programs_url,
        "Programs_Content": programs_summary
    })

# Convert the results to a DataFrame and save to CSV.
df = pd.DataFrame(data)
df.to_csv("scraped_pages_uc_mode.csv", index=False, encoding='utf-8-sig')

print("\n✅ CSV file created successfully!")
