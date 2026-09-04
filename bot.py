import feedparser
import requests
import google.generativeai as genai
import os
from datetime import datetime

# Настройки из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL = os.getenv('TELEGRAM_CHANNEL')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Настройка Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# RSS ленты с кулинарными новостями (русскоязычные)
RSS_FEEDS = [
    'https://eda.ru/rss',
    'https://www.gastronom.ru/rss',
    'https://t-j.ru/tag/food/feed/',
]

def get_news():
    """Получаем новости из RSS лент"""
    print(f"[{datetime.now()}] Получение новостей...")
    all_news = []
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            print(f"  ✓ {feed_url}: найдено {len(feed.entries)} новостей")
            
            for entry in feed.entries[:2]:
                news_item = {
                    'title': entry.title,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'link': entry.link,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else 'Unknown'
                }
                all_news.append(news_item)
                
        except Exception as e:
            print(f"   Ошибка парсинга {feed_url}: {e}")
    
    print(f"Всего новостей: {len(all_news)}")
    return all_news

def create_post(news_item):
    """AI создаёт увлекательный пост для Telegram"""
    print("Создание поста с помощью AI...")
    
    prompt = f"""
Ты — профессиональный кулинарный редактор и SMM-специалист Telegram канала "ВкусноДом AI".

Твоя задача: создать увлекательный пост на основе кулинарной новости.

СТИЛЬ:
- Дружелюбный, живой, с лёгким юмором
- Кратко (3-5 предложений, не больше!)
- Используй 2-3 эмодзи (умеренно)
- Добавь интересный факт или полезный совет
- В конце призыв к действию

СТРУКТУРА ПОСТА:
1. Цепляющий заголовок с эмодзи
2. Основная информация (2-3 предложения)
3. 💡 Интересный факт или лайфхак
4. 👉 Призыв (попробуй, поделись мнением, переходи на сайт)

НОВОСТЬ ДЛЯ ОБРАБОТКИ:
Заголовок: {news_item['title']}
Содержание: {news_item['summary'][:600]}
Источник: {news_item['source']}

Создай пост на РУССКОМ языке. Не копируй текст новости — переработай его!
"""
    
    try:
        response = model.generate_content(prompt)
        post_text = response.text.strip()
        print(f"✓ Пост создан ({len(post_text)} символов)")
        return post_text
    except Exception as e:
        print(f"✗ Ошибка Gemini AI: {e}")
        return None

def publish_to_telegram(post_text, news_link):
    """Публикуем пост в Telegram канал"""
    print("Публикация в Telegram...")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    full_text = f"{post_text}\n\n🔗 Подробнее: {news_link}"
    
    data = {
        'chat_id': TELEGRAM_CHANNEL,
        'text': full_text,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('ok'):
            print("✅ Опубликовано в Telegram!")
            return True
        else:
            print(f"✗ Ошибка публикации: {result}")
            return False
            
    except Exception as e:
        print(f"✗ Ошибка отправки в Telegram: {e}")
        return False

def main():
    """Основная функция бота"""
    print("=" * 50)
    print(f"[{datetime.now()}] Запуск бота ВкусноДом AI")
    print("=" * 50)
    
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL, GEMINI_API_KEY]):
        print("❌ Ошибка: не все переменные окружения установлены!")
        print(f"  TELEGRAM_BOT_TOKEN: {'✓' if TELEGRAM_BOT_TOKEN else '✗'}")
        print(f"  TELEGRAM_CHANNEL: {'✓' if TELEGRAM_CHANNEL else '✗'}")
        print(f"  GEMINI_API_KEY: {'✓' if GEMINI_API_KEY else '✗'}")
        return
    
    news_list = get_news()
    
    if not news_list:
        print("❌ Новостей нет. Завершаю работу.")
        return
    
    news = news_list[0]
    print(f"\nОбрабатываю новость: {news['title'][:50]}...")
    
    post = create_post(news)
    
    if post:
        success = publish_to_telegram(post, news['link'])
        
        if success:
            print("\n Всё успешно! До встречи.")
        else:
            print("\n✗ Не удалось опубликовать.")
    else:
        print("\n Не удалось создать пост.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
