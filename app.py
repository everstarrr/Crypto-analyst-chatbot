from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
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
CORS(app)

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
       

@app.route('/api/chat/send_message', methods=['POST'])
def api_send_message():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        message_text = data.get('message')
        
        if not user_id or not message_text:
            return jsonify({"status": "error", "message": "Missing user_id or message"}), 400
        
        # Database operations
        database.register(user_id)
        prompt = [{"text": message_text}]
        conversation = database.add_message(user_id, prompt, "user")
        
        # Generate AI response
        llm = ai.llm()
        ai_response = llm.generate_response(user_id, conversation)
        response_data = [{"text": ai_response}]
        database.add_message(user_id, response_data, "model")
        
        return jsonify({
            "status": "success",
            "response": ai_response,
            "conversation_id": user_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chat/reset', methods=['POST'])
def api_reset():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"status": "error", "message": "Missing user_id"}), 400
            
        database.reset_conversation(user_id)
        return jsonify({
            "status": "success",
            "message": "Conversation reset successfully",
            "user_id": user_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chat/history', methods=['POST'])
def api_history():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"status": "error", "message": "Missing user_id"}), 400
            
        conversation = database.get_conversation(user_id)
        
        # Process conversation history
        processed_history = [
            {
                "role": msg["role"],
                "message": part["text"]
            }
            for msg in reversed(conversation)
            for part in msg["parts"]
            if msg["role"] in ["user", "model"]
            and "text" in part
            and not part.get("functionCall")
            and not part.get("functionResponse")
        ]

        return jsonify({
            "status": "success",
            "user_id": user_id,
            "history": processed_history
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)






