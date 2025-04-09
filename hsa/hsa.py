import os
import asyncio
import aiohttp
from datetime import datetime
import pytz
from telegram import Bot

# 配置信息
API_BASE_URL = "https://api.pearktrue.cn/api/dailyhot/"
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"
NEWS_API_KEY = os.environ["NEWS_API_KEY"]
PLATFROMS = [
    ["百度", "url"], ["微博", "url"],
    ["百度贴吧", "url"], ["少数派", "url"],
    ["IT之家", "url"], ["腾讯新闻", "url"],
    ["今日头条", "url"], ["36氪", "url"],
    ["哔哩哔哩", "mobileUrl"], ["澎湃新闻", "url"],
    ["稀土掘金", "mobileUrl"], ["知乎", "url"]
]

FOREIGN_MEDIA = [
    ["BBC", "bbc-news"], ["彭博社", "bloomberg"]
]

CATEGORIES = [
    ["商业", "business"], ["科学", "science"], ["技术", "technology"], ["综合", "general"]
]

TELEGRAM_BOT_TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = '@hot_search_aggregation'
TELEGRAM_GROUP_ID = '-1002699038758'

bot = Bot(token=TELEGRAM_BOT_TOKEN)

def escape_html(text):
    """转义 HTML 特殊字符"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

async def fetch_data(url, params):
    """异步获取数据"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        except Exception as e:
            print(f"错误：请求时发生异常：{str(e)}")
            return None

async def fetch_hot_data(platform):
    """获取指定平台的热搜数据"""
    url = f"{API_BASE_URL}?title={platform}"
    data = await fetch_data(url, {})
    if data and data.get("code") == 200:
        return data.get("data", [])
    print(f"警告：{platform} API返回错误：{data.get('message') if data else '未知错误'}")
    return []

async def fetch_news_data(source=None, category=None):
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

async def translate_text(text):
    """调用翻译 API 翻译文本"""
    url = f"https://api.52vmy.cn/api/query/fanyi?msg={text}"
    translated_data = await fetch_data(url, {})
    if translated_data and 'target' in translated_data['data']:
        return translated_data['data']['target']
    print(f"翻译错误：{text}")
    return text  # 如果翻译失败，返回原文本

async def format_data(data_list, url_key, is_news=False):
    """格式化数据为可读文本，并添加序号""" 
    formatted_data = []
    for index, item in enumerate(data_list, start=1):
        title = escape_html(item.get('title', '无标题')) if not is_news else escape_html(await translate_text(item.get('title', '无标题')))
        url = item.get(url_key, '#')
        hot_info = f"<i>{item.get('hot')}🔥</i>" if not is_news and item.get('hot') else ""

        if is_news:
            desc = await translate_text(item.get('description', ''))
        elif item.get('desc'):
            desc = item.get('desc')
        else:
            desc = ''

        if desc:
            desc = "\n\n" + escape_html(desc) + "\n"

        formatted_string = f"{index}. <a href=\"{url}\">{title}</a>{hot_info}{desc}"
        formatted_data.append(formatted_string)

    return formatted_data

async def send_to_telegram(platform, formatted_data):
    """发送数据到 Telegram 频道"""
    top_five = formatted_data[:5]
    message = f"<b>{escape_html(platform)}</b> 热搜榜单\n" + "\n".join(top_five)
    sent_message = await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode='HTML')

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
        return

    for i in range(5, len(formatted_data), 5):
        group = formatted_data[i:i + 5]
        comment_message = "\n".join(group)
        await bot.send_message(chat_id=TELEGRAM_GROUP_ID, text=comment_message, parse_mode='HTML', reply_to_message_id=forwarded_message_id)
        await asyncio.sleep(2)

async def main():
    tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    init_message = await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=f"北京时间: <b>{current_time}</b>", parse_mode='HTML')
    await bot.pin_chat_message(chat_id=TELEGRAM_CHANNEL_ID, message_id=init_message.message_id)
    await asyncio.sleep(2)

    for media in FOREIGN_MEDIA:
        print(f"正在获取：{media[0]}")
        articles = await fetch_news_data(source=media[1])
        if articles:
            formatted_news = await format_data(articles, 'url', is_news=True)
            await send_to_telegram(media[0], formatted_news)
        await asyncio.sleep(2)

    for category in CATEGORIES:
        print(f"正在获取：{category[0]}")
        articles = await fetch_news_data(category=category[1])
        if articles:
            formatted_news = await format_data(articles, 'url', is_news=True)
            await send_to_telegram(category[0], formatted_news)
        await asyncio.sleep(2)

    for platform in PLATFROMS:
        print(f"正在获取：{platform[0]}")
        data = await fetch_hot_data(platform[0])
        if data:
            formatted = await format_data(data, platform[1])
            await send_to_telegram(platform[0], formatted)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())