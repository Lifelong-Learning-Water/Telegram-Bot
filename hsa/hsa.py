import os
import requests
from bs4 import BeautifulSoup
from pytrends.request import TrendReq
import telegram

# 配置信息（替换为您的信息）
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHANNEL_ID = '@your_channel_username'  # 例如：@mychannel
WEIBO_URL = 'https://m.weibo.cn/api/statuses/hot_topic_list'
GOOGLE_TRENDS_HL = 'zh-CN'  # 语言设置（中文）
GOOGLE_TRENDS_TZ = 360      # 时区设置（中国标准时间）

def get_weibo_hot():
    """获取微博热搜"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        response = requests.get(WEIBO_URL, headers=headers, timeout=10)
        data = response.json()
        return [item['name'] for item in data['data']['hot_list']]
    except Exception as e:
        print(f"获取微博热搜失败: {str(e)}")
        return []

def get_google_trends():
    """获取Google Trends实时热搜"""
    try:
        pytrends = TrendReq(hl=GOOGLE_TRENDS_HL, tz=GOOGLE_TRENDS_TZ, timeout=(10, 25), retries=2)
        trends = pytrends.trending_searches(pn='united_states')  # 可调整国家代码
        return trends[0].tolist()[:10]  # 取前10个
    except Exception as e:
        print(f"获取Google Trends失败: {str(e)}")
        return []

def send_to_telegram(message):
    """发送消息到Telegram频道"""
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode='Markdown')
        print("消息发送成功！")
    except Exception as e:
        print(f"发送失败: {str(e)}")

def main():
    # 获取热搜数据
    weibo_hot = get_weibo_hot()
    google_trends = get_google_trends()
    
    # 构建消息内容
    message = "🔥 当前热搜榜单 🌟\n\n"
    message += "### 微博热搜\n"
    for idx, topic in enumerate(weibo_hot[:10], 1):
        message += f"{idx}. {topic}\n"
    
    message += "\n### Google Trends热搜\n"
    for idx, topic in enumerate(google_trends[:10], 1):
        message += f"{idx}. {topic}\n"
    
    # 发送到Telegram
    send_to_telegram(message)

if __name__ == "__main__":
    main()