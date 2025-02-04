from pymongo import MongoClient
import os
from dotenv import load_dotenv


load_dotenv()

MONGO_URL = os.getenv('MONGO_URL')
client = MongoClient(MONGO_URL)
db = client['chat']
Users = db['users']  

instruction = "you are solana crypto trading assistant"

def reset_conversation(_id):
    Users.update_one({"_id":int(_id)},{"$set":{"conversation":[]}})

def register(_id): 
    existance = Users.find_one({"_id":int(_id)})
    if existance == None:
        Users.insert_one({"_id":_id,"conversation":[]})
    
def add_message(_id,message,role):
    conversation = Users.find_one({"_id":_id}).get("conversation")
    conversation.append({"role":role,"parts":message})
    Users.update_one({"_id":int(_id)},{"$set":{"conversation":conversation}})
    return conversation
  

def set_user_info(_id,info):
    Users.update_one({"_id":int(_id)},{"$set":info})

    