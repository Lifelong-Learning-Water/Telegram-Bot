import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = '欢迎来到Delta Water的机器人世界。\n\n请选择你想要访问的机器人：'
    
    # 创建按钮
    keyboard = [
        [InlineKeyboardButton("LLM AI", url="https://t.me/delta_water_llm_ai_bot")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = '这是帮助信息。你可以使用 /start 命令来获取机器人列表。'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

TOKEN = os.environ['BOT_TOKEN']
application = ApplicationBuilder().token(TOKEN).build()

# 添加命令处理器
application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('help', help_command))

# 启动轮询
application.run_polling()