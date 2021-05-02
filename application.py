from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    FlexSendMessage
)

app = Flask(__name__)

LINE_SECRET = "dc07d5e38aa2320a0436144e05ca9670"
LINE_TOKEN = "WqIoSCQwZyooqAmS5ZgD7uGENWOdYeRnLe5RKR2518FDFFFuCktomtOiHSD5e5gCkdEtyYZiURI82dRQJMUPpoDa/5aIWynJ0k78J5y5UjhzG8CFnP08eZVZ3wGTOsuaf7KqXsqPKrArMTS0WMZxNAdB04t89/1O/w1cDnyilFU="
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
    url_dict = {
      "TIBAME":"https://www.tibame.com/coursegoodjob/traffic_cli", 
      "HELP":"https://developers.line.biz/zh-hant/docs/messaging-api/"}
# 將要發出去的文字變成TextSendMessage
    try:
        url = url_dict[event.message.text.upper()]
        message = TextSendMessage(text=url)
    except:
        message = TextSendMessage(text=event.message.text)
# 回覆訊息
    LINE_BOT.reply_message(event.reply_token, message)

