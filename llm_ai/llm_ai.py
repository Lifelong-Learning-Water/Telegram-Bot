import os
import json
from cryptography.fernet import Fernet
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import uuid
import asyncio
from git import Repo
from collections import defaultdict
from threading import Lock
import requests

development = False
duration = 120

class UserDataManager:
    def __init__(self, file_path, key):
        self.file_path = file_path
        self.cipher = Fernet(key)
        self.user_data = defaultdict(lambda: {
            'openai_token': None,
            'base_url': None,
            'model': None,
            'conversations': {},
            'current_conversation': None
        })
        self.lock = Lock()
        self.load_user_data()

    def load_user_data(self):
        with self.lock:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'rb') as f:
                    if development:
                        # 在开发模式下直接读取未加密的数据
                        decrypted_data = f.read()
                    else:
                        # 在生产模式下读取加密的数据
                        encrypted_data = f.read()
                        decrypted_data = self.cipher.decrypt(encrypted_data)
                    
                    # 将加载的数据转换为 defaultdict
                    loaded_data = json.loads(decrypted_data)
                    self.user_data = defaultdict(lambda: {
                        'openai_token': None,
                        'base_url': None,
                        'model': None,
                        'conversations': {},
                        'current_conversation': None
                    }, loaded_data)

    def save_user_data(self):
        with self.lock:
            if development:
                # 在开发模式下直接写入未加密的数据
                with open(self.file_path, 'w') as f:
                    json.dump(self.user_data, f)
            else:
                # 在生产模式下写入加密的数据
                encrypted_data = self.cipher.encrypt(json.dumps(self.user_data).encode())
                with open(self.file_path, 'wb') as f:
                    f.write(encrypted_data)
            self.commit_changes()

    def commit_changes(self):
        repo = Repo(os.getcwd())
        repo.index.add([self.file_path])
        repo.index.commit("Update user_data.json")
        origin = repo.remote(name='origin')
        origin.push()

user_data_manager = UserDataManager('llm_ai/user_data.enc', os.environ['CRYPTOGRAPHY_KEY'])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.application.should_stop:
        return
    text = "Welcome to LLM AI!\nThis bot is open source!\n\nhttps://github.com/Alpha-Water/Telegram-Bot"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    await help_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.application.should_stop:
        return
    text = (
        "Here are the available commands for the bot:\n"
        "/start - Start the bot.\n\n"
        "/help - View help information.\n\n"
        "/set <token> <url> <model> - Set OpenAI Token, API URL, and model.\n\n"
        "/new_conversation <code name> - Create a new conversation.\n\n"
        "/switch <conversation_id> - Switch to a different conversation.\n\n"
        "/list_conversations - View all conversations.\n\n"
        "/delete_current_conversation - Delete the current conversation."
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

async def set_parameters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.application.should_stop:
        return
    user_id = update.effective_chat.id
    if len(context.args) < 3:
        await context.bot.send_message(chat_id=user_id, text="Please provide Token, Interface Address and Model Name.\nFormat: /set <token> <url> <model>")
        return

    user_settings = user_data_manager.user_data[str(user_id)]
    user_settings['openai_token'] = context.args[0]
    user_settings['base_url'] = context.args[1]
    user_settings['model'] = context.args[2]
    user_data_manager.save_user_data()  # 保存用户数据
    await context.bot.send_message(chat_id=user_id, text="The parameter has been set.\nPlease use /new_conversation <code name> to create a new conversation.")

async def new_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.application.should_stop:
        return
    user_id = update.effective_chat.id
    user_settings = user_data_manager.user_data[str(user_id)]

    if len(context.args) == 0:
        await context.bot.send_message(chat_id=user_id, text="Please provide a conversation code name.\nFormat: /new_conversation <code name>")
        return

    conversation_name = ' '.join(context.args)

    # 检查名称是否包含空格或制表符
    if any(char.isspace() for char in conversation_name):
        await context.bot.send_message(chat_id=user_id, text="The conversation code name cannot contain spaces or tabs. Please try again.")
        return

    conversation_id = str(uuid.uuid4())  # 使用 UUID 生成唯一的对话 ID
    user_settings['conversations'][conversation_id] = {
        'name': conversation_name,
        'history': []
    }
    user_settings['current_conversation'] = conversation_id
    user_data_manager.save_user_data()  # 保存用户数据
    await context.bot.send_message(chat_id=user_id, text=f"New conversation created.\nID: {conversation_id}\nName: {conversation_name}")

async def list_conversations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.application.should_stop:
        return
    user_id = update.effective_chat.id
    conversations = user_data_manager.user_data[str(user_id)]['conversations']
    if not conversations:
        await context.bot.send_message(chat_id=user_id, text="You don't have any conversations yet.")
        return

    conversation_list = "\n".join([f"ID: {cid[:5]}..., code name: {conv['name']}" for cid, conv in conversations.items()])
    await context.bot.send_message(chat_id=user_id, text=f"Your Conversation List:\n{conversation_list}")

async def switch_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.application.should_stop:
        return
    user_id = update.effective_chat.id
    if len(context.args) == 0:
        await context.bot.send_message(chat_id=user_id, text="Please provide a conversation code name or ID to switch.")
        return

    conversation_identifier = context.args[0]
    user_settings = user_data_manager.user_data[str(user_id)]
    conversations = user_settings['conversations']

    # 尝试通过 ID 切换
    if conversation_identifier in conversations:
        user_settings['current_conversation'] = conversation_identifier
        user_data_manager.save_user_data()  # 保存用户数据
        await context.bot.send_message(chat_id=user_id, text=f"Switched to Conversation ID: {conversation_identifier[:5]}..., code name: {conversations[conversation_identifier]['name']}.")
        return

    # 尝试通过名称切换
    for cid, conv in conversations.items():
        if conv['name'] == conversation_identifier:
            user_settings['current_conversation'] = cid
            user_data_manager.save_user_data()  # 保存用户数据
            await context.bot.send_message(chat_id=user_id, text=f"Switched to Conversation ID: {cid[:5]}..., code name: {conv['name']}.")
            return

    await context.bot.send_message(chat_id=user_id, text="Invalid conversation ID or code name.")

async def delete_current_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.application.should_stop:
        return
    user_id = update.effective_chat.id
    user_settings = user_data_manager.user_data[str(user_id)]
    current_conversation_id = user_settings.get('current_conversation')

    if current_conversation_id in user_settings['conversations']:
        del user_settings['conversations'][current_conversation_id]  # 删除当前对话
        user_settings['current_conversation'] = None  # 清空当前对话 ID
        user_data_manager.save_user_data()  # 保存用户数据
        await context.bot.send_message(chat_id=user_id, text="The current conversation has been deleted.")
    else:
        await context.bot.send_message(chat_id=user_id, text="Current conversation not found.")

async def get_model_response(update, context, user_settings, user_id, user_message):
    if context.application.should_stop:
        return
    user_settings['is_processing'] = True
    loading_message = await context.bot.send_message(chat_id=user_id, text="Responding, please wait...\nThe information sent in the response is not valid.")

    api_key = user_settings['openai_token']
    base_url = user_settings['base_url']
    model = user_settings.get('model', 'gpt-3.5-turbo')
    client = OpenAI(api_key=api_key, base_url=base_url)

    current_conversation_id = user_settings['current_conversation']
    conversation_history = user_settings['conversations'][current_conversation_id]['history']
    conversation_history.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=model,
        messages=conversation_history
    )

    bot_reply = response.choices[0].message.content
    await context.bot.send_message(chat_id=user_id, text=bot_reply, parse_mode='Markdown', reply_to_message_id=update.message.message_id)

    user_settings['conversations'][current_conversation_id]['history'].append({"role": "assistant", "content": bot_reply})

    user_settings['is_processing'] = False
    await context.bot.delete_message(chat_id=user_id, message_id=loading_message.message_id)
    user_data_manager.save_user_data()  # 保存用户数据

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.application.should_stop:
        return
    user_message = update.message.text
    user_id = update.effective_chat.id
    user_settings = user_data_manager.user_data[str(user_id)]

    if not user_settings['openai_token']:
        await context.bot.send_message(chat_id=user_id, text="Please use the /set command to set the necessary parameters first.")
        return
    elif not user_settings['current_conversation']:
        await context.bot.send_message(chat_id=user_id, text="Please create a new conversation using /new_conversation <code name> first.")
        return
    if user_settings.get('is_processing', False):
        await context.bot.send_message(chat_id=user_id, text="The information sent in the response is invalid.", reply_to_message_id=update.message.message_id)
        return
    try:
        asyncio.create_task(get_model_response(update, context, user_settings, user_id, user_message))
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"An error occurred: {str(e)}")

async def shutdown(application):
    await asyncio.sleep(duration)
    # 触发 GitHub Actions 工作流
    repo_name = "Telegram-Bot"
    workflow_id = "llm_ai.yml"
    github_token = os.environ['GITHUB_TOKEN']
    url = f"https://api.github.com/repos/Alpha-Water/{repo_name}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "ref": "main"  # 触发的分支
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print("GitHub Actions workflow triggered successfully.")
    else:
        print(f"Failed to trigger workflow: {response.status_code} {response.text}")

    # 设置一个标志位，指示程序应该停止接收新消息
    application.should_stop = True

    # 等待所有任务完成
    await application.shutdown()

    print("Shutting down the bot...")

def main():
    TOKEN = os.environ['BOT_TOKEN']
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('set', set_parameters))
    application.add_handler(CommandHandler('new_conversation', new_conversation))
    application.add_handler(CommandHandler('switch', switch_conversation))
    application.add_handler(CommandHandler('list_conversations', list_conversations))
    application.add_handler(CommandHandler('delete_current_conversation', delete_current_conversation))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    asyncio.run(shutdown(application))
    application.run_polling()

if __name__ == '__main__':
    main()