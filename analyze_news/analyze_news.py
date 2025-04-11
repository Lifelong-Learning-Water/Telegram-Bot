import os
import requests
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 你的 OpenAI API 密钥
OPENAI_API_KEY = 'your_openai_api_key'
# 你的 Telegram Bot API 密钥
TELEGRAM_BOT_TOKEN = os.environ['BOT_TOKEN']
base_url = 'http://61.189.189.2:11434/v1/'

def analyze_news(url):
    api_url = f"https://api.pearktrue.cn/api/htmltext/?url={url}"
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        if data['code'] == 200:
            text_data = '\n'.join(data['data'])

            openai = OpenAI(api_key=OPENAI_API_KEY, base_url=base_url)
            prompt = f"""作为一名经验丰富的新闻分析师，请对以下内容进行深入分析，并按照以下格式输出：

---

### 1. 可能的误导性陈述
- 列出文本中可能存在的误导性或不准确的陈述。
- 对每条陈述进行简要说明，解释为什么它可能是误导性的。

### 2. 合理性评估
- 从逻辑和事实角度分析这些陈述的合理性。
- 提供支持您观点的事实或背景信息（如果有）。

### 3. 未来预测
- 根据文本内容，预测相关事件可能的未来发展方向。
- 预测需要基于现有信息，并提供逻辑依据。

### 4. 总结与建议
- 简要总结您的分析发现。
- 提供针对读者的实用建议（如如何辨别类似误导性信息）。

---

请确保分析内容：
1. 逻辑清晰，条理分明。
2. 使用事实和数据支持观点。
3. 避免主观臆断。
4. 避免使用Markdown格式。

如果文本中没有明显的误导性内容，请重点分析其信息的透明度和可信度。
"""

            model = "deepseek"  # 确保您有权限使用该模型
            response_openai = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "您是经验丰富的新闻分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            analysis = response_openai.choices[0].message.content
            return analysis
        else:
            return f"API调用失败：{data['msg']}"
    else:
        return f"请求失败，状态码：{response.status_code}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('欢迎使用新闻分析Bot！请发送 /analyze <新闻链接> 进行分析。')

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text('请提供一个新闻链接，例如：/analyze https://www.example.com/news')
        return

    url = context.args[0]
    await update.message.reply_text('正在分析，请稍候...')

    analysis_result = analyze_news(url)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=analysis_result)

async def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analyze", analyze))

    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())