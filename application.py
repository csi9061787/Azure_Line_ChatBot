from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
import os
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    FlexSendMessage
)

app = Flask(__name__)

LINE_SECRET = os.getenv('secret')
LINE_TOKEN = os.getenv('token')
LINE_BOT = LineBotApi(LINE_TOKEN)
HANDLER = WebhookHandler(LINE_SECRET)


@app.route("/callback", methods=["POST"])
def callback():
    # X-Line-Signature: 數位簽章
    signature = request.headers["X-Line-Signature"]
    print(signature)
    body = request.get_data(as_text=True)
    print(body)
    try:
        HANDLER.handle(body, signature)
    except InvalidSignatureError:
        print("Check the channel secret/access token.")
        abort(400)
    return "OK"
    
# message 可以針對收到的訊息種類
@HANDLER.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message == '介紹':
        with open("Introduction.json", "r") as f_r:
            bubble = json.load(f_r)
        f_r.close()
        message = FlexSendMessage(alt_text="Report", contents=bubble)
    else:
        message = TextSendMessage(text=event.message.text)
        
    LINE_BOT.reply_message(event.reply_token, message)
