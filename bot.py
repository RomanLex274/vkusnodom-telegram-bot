import feedparser
import requests
import google.generativeai as genai
import os
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL = os.getenv('TELEGRAM_CHANNEL')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

RSS_FEEDS = [
    'https://eda.ru/rss',
    'https://www.gastronom.ru/rss',
    'https://t-j.ru/tag/food/feed/',
]

def get_news():
    print(f"[{datetime.now()}] Getting news...")
    all_news = []
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            print(f"  OK {feed_url}: found {len(feed.entries)} items")
            
            for entry in feed.entries[:2]:
                news_item = {
                    'title': entry.title,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'link': entry.link,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else 'Unknown'
                }
                all_news.append(news_item)
                
        except Exception as e:
            print(f"   Error parsing {feed_url}: {e}")
    
    print(f"Total news: {len(all_news)}")
    return all_news

def create_post(news_item):
    print("Creating post with AI...")
    
    prompt = f"""You are a professional culinary editor and SMM specialist for Telegram channel "VkusnoDom AI".

Create an engaging post based on this culinary news.

STYLE:
- Friendly, lively, with light humor
- Short (3-5 sentences max!)
- Use 2-3 emojis (moderately)
- Add an interesting fact or useful tip
- End with a call to action

POST STRUCTURE:
1. Catchy headline with emoji
2. Main info (2-3 sentences)
3. Interesting fact or lifehack
4. Call to action

NEWS TO PROCESS:
Title: {news_item['title']}
Content: {news_item['summary'][:600]}
Source: {news_item['source']}

Create the post in RUSSIAN language. Do not copy the news text - rewrite it!"""
    
    try:
        response = model.generate_content(prompt)
        post_text = response.text.strip()
        print(f"OK Post created ({len(post_text)} chars)")
        return post_text
    except Exception as e:
        print(f"Error Gemini AI: {e}")
        return None

def publish_to_telegram(post_text, news_link):
    print("Publishing to Telegram...")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    full_text = f"{post_text}\n\nMore: {news_link}"
    
    data = {
        'chat_id': TELEGRAM_CHANNEL,
        'text': full_text,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('ok'):
            print("Published to Telegram!")
            return True
        else:
            print(f"Publish error: {result}")
            return False
            
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False

def main():
    print("=" * 50)
    print(f"[{datetime.now()}] VkusnoDom AI Bot starting")
    print("=" * 50)
    
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL, GEMINI_API_KEY]):
        print("ERROR: not all env vars set!")
        print(f"  TELEGRAM_BOT_TOKEN: {'OK' if TELEGRAM_BOT_TOKEN else 'X'}")
        print(f"  TELEGRAM_CHANNEL: {'OK' if TELEGRAM_CHANNEL else 'X'}")
        print(f"  GEMINI_API_KEY: {'OK' if GEMINI_API_KEY else 'X'}")
        return
    
    news_list = get_news()
    
    if not news_list:
        print("No news. Exiting.")
        return
    
    news = news_list[0]
    print(f"\nProcessing: {news['title'][:50]}...")
    
    post = create_post(news)
    
    if post:
        success = publish_to_telegram(post, news['link'])
        
        if success:
            print("\nAll done!")
        else:
            print("\nFailed to publish.")
    else:
        print("\nFailed to create post.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
