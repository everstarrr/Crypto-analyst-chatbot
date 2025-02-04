from flask import Flask, request, jsonify
import json
import telebot
import os
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
import database
import ai
import re
import markdown

load_dotenv(override=True)

app = Flask(__name__)
bot_token = os.environ.get("TelegramBotToken")
bot = telebot.TeleBot(bot_token)

MONGO_URL = os.getenv('MONGO_URL')
client = MongoClient(MONGO_URL)
db = client['Chat']  
client = MongoClient(MONGO_URL)
conversations = db["conversations"]

def remove_unsupported_tags(html_string):

  supported_tags = ["b", "strong", "i", "em", "a", "code", "pre"]
  
  pattern = r"<[^>]+>" 
  
  def replace_tag(match):
    tag = match.group(0)
    
    if any(tag.startswith(f"<{supported_tag}") or tag.startswith(f"</{supported_tag}") for supported_tag in supported_tags):
      return tag  
    else:
      return ""  
  
  clean_string = re.sub(pattern, replace_tag, html_string)
  return clean_string

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
    try:
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
        print(f"final response: {response}")
        response = [
                    {"text": response},  
                ] 
        database.add_message(user_id,response,"model")
        response_message = response[0].get("text")


        escaped_response = markdown.markdown(response_message)
        escaped_response = remove_unsupported_tags(escaped_response)
        bot.send_message(user_id,escaped_response,parse_mode='HTML')
    except Exception as e:
        print(f"error: {e}")
       

    
if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)






