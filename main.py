from flask import Flask, request, jsonify
from pydub import AudioSegment
import openai
import os
import requests
import tiktoken
from db import MessageDB

replit_url = 'https://fixithelper.onrender.com'

openai.api_key = os.environ['OPENAI_KEY']
bot_token = os.environ['BOT_TOKEN']

app = Flask(__name__)

@app.route('/')
def index():
    return 'مرحباً من بوت FixItHelper!'

@app.route('/setup')
def setup():
    webhook_url = f'{replit_url}/webhook'
    response = requests.post(
        f'https://api.telegram.org/bot{bot_token}/setWebhook?url={webhook_url}'
    )
    return jsonify(response.json())

@app.route('/webhook', methods=['POST'])
def webhook():
    db = MessageDB("data.db")
    request_data = request.get_json()
    text = ""

    if 'voice' in request_data['message']:
        file_id = request_data["message"]["voice"]["file_id"]
        file_info = requests.get(f'https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}').json()
        file_path = file_info['result']['file_path']
        file_url = f'https://api.telegram.org/file/bot{bot_token}/{file_path}'
        voice_data = requests.get(file_url).content

        with open("audio.ogg", "wb") as f:
            f.write(voice_data)

        audio = AudioSegment.from_ogg("audio.ogg")
        audio.export("audio.mp3", format="mp3")

        with open("audio.mp3", "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
            text = transcript['text']

    elif 'text' in request_data['message']:
        text = request_data['message']['text']

    user_id = request_data["message"]["chat"]["id"]

    if text == "/start":
        return sendMessage(user_id, "مرحباً! اسألني أي شيء ✨")

    db.insert_message(user_id, "user", text)
    messages = db.get_messages_by_user(user_id)
    messages.reverse()
    messages.insert(0, {"role": "system", "content": "أنت مساعد ذكي تجيب دائماً بالعربية"})

    completion_length = 500
    total_tokens = num_tokens_from_messages(messages)
    while total_tokens >= (4096 - completion_length):
        messages.pop(1)
        total_tokens = num_tokens_from_messages(messages)

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=completion_length
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        return sendMessage(user_id, f"حدث خطأ: {e}")

    db.insert_message(user_id, "assistant", reply)
    return sendMessage(user_id, reply)

def sendMessage(user_id, text):
    return requests.post(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        data={'chat_id': user_id, 'text': text}
    )

def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0
    for message in messages:
        num_tokens += 4
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens -= 1
    num_tokens += 2
    return num_tokens

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
