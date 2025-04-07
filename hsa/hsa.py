import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, filters
import logging
import json
import os  # 确保已导入os模块

# 配置部分
BOT_TOKEN = os.environ['BOT_TOKEN']
CHANNEL_ID = '@lifelong_learning_dw'

# 需要爬取的平台（仅选择新闻类）
platforms = [
    {'name': '百度', 'title': '百度'},
    {'name': '知乎', 'title': '知乎'},
    {'name': '微博热搜', 'title': '微博热搜'},
    # 添加其他需要的平台
]

def get_hot_search(platform_title):
    """
    爬取指定平台的热搜数据
    """
    url = f'https://api.pearktrue.cn/api/dailyhot/?title={platform_title}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取{platform_title}热搜失败，状态码：{response.status_code}")
            return None
    except Exception as e:
        print(f"获取{platform_title}热搜时发生错误：{str(e)}")
        return None

def process_data(data):
    """
    处理抓取到的数据，提取需要的信息
    """
    print(data)
    if not data or data['code'] != 200:
        return []

    hot_search_list = []
    for item in data.get('data', []):
        hot_item = {
            'title': item.get('title', ''),
            'desc': item.get('desc', ''),
            'url': item.get('mobileUrl', '')
        }
        hot_search_list.append(hot_item)

    return hot_search_list

def main():
    # 初始化Telegram Bot
    updater = Updater(BOT_TOKEN, use_context=True)

    for platform in platforms:
        title = platform['name']
        data = get_hot_search(platform['title'])
        if not data:
            continue

        hot_list = process_data(data)
        if hot_list:
            # 打印抓取到的数据
            print(f"\n=== {title} 热搜 ===")
            for index, item in enumerate(hot_list, 1):
                print(f"{index}. 标题: {item['title']}")
                print(f"描述: {item['desc']}")
                print(f"链接: {item['url']}\n")
            # 如果需要发送消息，解除下行注释
            # send_to_telegram(updater, title, hot_list)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()