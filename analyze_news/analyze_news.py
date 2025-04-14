import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import re
import json

# 设置日志记录到文件
logging.basicConfig(
    filename='bot.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

# 记录示例
logger = logging.getLogger(__name__)
logger.info("Bot 启动")

# 你的 OpenAI API 密钥
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
# 你的 Telegram Bot API 密钥
TELEGRAM_BOT_TOKEN = os.environ['BOT_TOKEN']
# 替换为您的 API 密钥
FIRECRAWL_API_KEY = os.environ["FIRECRAWL_API_KEY"]

base_url_1 = 'https://api.chatanywhere.tech'
base_url_2 = 'http://95.53.166.141:11434'

def fetch_data_from_api(api_url):
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"请求失败: {e}")
        return None

def remove_think_tags(text):
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned_text

def extract_news_content(url):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {FIRECRAWL_API_KEY}'
    }

    data = {
        'urls': [url],
        'prompt': 'Extract the main content of the news article from the page.',
        'enableWebSearch': True
    }

    response = requests.post('https://api.firecrawl.dev/v1/extract', headers=headers, data=json.dumps(data), timeout=300)

    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            logger.info(result)
            return result['data']['json']
        else:
            logger.error("提取失败: %s", result)
            return None
    else:
        logger.error("请求失败，响应: %s", response.json())
        return None

def analyze_news(url):
    # 提取新闻正文
    text_data = extract_news_content(url)
    if not text_data:
        return "获取新闻内容失败"

    # 第二步：深度分析
    prompt_analysis = f"""
    你是一位资深的新闻分析师，擅长从多角度、多维度解读复杂的新闻事件。请根据以下要求对内容进行深入分析：
    
    1. 主要观点或核心信息：
       - 新闻的主要主题是什么？
       - 核心事件或问题是什么？
       - 关键人物或机构是谁？
       
    2. 背景信息与关联性：
       - 该新闻发生的背景是什么？
       - 与当前社会、政治、经济等领域的关联性如何？
       - 是否存在前后续的事件？
    
    3. 多方观点与立场分析：
       - 新闻中直接或间接体现了哪些不同的观点或立场？
       - 各方的动机和目的可能是什么？
       - 是否存在明显的偏见或片面性？
    
    4. 潜在影响与后果预测：
       - 该新闻可能对社会、行业或个人产生什么影响？
       - 可能引发哪些潜在的连锁反应？
       - 对未来政策、市场或公众舆论的启示是什么？
    
    5. 逻辑性和深度思考：
       - 新闻内容的逻辑结构是否严密？
       - 是否存在未解答的问题或疑问？
       - 可能的隐含意义或深层次原因是什么？
    
    请以清晰、条理性的方式呈现你的分析。
    
    新闻爬取内容如下：
    {text_data}
    """

    analysis_response = requests.post(
        f"{base_url_2}/api/chat",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": "qwq:latest",
            "messages": [
                {"role": "system", "content": "你是一位经验丰富的新闻分析专家，擅长从多角度解读复杂事件。请提供口语化的、全面的、深入的分析。"},
                {"role": "user", "content": prompt_analysis}
            ],
            "stream": False
        }
    )
    logger.info(analysis_response.json())

    if analysis_response.status_code == 200:
        analysis_data = analysis_response.json()
        return remove_think_tags(analysis_data['message']['content'])
    else:
        logger.error(f"分析模型调用失败，状态码：{analysis_response.status_code}, 响应：{analysis_response.json()}")
        return f"分析模型调用失败，状态码：{analysis_response.status_code}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('欢迎使用新闻分析Bot！请发送 /analyze <新闻链接> 进行分析。')

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text('请提供一个新闻链接，例如：/analyze https://www.example.com/news')
        return

    url = context.args[0]
    loading_message = await update.message.reply_text('加载中...耗时较长，请耐心等待')

    try:
        analysis_result = analyze_news(url)
        await context.bot.edit_message_text(chat_id=loading_message.chat.id, message_id=loading_message.message_id, text=analysis_result, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"发生错误：{str(e)}")
        await context.bot.edit_message_text(chat_id=loading_message.chat.id, message_id=loading_message.message_id, text=f"发生错误：{str(e)}")

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analyze", analyze))
    application.run_polling()

if __name__ == '__main__':
    main()