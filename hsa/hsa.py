import os
import requests
import time
from datetime import datetime
import pytz
import asyncio
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
    ["稀土掘金", "mobileUrl"], ["知乎", "url"],
    ["哔哩哔哩", "mobileUrl"], ["澎湃新闻", "url"]
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

def fetch_hot_data(platform):
    """获取指定平台的热搜数据"""
    url = f"{API_BASE_URL}?title={platform}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 200:
            return data.get("data", [])
        else:
            print(f"警告：{platform} API返回错误：{data.get('message')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"错误：请求{platform}时发生异常：{str(e)}")
        return []

def fetch_news_data(source):
    """获取指定来源的新闻数据"""
    params = {
        'apiKey': NEWS_API_KEY,
        'sources': source,
        'pageSize': 20
    }
    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok":
            print(data.get("articles", []))
            return data.get("articles", [])
        else:
            print(f"警告：{source} API返回错误：{data.get('message')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"错误：请求{source}时发生异常：{str(e)}")
        return []

def fetch_news_data_category(category):
    """获取指定来源的新闻数据"""
    params = {
        'apiKey': NEWS_API_KEY,
        'category': category,
        'pageSize': 20
    }
    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok":
            print(data.get("articles", []))
            return data.get("articles", [])
        else:
            print(f"警告：{source} API返回错误：{data.get('message')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"错误：请求{source}时发生异常：{str(e)}")
        return []

def format_hot_data(data_list, url_key):
    """格式化数据为可读文本，并添加序号"""
    formatted = []
    for index, item in enumerate(data_list, start=1):
        title = item.get("title", "无标题")
        link = item.get(url_key, "#")
        hot = item.get("hot", "无热度")
        formatted.append(f"{index}. [{title}]({link})_{hot}🔥_")
    return formatted

def format_news_data(articles):
    """格式化新闻数据为可读文本"""
    formatted = []
    for index, article in enumerate(articles, start=1):
        title = article.get("title", "无标题")
        link = article.get("url", "#")
        formatted.append(f"{index}. [{title}]({link})")
    print(formatted)
    return formatted

async def send_to_telegram(platform, formatted_data):
    """发送数据到 Telegram 频道"""
    # 发送前5项
    top_five = formatted_data[:5]
    message = f"*{platform}* 热搜榜单\n" + "\n".join(top_five)
    sent_message = await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode='Markdown')

    # 等待一段时间以确保消息被转发
    await asyncio.sleep(4)

    # 获取群组中的最新消息
    offset = 0  # 初始化 offset
    forwarded_message_id = None
    sent_time = sent_message.date.timestamp()  # 获取发送时间的时间戳

    while True:
        updates = await bot.get_updates(offset=offset)

        if not updates:
            break

        for update in updates:
            if update.message and update.message.chat.id == int(TELEGRAM_GROUP_ID):
                # 检查消息时间戳是否在发送时间之后
                if update.message.date.timestamp() > sent_time:
                    # 检查消息是否为转发消息
                    if update.message.is_automatic_forward:
                        forwarded_message_id = update.message.message_id
                        break

            # 更新 offset 为当前更新的 ID + 1
            offset = update.update_id + 1

        if forwarded_message_id is not None:
            break

    if forwarded_message_id is None:
        print("未找到转发的消息 ID")
        return

    # 发送剩余部分，每5个一组作为评论
    for i in range(5, len(formatted_data), 5):
        group = formatted_data[i:i+5]
        comment_message = "\n".join(group)
        await bot.send_message(chat_id=TELEGRAM_GROUP_ID, text=comment_message, parse_mode='Markdown', reply_to_message_id=forwarded_message_id)
        await asyncio.sleep(2.5)  # 避免请求过快

async def main():
    tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    init_message = await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=f"__北京时间: {current_time}__", parse_mode='Markdown')
    await bot.pin_chat_message(chat_id=TELEGRAM_CHANNEL_ID, message_id=init_message.message_id)
    await asyncio.sleep(2.5)  # 避免请求过快

    for platform in PLATFROMS:
        print(f"正在获取：{platform[0]}")
        data = fetch_hot_data(platform[0])
        if data:
            formatted = format_hot_data(data, platform[1])
            await send_to_telegram(platform[0], formatted)
        await asyncio.sleep(2.5)  # 避免请求过快

    for media in FOREIGN_MEDIA:
        print(f"正在获取：{media[0]}")
        articles = fetch_news_data(media[1])
        if articles:
            formatted_news = format_news_data(articles)
            await send_to_telegram(media[0], formatted_news)
        await asyncio.sleep(2.5)  # 避免请求过快

    for media in CATEGORIES:
        print(f"正在获取：{media[0]}")
        articles = fetch_news_data_category(media[1])
        if articles:
            formatted_news = format_news_data(articles)
            await send_to_telegram(media[0], formatted_news)
        await asyncio.sleep(2.5)  # 避免请求过快

if __name__ == "__main__":
    asyncio.run(main())