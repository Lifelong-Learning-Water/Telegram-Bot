import os
import asyncio
import aiohttp
from datetime import datetime
import pytz
from telegram import Bot
import translators as ts

# 配置信息
API_BASE_URL = "https://api.pearktrue.cn/api/dailyhot/"
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"
NEWS_API_KEY = os.environ["NEWS_API_KEY"]
PLATFROMS = [
    ["哔哩哔哩", "mobileUrl"], ["微博", "url"],
    ["百度贴吧", "url"], ["少数派", "url"],
    ["IT之家", "url"], ["腾讯新闻", "url"],
    ["今日头条", "url"], ["36氪", "url"],
    ["澎湃新闻", "url"], ["百度", "url"],
    ["稀土掘金", "mobileUrl"], ["知乎", "url"]
]

FOREIGN_MEDIA = [
    ["彭博社", "bloomberg"],
]

CATEGORIES = [
    ["世界-商业", "business"], ["世界-科学", "science"], ["世界-技术", "technology"], ["世界-综合", "general"]
]

TELEGRAM_BOT_TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = '@hot_search_aggregation'
TELEGRAM_GROUP_ID = '-1002699038758'

bot = Bot(token=TELEGRAM_BOT_TOKEN)

session = aiohttp.ClientSession()

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if text else ""

async def fetch_data(url: str, params: dict) -> dict:
    """异步获取数据"""
    try:
        async with session.get(url, params=params, timeout=10) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        print(f"错误：请求时发生异常：{str(e)}")
        return None

async def fetch_hot_data(platform: str) -> list:
    """获取指定平台的热搜数据"""
    url = f"{API_BASE_URL}?title={platform}"
    data = await fetch_data(url, {})
    if data and data.get("code") == 200:
        return data.get("data", [])
    print(f"警告：{platform} API返回错误：{data.get('message') if data else '未知错误'}")
    return []

async def fetch_news_data(source: str = None, category: str = None) -> list:
    """获取指定来源或类别的新闻数据"""
    params = {'apiKey': NEWS_API_KEY, 'pageSize': 20}
    if source:
        params['sources'] = source
    if category:
        params['category'] = category
    data = await fetch_data(NEWS_API_URL, params)
    if data and data.get("status") == "ok":
        return data.get("articles", [])
    print(f"警告：{source or category} API返回错误：{data.get('message') if data else '未知错误'}")
    return []

async def translate_text(text: str) -> str:
    """使用 translators 翻译文本"""
    if not text:
        return ""
    try:
        return ts.translate_text(text, from_language='en', to_language='zh')
    except Exception as e:
        print(f"翻译错误：{text}，错误信息：{str(e)}")
        return text

async def format_title_and_desc(item: dict, is_news: bool) -> tuple:
    """格式化标题和描述"""
    title = item.get('title', '无标题')
    if is_news:
        title = await translate_text(title)
    title = escape_html(title)

    desc = item.get('description') or item.get('desc', '')
    if desc:
        desc = await translate_text(desc)
        if len(desc) > 150:
            desc = desc[:100] + '...'
        desc = "\n\n" + escape_html(desc)
    else:
        desc = ""

    return title, desc

async def format_data(data_list: list, url_key: str, is_news: bool = False) -> list:
    """格式化数据为可读文本，并添加序号""" 
    formatted_data = []
    for index, item in enumerate(data_list[:30], start=1):
        title, desc = await format_title_and_desc(item, is_news)
        url = item.get(url_key, '#')
        hot_info = f"<i>{item.get('hot')}🔥</i>" if not is_news and item.get('hot') else ""
        formatted_string = f"{index}. <a href=\"{url}\">{title}</a>{hot_info}{desc}"
        formatted_data.append(formatted_string)
    return formatted_data

async def send_to_telegram(platform: str, formatted_data: list) -> dict:
    """发送数据到 Telegram 频道并记录消息 ID"""
    top = formatted_data[:10]
    first_hot_search = formatted_data[0] if formatted_data else "无热搜"
    message = f"<b>{escape_html(platform)}</b> 热搜榜单\n" + "\n\n".join(top)
    sent_message = await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode='HTML')

    message_info = {
        'id': sent_message.message_id,
        'name': platform,
        'first_hot_search': first_hot_search
    }

    await asyncio.sleep(4)

    # 获取群组中的最新消息
    offset = 0
    forwarded_message_id = None
    sent_time = sent_message.date.timestamp()

    while True:
        updates = await bot.get_updates(offset=offset)
        if not updates:
            break

        for update in updates:
            if update.message and update.message.chat.id == int(TELEGRAM_GROUP_ID):
                if update.message.date.timestamp() > sent_time and update.message.is_automatic_forward:
                    forwarded_message_id = update.message.message_id
                    break
            offset = update.update_id + 1

        if forwarded_message_id is not None:
            break

    if forwarded_message_id is None:
        print("未找到转发的消息 ID")
        return message_info

    for i in range(10, len(formatted_data), 10):
        group = formatted_data[i:i + 10]
        comment_message = "\n\n".join(group)
        await bot.send_message(chat_id=TELEGRAM_GROUP_ID, text=comment_message, parse_mode='HTML', reply_to_message_id=forwarded_message_id)
        await asyncio.sleep(2)

    return message_info

async def main():
    global session
    tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    init_message = await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=f"📅(UTC+8): <b>{current_time}</b>", parse_mode='HTML')
    await bot.pin_chat_message(chat_id=TELEGRAM_CHANNEL_ID, message_id=init_message.message_id)
    await asyncio.sleep(2)

    all_message_info = []

    tasks = []
    for media in FOREIGN_MEDIA:
        tasks.append(fetch_news_data(source=media[1]))

    for category in CATEGORIES:
        tasks.append(fetch_news_data(category=category[1]))

    for platform in PLATFROMS:
        tasks.append(fetch_hot_data(platform[0]))

    results = await asyncio.gather(*tasks)

    for i, media in enumerate(FOREIGN_MEDIA):
        articles = results[i]
        if articles:
            formatted_news = await format_data(articles, 'url', is_news=True)
            message_info = await send_to_telegram(media[0], formatted_news)
            all_message_info.append(message_info)

    for i, category in enumerate(CATEGORIES, start=len(FOREIGN_MEDIA)):
        articles = results[i]
        if articles:
            formatted_news = await format_data(articles, 'url', is_news=True)
            message_info = await send_to_telegram(category[0], formatted_news)
            all_message_info.append(message_info)

    for i, platform in enumerate(PLATFROMS, start=len(FOREIGN_MEDIA) + len(CATEGORIES)):
        data = results[i]
        if data:
            formatted = await format_data(data, platform[1])
            message_info = await send_to_telegram(platform[0], formatted)
            all_message_info.append(message_info)

    if all_message_info:
        jump_message = f"📅(UTC+8): <b>{current_time}</b>\n\n"
        links = []

        for info in all_message_info:
            link = f"<a href='https://t.me/{TELEGRAM_CHANNEL_ID[1:]}/{info['id']}'>{escape_html('☞ ' + info['name'])}</a>\n\n首条: {info['first_hot_search'][3:]}"
            links.append(link)

        jump_message += "\n\n".join(links)
        share_message = jump_message + "\n\n<i><a href='https://github.com/Lifelong-Learning-Water/Telegram-Bot/'>开源项目</a>，欢迎共同维护！</i>"
        await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=share_message, parse_mode='HTML')

    await session.close()

if __name__ == '__main__':
    asyncio.run(main())