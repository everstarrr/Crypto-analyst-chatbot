from flask import Flask, request, jsonify
import json
import telebot
import os
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
import database
import ai

load_dotenv(override=True)

app = Flask(__name__)
bot_token = os.environ.get("TelegramBotToken")
bot = telebot.TeleBot(bot_token)

MONGO_URL = os.getenv('MONGO_URL')
client = MongoClient(MONGO_URL)
db = client['Chat']  
client = MongoClient(MONGO_URL)
conversations = db["conversations"]
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
def chat(user):
    user_id = user.chat.id
    if user.text == "/reset":
        database.reset_conversation(user_id)
        return
    prompt = [
                {"text": user.text},  
            ]    
    database.register(user_id)
    conversation = database.add_message(user_id,prompt,"user")
    llm = ai.llm()
    
    response = llm.generate_response(user_id,conversation)
    response = [
                {"text": response},  
            ] 
    database.add_message(user_id,response,"model")
    response_message = response[0].get("text")
    bot.send_message(user_id,response_message)

    
if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)






