import os
import requests
import time
import asyncio
from telegram import Bot

# 配置信息
API_BASE_URL = "https://api.pearktrue.cn/api/dailyhot/"
PLATFROMS = [
    ["百度", "url"], ["知乎", "url"], ["百度贴吧", "url"], ["少数派", "url"], ["IT之家", "url"],
    ["澎湃新闻", "url"], ["今日头条", "url"], ["36氪", "url"], ["稀土掘金", "mobileUrl"], ["腾讯新闻", "url"]
]

TELEGRAM_BOT_TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = '@hot_search_aggregation'

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

def format_hot_data(data_list, url_key):
    """格式化数据为可读文本"""
    formatted = []
    for item in data_list:
        title = item.get("title", "无标题")
        link = item.get(url_key, "#")
        hot = item.get("hot", "无热度")
        formatted.append(f"- [{title}]({link}) (热度: {hot})")
    return formatted

async def send_to_telegram(platform, formatted_data):
    """发送数据到 Telegram 频道"""
    # 发送前5项
    top_five = formatted_data[:5]
    message = f"**{platform} 热搜榜单**\n" + "\n".join(top_five)
    sent_message = await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode='Markdown')

    # 发送剩余部分，每5个一组作为评论
    for i in range(5, len(formatted_data), 5):
        group = formatted_data[i:i+5]
        comment_message = "\n".join(group)
        await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=comment_message, parse_mode='Markdown', reply_to_message_id=sent_message.message_id)

async def main():
    for platform in PLATFROMS:
        print(f"正在获取：{platform[0]}")
        data = fetch_hot_data(platform[0])
        if data:
            formatted = format_hot_data(data, platform[1])
            await send_to_telegram(platform[0], formatted)
        time.sleep(1)  # 避免请求过快

if __name__ == "__main__":
    asyncio.run(main())