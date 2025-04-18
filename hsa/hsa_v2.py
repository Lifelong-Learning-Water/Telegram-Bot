import os
import asyncio
import aiohttp
from datetime import datetime
import pytz
from telegram import Bot
import translators as ts
import re
from transformers import pipeline
import torch

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
    ["彭博社", "bloomberg"], # ["BBC", "bbc-news"]
]

CATEGORIES = [
    # ["世界-商业", "business"], ["世界-科学", "science"], ["世界-技术", "technology"], ["世界-综合", "general"]
]

TELEGRAM_BOT_TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = '@tech_news_aggregation'

# 分类频道映射
CATEGORY_CHANNELS = {
    "科技": "@tech_news_aggregation",
    "财经": "@finance_news_aggregation",
    "娱乐": "@entertainment_news_aggregation",
    "社会": "@society_news_aggregation",
    "国际": "@world_news_aggregation"
}

categories = ["科技", "财经", "娱乐", "社会", "国际", "其他"]  # 定义分类类别

bot = Bot(token=TELEGRAM_BOT_TOKEN)
# _ = ts.preaccelerate_and_speedtest()

classifier = pipeline("zero-shot-classification", 
                     model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
                     device="cuda" if torch.cuda.is_available() else "cpu")

# 更细化的中文分类类别
CATEGORIES = [
    "科技", "财经", "娱乐", "社会", "国际", 
    "体育", "健康", "教育", "军事", "汽车"
]

# 添加类别描述提高准确度
CATEGORY_DESCRIPTIONS = {
    "科技": "包括互联网、人工智能、电子产品、软件开发等技术相关内容",
    "财经": "涉及股票、金融、投资、经济政策、市场趋势等内容",
    "娱乐": "涵盖明星、电影、电视剧、音乐、综艺节目等娱乐产业内容",
    "社会": "关于民生、法律、公共事件、社会现象等社会生活内容",
    "国际": "国际关系、外交政策、全球事件等跨国内容",
    "体育": "体育赛事、运动员、体育产业相关内容",
    "健康": "医疗、养生、疾病预防、健康生活方式等内容",
    "教育": "学校教育、教育改革、考试政策、学术研究等内容",
    "军事": "国防、武器装备、军事行动、军事科技等内容",
    "汽车": "汽车行业、新车发布、汽车技术、车展等内容"
}

async def classify_text(text, categories):
    """优化后的中文文本分类函数"""
    if not text or len(text) < 3:
        return None
    
    # 预处理文本
    processed_text = preprocess_text(text)
    
    # 准备带有描述的标签
    candidate_labels = [f"{cat}: {CATEGORY_DESCRIPTIONS.get(cat, '')}" for cat in categories]
    
    try:
        result = classifier(
            processed_text, 
            candidate_labels, 
            multi_label=False,
            hypothesis_template="这个文本关于{}"  # 中文优化模板
        )
        
        # 提取最可能的类别
        best_label = result["labels"][0].split(":")[0]
        confidence = result["scores"][0]
        
        # 只返回置信度高于阈值的分类
        return best_label if confidence > 0.6 else "其他"
    except Exception as e:
        print(f"分类错误: {str(e)}")
        return None

def preprocess_text(text):
    """预处理文本以提高分类准确度"""
    if not text:
        return ""
    
    # 移除URL、特殊字符和多余空格
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\@\w+|\#', '', text)
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)  # 保留中文和基本字符
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 截断过长的文本(模型有token限制)
    return text[:500]

def escape_html(text):
    if text is None:
        return ""
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
        print(data)
        return data.get("articles", [])
    print(f"警告：{source or category} API返回错误：{data.get('message') if data else '未知错误'}")
    return []

async def translate_text(text):
    """使用 translators 翻译文本"""
    if text is None:
        return ""
    try:
        translated_text = ts.translate_text(text, translator='caiyun', from_language='en', to_language='zh')
        await asyncio.sleep(2)
        return translated_text
    except Exception as e:
        print(f"翻译错误：{text}，错误信息：{str(e)}")
        return text

async def format_and_classify_data(data_list, url_key, is_news=False):
    """格式化数据并进行分类"""
    classified_data = {category: [] for category in categories}

    for index, item in enumerate(data_list[:30], start=1):
        # 原始格式化逻辑
        title = item.get('title', '无标题') if not is_news else await translate_text(item.get('title', '无标题'))
        title = title if title is not None else '无标题'
        title = escape_html(title)
        url = item.get(url_key, '#')
        hot_info = f"<i>{item.get('hot')}🔥</i>" if not is_news and item.get('hot') else ""

        if item.get('description'):
            desc = await translate_text(item.get('description'))
        elif item.get('desc'):
            desc = item.get('desc')
        else:
            desc = ''

        if desc:
            desc = desc.replace('\n', '')
            if len(desc) > 150:
                desc = desc[:100] + '……'
            desc = "\n\n" + escape_html(desc) 
        else:
            desc = ""

        formatted_string = f"{index}. <a href=\"{url}\">{title}</a>{hot_info}{desc}"

        # 分类逻辑
        text_to_classify = f"{title} {desc}"
        category = await classify_text(text_to_classify, categories)

        if not category:  # 分类失败默认类别
            category = "社会" if not is_news else "国际"

        classified_data[category].append(formatted_string)

    return classified_data

async def send_classified_data(platform, classified_data, is_news=False):
    """按分类发送数据到不同频道"""
    # 1. 发送原始聚合数据到主频道
    all_items = []
    for category in classified_data:
        all_items.extend(classified_data[category][:5])  # 每个分类取前5条

    if all_items:
        message = f"<b>{escape_html(platform)} 热点精选</b>\n\n" + "\n\n".join(all_items[:15])
        await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode='HTML')
        await asyncio.sleep(2)

    # 2. 发送完整分类数据到各专业频道
    for category, items in classified_data.items():
        if items and category in CATEGORY_CHANNELS:
            channel_id = CATEGORY_CHANNELS[category]
            header = "📰 " if is_news else "🔥 "
            message = f"{header}<b>{escape_html(platform)} - {category}精选</b>\n\n" + "\n\n".join(items[:15])
            try:
                await bot.send_message(chat_id=channel_id, text=message, parse_mode='HTML')
                await asyncio.sleep(1)
            except Exception as e:
                print(f"发送到{channel_id}失败: {str(e)}")

async def main():
    tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    init_message = await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=f"北京时间: <b>{current_time}</b>", parse_mode='HTML')
    await bot.pin_chat_message(chat_id=TELEGRAM_CHANNEL_ID, message_id=init_message.message_id)
    await asyncio.sleep(2)

    all_message_info = []

    for platform in PLATFROMS:
        print(f"正在获取：{platform[0]}")
        data = await fetch_hot_data(platform[0])
        if data:
            classified = await format_and_classify_data(data, platform[1])
            await send_classified_data(platform[0], classified)
        await asyncio.sleep(2)

    for media in FOREIGN_MEDIA:
        print(f"正在获取：{media[0]}")
        articles = await fetch_news_data(source=media[1])
        if articles:
            classified = await format_and_classify_data(articles, 'url', is_news=True)
            await send_classified_data(media[0], classified, is_news=True)
        await asyncio.sleep(2)

if __name__ == '__main__':
    asyncio.run(main())