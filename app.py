from flask import Flask, request, jsonify
import json
import telebot
import os
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(override=True)

app = Flask(__name__)
bot_token = os.environ.get("TelegramBotToken")
bot = telebot.TeleBot(bot_token)

@app.route('/')
def hello():
    return f"Hello, World!"

@app.route('/bot', methods=['POST'])
def telegram_bot():
    try:
        update = telebot.types.Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
        return "!", 200
    except Exception as e:
        print(f"Error processing Telegram update: {e}")
        return "Error", 500

@bot.message_handler(func=lambda message: True)
def chat(message):
    bot.reply_to(message,"hi")
if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)






