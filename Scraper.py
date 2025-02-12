import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Google Custom Search API configuration
GOOGLE_API_KEY = ""
SEARCH_ENGINE_ID = ""

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
        print("\n🔍 Google API Response:", data)  # Debugging line
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

import time

def get_website_text(url):
    """
    Fetches a webpage using requests. If it returns status 202 or fails, it switches to Selenium.
    Uses a User-Agent header to avoid bot detection.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for attempt in range(2):  # Try requests twice before switching to Selenium
        try:
            response = requests.get(url, timeout=10, headers=headers)
            
            if response.status_code == 202:
                print(f"⚠️ Server returned 202 for {url}. Retrying in 3 seconds...")
                time.sleep(3)
                continue  # Retry loop
            
            if response.status_code != 200:
                print(f"❌ Error {response.status_code} fetching {url}. Switching to Selenium.")
                return get_website_text_selenium(url)  # Use Selenium
            
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

            for tag in soup(["script", "style"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            print(f"📝 Extracted {len(text)} characters from {url}")

            if len(text) < 50:  # If content is too small, try Selenium
                print(f"⚠️ Content might be hidden in JavaScript! Using Selenium for {url}")
                return get_website_text_selenium(url)
            
            return text
        
        except Exception as e:
            print(f"⚠️ Error fetching {url} with requests: {e}. Switching to Selenium.")
            return get_website_text_selenium(url)

    print(f"⚠️ All request attempts failed for {url}. Switching to Selenium.")
    return get_website_text_selenium(url)

def get_website_text_selenium(url):
    """
    Uses Selenium to fetch content from JavaScript-heavy pages.
    Runs Chrome in headless mode and ensures text is extracted.
    """
    print(f"🌐 Using Selenium to fetch {url}...")

    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")

    # Initialize the WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.get(url)
    time.sleep(5)  # Allow JavaScript to load

    try:
        text = driver.find_element("tag name", "body").text  # Get full page text
    except Exception as e:
        print(f"⚠️ Error extracting text with Selenium for {url}: {e}")
        text = ""

    driver.quit()
    
    print(f"📝 Extracted {len(text)} characters using Selenium for {url}")
    return text



def find_page_via_google(homepage, candidate_phrases, api_key, cx):
    """
    Searches Google for relevant pages (e.g., About Us, Programs).
    Returns the first valid URL and its content.
    """
    base_domain = get_base_url(homepage)  # Get base domain

    for phrase in candidate_phrases:
        query = f"site:{base_domain} {phrase}"
        print(f"🔎 Searching Google for: {query}")
        
        results = search_google(query, api_key, cx)
        if not results:
            print(f"⚠️ No results found for: {query}")
            continue  # Skip if no results
        
        for result in results:
            url = result.get("link")
            print(f"✅ Checking URL: {url}")  # Debugging
            
            if url and get_base_url(url) == base_domain and url != homepage:
                content = get_website_text(url)
                if content:  # Ensure the page has content
                    print(f"🎯 Found valid page: {url}")
                    return url, content

    return None, None  # No valid result found

# Define candidate search phrases for each type of page.
about_candidate_phrases = ["about us", "about-us", "about", "company info", "our story"]
programs_candidate_phrases = ["programs", "training", "courses", "classes", "workshops"]

# List of website homepage URLs.
websites = [
    "https://www.alliance-francaise.ca/",
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
    
    # Store results
    data.append({
        "Homepage": homepage,
        "About_Page": about_url,
        "About_Content": about_content[:500],  # Limit content preview
        "Programs_Page": programs_url,
        "Programs_Content": programs_content[:500]  # Limit content preview
    })

# Convert results to a DataFrame and save to CSV
df = pd.DataFrame(data)
df.to_csv("scraped_pages_google.csv", index=False, encoding='utf-8-sig')

print("\n✅ CSV file created successfully!")
