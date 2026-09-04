import feedparser
import requests
import google.generativeai as genai
import os
import re
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL = os.getenv('TELEGRAM_CHANNEL')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

# Отладка: выводим, какие переменные загружены
print(f"TELEGRAM_BOT_TOKEN: {'OK' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
print(f"TELEGRAM_CHANNEL: {'OK' if TELEGRAM_CHANNEL else 'MISSING'}")
print(f"GEMINI_API_KEY: {'OK' if GEMINI_API_KEY else 'MISSING'}")
print(f"PEXELS_API_KEY: {'OK' if PEXELS_API_KEY else 'MISSING'}")
print(f"PEXELS_API_KEY length: {len(PEXELS_API_KEY) if PEXELS_API_KEY else 0}")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.6-flash')

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
                image_url = None
                if hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url')
                elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get('url')
                elif hasattr(entry, 'summary'):
                    img_match = re.search(r'<img[^>]+src="([^"]+)"', entry.summary)
                    if img_match:
                        image_url = img_match.group(1)
                
                news_item = {
                    'title': entry.title,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'link': entry.link,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else 'Unknown',
                    'image': image_url
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
- Short and concise (3-5 sentences per section max!)
- Use 2-3 emojis (moderately)
- Add an interesting fact or useful tip
- End with a call to action

POST STRUCTURE (use exact formatting):

1. HEADLINE with emoji (bold)
2. Main text (2-3 sentences)

3. 🔥 **Main feature:** (bold heading)
   Description (1-2 sentences)

4. 💡 **Lifehack:** (bold heading)
   Practical tip (2-3 sentences)

5. Question to audience with emoji

6. Hashtags at the end: #рецепты #вкуснодом #готовка #еда

NEWS TO PROCESS:
Title: {news_item['title']}
Content: {news_item['summary'][:600]}
Source: {news_item['source']}

Create the post in RUSSIAN language. Do not copy the news text - rewrite it!
Use Telegram Markdown: *bold* for headings, normal text for body."""
    
    try:
        response = model.generate_content(prompt)
        post_text = response.text.strip()
        print(f"OK Post created ({len(post_text)} chars)")
        return post_text
    except Exception as e:
        print(f"Error Gemini AI: {e}")
        return None

def get_image_for_post(news_item):
    """Get image URL for the post"""
    print("Getting image...")
    
    # 1. Если есть картинка в RSS — используем её
    if news_item.get('image'):
        print(f"  OK Using image from RSS: {news_item['image']}")
        return news_item['image']
    
    # 2. Ищем фото на Pexels (реальные фото еды)
    print(f"  Checking PEXELS_API_KEY: {'OK' if PEXELS_API_KEY else 'MISSING'}")
    
    if PEXELS_API_KEY and len(PEXELS_API_KEY) > 10:
        try:
            print("  Attempting to use Pexels API...")
            
            # Используем Gemini для перевода названия на английский
            title = news_item['title'][:80]
            translate_prompt = f"Translate this Russian dish name to English (just 2-3 words, no explanations): {title}"
            translate_response = model.generate_content(translate_prompt)
            english_query = translate_response.text.strip().replace(' ', ',')
            
            print(f"  Searching Pexels for: {english_query}")
            
            headers = {'Authorization': PEXELS_API_KEY}
            url = f"https://api.pexels.com/v1/search?query={english_query}+food&per_page=1&orientation=landscape"
            
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  Pexels response status: {response.status_code}")
            
            result = response.json()
            
            if result.get('photos') and len(result['photos']) > 0:
                photo = result['photos'][0]
                image_url = photo['src']['medium']
                print(f"  OK Found on Pexels: {image_url}")
                return image_url
            else:
                print(f"  No photos found on Pexels. Response: {result}")
        except Exception as e:
            print(f"  Error with Pexels: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("  PEXELS_API_KEY is missing or too short, skipping Pexels")
    
    # 3. Fallback: генерируем через Pollinations.ai (улучшенное качество)
    try:
        print("  Using Pollinations.ai as fallback...")
        title = news_item['title'][:50]
        image_prompt = f"professional food photography, delicious dish close-up, {title}, studio lighting, ultra high quality, 8k resolution, sharp focus, restaurant plating, gourmet, detailed".replace(' ', '%20')
        image_url = f"https://image.pollinations.ai/prompt/{image_prompt}?width=1200&height=900&nologo=true&seed=42&enhance=true"
        print(f"  OK Generated image: {image_url}")
        return image_url
    except Exception as e:
        print(f"  Error generating image: {e}")
        return None

def publish_to_telegram(post_text, news_link, image_url=None):
    print("Publishing to Telegram...")
    
    full_caption = f"{post_text}\n\n Подробнее: {news_link}"
    
    if image_url:
        # Telegram ограничивает caption до 1024 символов
        # Обрезаем до 1000, чтобы точно влезло
        if len(full_caption) > 1000:
            max_text_len = 1000 - len(f"\n\n🔗 Подробнее: {news_link}")
            if max_text_len > 100:
                post_text = post_text[:max_text_len] + "..."
            full_caption = f"{post_text}\n\n🔗 Подробнее: {news_link}"
        
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        photo_data = {
            'chat_id': TELEGRAM_CHANNEL,
            'photo': image_url,
            'caption': full_caption,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(photo_url, json=photo_data)
            result = response.json()
            
            if result.get('ok'):
                print("Photo with caption published OK!")
                return True
            else:
                print(f"Error publishing photo: {result}")
                print("Trying to send text only...")
                return send_text_only(full_caption)
                
        except Exception as e:
            print(f"Error sending photo: {e}")
            return send_text_only(full_caption)
    else:
        return send_text_only(full_caption)

def send_text_only(text):
    """Отправка только текста (запасной вариант)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    data = {
        'chat_id': TELEGRAM_CHANNEL,
        'text': text,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('ok'):
            print("Text message published OK!")
            return True
        else:
            print(f"Error publishing text: {result}")
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
        print(f"  PEXELS_API_KEY: {'OK' if PEXELS_API_KEY else 'X (optional)'}")
        return
    
    news_list = get_news()
    
    if not news_list:
        print("No news. Exiting.")
        return
    
    news = news_list[0]
    print(f"\nProcessing: {news['title'][:50]}...")
    
    post = create_post(news)
    
    if not post:
        print("\nFailed to create post.")
        return
    
    image_url = get_image_for_post(news)
    
    success = publish_to_telegram(post, news['link'], image_url)
    
    if success:
        print("\nAll done!")
    else:
        print("\nFailed to publish.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
