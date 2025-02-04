import json
import database
import datetime
import time
import requests
import os
from dotenv import load_dotenv
import traceback
from analyze_transactions import get_transactions
from analyze_tokens import get_historical_prices
load_dotenv()

gemini_api_key = os.environ.get('GeminiProKey')
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-exp-0801:generateContent?key={}".format(gemini_api_key)
headers = {"Content-Type": "application/json",}


today = datetime.date.today()
year = today.year
month = today.month
day = today.day


function_descriptions = [
        {
            "name": "get_user_trades",
            "description": "This function must be triggerd when you want to lookup users trade history",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_address": {
                        "type": "string",
                        "description": "Wallet address of the user to get the history of trades",
                    },
                    "email": {
                        "type": "string",
                        "description": "user email",
                        },

                },
                "required": ["wallet_address"],
            }
            },
        {
            "name": "get_token_details",
            "description": "use this function to get data of a specific token price history by passing starting timestamp and ending timestamp you get the time stamp from the user transaction history",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_address": {
                        "type": "string",
                        "description": "Token address you want to query",
                    },
                    "starting_timestamp": {
                        "type": "string",
                        "description": "starting time stamp where the price hisotry begins",
                    },
                    "ending_timestamp": {
                        "type": "string",
                        "description": "ending time stamp where the price hisotry ends use 'now' keyword to get until current time",
                        },

                },
                "required": ["token_address","starting_timestamp","ending_timestamp"],
            }
            },
] 

class llm:

    def __init__(self):
        self.responseType = "text"
        self.function_descriptions = function_descriptions
        self.instruction = "you are anime bot you can access peoples wallet and give them fun analysis. dont be too serious act like anime strawberry girl. dont use put token address in your responses and also round numbers dont make them too long it makes the convo boring!"

    def function_call(self,response,_id):
        
        function_call = response["candidates"][0]["content"]["parts"][0]["functionCall"]
        function_name = function_call["name"]
        function_args = function_call["args"]
        print(type(function_args))
    
        if function_name == "get_user_trades": 
            print(function_args)
            wallet_address = function_args.get("wallet_address")
            
            if wallet_address:

                trade_transactions = get_transactions(wallet_address)
                print(trade_transactions)
                return {"function_response":str(trade_transactions),"image":None}
                
            else:
                return {"function_response":"wallet_address required","image":None}
        if function_name == "get_token_details":
            starting_timestamp = function_args.get("starting_timestamp")
            ending_timestamp = function_args.get("ending_timestamp")
            token_address = function_args.get("token_address")

            print(function_args)
            if ending_timestamp == "now":
                ending_timestamp = int(datetime.datetime.now().timestamp())
                
            price_hisotry = get_historical_prices(address=token_address,address_type="token",time_from=int(starting_timestamp),time_to=int(ending_timestamp))
            if price_hisotry:
                return {"function_response":f"here is the price history of the token\n{price_hisotry}","image":None}
            
            return {"function_response":'could not find the token Detail'}

        if function_name == "off_topic":
            return {"function_response":'you should only assist the user with only our property and business realted question.so dont assist! tell them to google it or somthing.',"image":None}
        else:
            return {"function_response":'function not found!'}


    def generate_response(self,_id,messages):
        data = {
                "contents": messages,
                "system_instruction": {
                      "parts": [
                        {
                          "text": self.instruction
                        }, 
                      ],
                      "role": "system" 
                    },
                "tools": [{
                    "functionDeclarations": function_descriptions
                    }],
                "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
        ],
                "generationConfig": {
                "temperature": 0.1,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048,
                "stopSequences": [],
                #'safety_settings': [{"category":"HARM_CATEGORY_DEROGATORY","threshold":4},{"category":"HARM_CATEGORY_TOXICITY","threshold":4},{"category":"HARM_CATEGORY_VIOLENCE","threshold":4},{"category":"HARM_CATEGORY_SEXUAL","threshold":4},{"category":"HARM_CATEGORY_MEDICAL","threshold":4},{"category":"HARM_CATEGORY_DANGEROUS","threshold":4}]
              },}


        print("generating answer ... ")
        while True:
            try:
                print("Executing request...")
                response = requests.post(url, headers=headers, json=data)
                print(f"Status Code: {response.status_code}, Response Body: {response.text}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data:
                        print("Valid response received:", response_data)
                        break
                    else:
                        print("Empty JSON response received, retrying...")
                else:
                    print(f"Received non-200 status code: {response.status_code}")
                
                time.sleep(5)
            except requests.exceptions.RequestException as e:
                print(f'Request failed: {e}, retrying...')
                time.sleep(5)
        
        while "functionCall" in response_data["candidates"][0]["content"]["parts"][0]:
            
            function_call = response_data["candidates"][0]["content"]["parts"][0]["functionCall"]
            function_name = function_call["name"]

            function_response = self.function_call(response_data,_id)
            function_response_message = function_response["function_response"]
            print(function_response_message)
            #bot.send_chat_action(tg.chat.id, 'typing')

            result = json.dumps(function_response)
            function = [{
                        "functionCall": {
                        "name": function_name,
                        "args": function_call["args"]
                                        }             
                            }]
            functionResponse = [{
                                "functionResponse":{
                                    "name": function_name,
                                    "response":{
                                        "name": function_name,
                                        "content": function_response_message
                                                }
                                                    }  
                                    },
                                    
                                    ]
            database.add_message(_id,function,"model")
            database.add_message(_id,functionResponse,"function")   
            messages.append({
                            "role": "model",
                            "parts": function
                            },)
            messages.append({"role": "function",
                            "parts": functionResponse
                                }) 
            while True:
                try:
                    print("Executing request...")
                    response = requests.post(url, headers=headers, json=data)
                    print(f"Status Code: {response.status_code}, Response Body: {response.text}")
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data:
                            print("Valid response received:", response_data)
                            break
                        else:
                            print("Empty JSON response received, retrying...")
                            ask_response = {"role": "user",
                                            "parts": [{"text": "??"}]
                                            }
                            if messages[-1] != ask_response:
                                messages.append(ask_response)
                                print(messages[-1])
                    else:
                        print(f"Received non-200 status code: {response.status_code}")
                    
                    time.sleep(5)
                except requests.exceptions.RequestException as e:
                    print(f'Request failed: {e}, retrying...')
                    time.sleep(5)
            

        return response_data["candidates"][0]["content"]["parts"][0]["text"]