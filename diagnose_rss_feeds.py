#!/usr/bin/env python3
"""
Diagnostic script to check RSS feed issues and propose fixes.
"""

import requests
import feedparser
from datetime import datetime
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

def diagnose_rss_feed(name, url):
    """Diagnose RSS feed issues and suggest fixes."""
    print(f"\n{'='*60}")
    print(f"DIAGNOSING: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        # Step 1: Check HTTP response
        print("1. Checking HTTP response...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"   Content-Length: {len(response.text)}")
        
        if response.status_code != 200:
            print(f"   ERROR: HTTP Error: {response.status_code}")
            return False
            
        # Step 2: Check if it's actually XML/RSS
        content = response.text.strip()
        print(f"   First 200 chars: {content[:200]}...")
        
        if not content.startswith('<?xml') and not content.startswith('<rss') and not content.startswith('<feed'):
            print("   ERROR: Content doesn't look like XML/RSS feed")
            
            # Check if it's HTML (common issue)
            if content.startswith('<!DOCTYPE html') or content.startswith('<html'):
                print("   INFO: Content appears to be HTML, not RSS")
                print("   SOLUTION: This source needs HTML scraping, not RSS parsing")
                return "needs_html_scraping"
            return False
        
        # Step 3: Try feedparser
        print("2. Testing with feedparser...")
        feed = feedparser.parse(url)
        
        print(f"   Bozo: {feed.bozo}")
        if feed.bozo:
            print(f"   Bozo Exception: {feed.bozo_exception}")
            
        print(f"   Entries found: {len(feed.entries)}")
        print(f"   Feed title: {getattr(feed.feed, 'title', 'Unknown')}")
        
        if feed.entries:
            print("   ✅ Feed has entries - should work with better error handling")
            entry = feed.entries[0]
            print(f"   Sample entry: {entry.get('title', 'No title')[:50]}...")
            return True
        else:
            print("   ❌ No entries found")
            
        # Step 4: Try manual XML parsing
        print("3. Testing manual XML parsing...")
        try:
            root = ET.fromstring(response.text)
            items = root.findall('.//item') or root.findall('.//entry')
            print(f"   XML items found: {len(items)}")
            if items:
                print("   ✅ Manual XML parsing works - need custom parser")
                return "needs_custom_parser"
        except ET.ParseError as xml_error:
            print(f"   ❌ XML Parse Error: {xml_error}")
            
        # Step 5: Try BeautifulSoup (lenient HTML/XML parser)
        print("4. Testing with BeautifulSoup...")
        try:
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item') or soup.find_all('entry')
            print(f"   BeautifulSoup items found: {len(items)}")
            if items:
                print("   ✅ BeautifulSoup works - can use as fallback parser")
                sample_item = items[0]
                title = sample_item.find('title')
                link = sample_item.find('link')
                print(f"   Sample: {title.text[:50] if title else 'No title'}...")
                return "needs_beautifulsoup_fallback"
        except Exception as bs_error:
            print(f"   ❌ BeautifulSoup Error: {bs_error}")
            
        return False
        
    except requests.RequestException as e:
        print(f"❌ Request Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

def main():
    """Main diagnostic function."""
    print(f"RSS Feed Diagnostic Report - {datetime.now()}")
    print("="*80)
    
    # Test the failing feeds
    feeds = {
        'forexlive': 'https://www.forexlive.com/feed/',
        'kabutan': 'https://kabutan.jp/news/marketnews/',  # This might not be RSS
        'poundsterlinglive': 'https://www.poundsterlinglive.com/markets'  # This might not be RSS
    }
    
    results = {}
    solutions = []
    
    for name, url in feeds.items():
        result = diagnose_rss_feed(name, url)
        results[name] = result
        
        if result == "needs_html_scraping":
            solutions.append(f"• {name}: Convert to HTML scraping source")
        elif result == "needs_custom_parser":
            solutions.append(f"• {name}: Implement custom XML parser")
        elif result == "needs_beautifulsoup_fallback":
            solutions.append(f"• {name}: Add BeautifulSoup fallback parser")
        elif result == True:
            solutions.append(f"• {name}: Improve RSS error handling (feed works but has bozo issues)")
        else:
            solutions.append(f"• {name}: Feed is broken - find alternative URL or switch to HTML scraping")
    
    # Print summary
    print(f"\n{'='*80}")
    print("DIAGNOSTIC SUMMARY")
    print(f"{'='*80}")
    
    for name, result in results.items():
        status = "✅ WORKS" if result == True else "🔄 FIXABLE" if isinstance(result, str) else "❌ BROKEN"
        print(f"{name:<20}: {status}")
    
    print(f"\n{'='*80}")
    print("RECOMMENDED SOLUTIONS")
    print(f"{'='*80}")
    for solution in solutions:
        print(solution)
    
    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    print("1. Run this script to see exact issues")
    print("2. Implement the suggested solutions")
    print("3. Update sources.yaml with correct configurations")
    print("4. Test with enhanced RSS parser that handles bozo feeds")

if __name__ == "__main__":
    main()
