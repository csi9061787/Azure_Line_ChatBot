from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.face import FaceClient
import os
import json
from imgur_python import Imgur
import re
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime, timezone, timedelta
from azure.cognitiveservices.vision.computervision \
import ComputerVisionClient
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    FlexSendMessage,
    ImageMessage
)

app = Flask(__name__)

LINE_SECRET = os.getenv('secret')
LINE_TOKEN = os.getenv('token')
LINE_BOT = LineBotApi(LINE_TOKEN)
HANDLER = WebhookHandler(LINE_SECRET)

IMGUR_CONFIG = {
        "client_id" : os.getenv("imgur_client_id"),
        "client_secret" : os.getenv("imgur_client_secret"),
        "access_token" : os.getenv("imgur_access_token"),
        "refresh_token" : os.getenv("imgur_refresh_token")
}
IMGUR_CLIENT = Imgur(config=IMGUR_CONFIG)

def azure_object_detection(url, filename):
    SUBSCRIPTION_KEY = os.getenv("detection_key")
    ENDPOINT = os.getenv("detection_endpoint")
    CV_CLIENT = ComputerVisionClient(
        ENDPOINT, CognitiveServicesCredentials(SUBSCRIPTION_KEY)
    )
    
    img = Image.open(filename)
    draw = ImageDraw.Draw(img)
    font_size = int(5e-2 * img.size[1])
    fnt = ImageFont.truetype(
      "TaipeiSansTCBeta-Regular.ttf", size=font_size)
    object_detection = CV_CLIENT.detect_objects(url)
    if len(object_detection.objects) > 0:
        for obj in object_detection.objects:
            left = obj.rectangle.x
            top = obj.rectangle.y
            right = obj.rectangle.x + obj.rectangle.w
            bot = obj.rectangle.y + obj.rectangle.h
            name = obj.object_property
            confidence = obj.confidence
            print("{} at location {}, {}, {}, {}".format(
              name, left, right, top, bot))
            draw.rectangle(
              [left, top, right, bot],
              outline=(255, 0, 0), width=5)
            draw.text(
                [left, top + font_size],
                "{0} {1:0.1f}".format(name, confidence * 100),
                fill=(255, 0, 0),
                font=fnt,
            )
    img.save(filename)
    image = IMGUR_CLIENT.image_upload(filename, "title", "description")
    link = image["response"]["data"]["link"]
    
    os.remove(filename)
    return link
        
        
def azure_face_recongition(filename):
    KEY = os.getenv("face_key")
    ENDPOINT = os.getenv("face_endpoint")
    FACE_CLIENT = FaceClient(
      ENDPOINT, CognitiveServicesCredentials(KEY))
    
    PERSON_GROUP_ID = "ceb102"
    img = open(filename, 'r+b')
    detected_face = FACE_CLIENT.face.detect_with_stream(
        img, detection_model="detection_01")
    
    if len(detected_face) != 1:
        return ""
    results = FACE_CLIENT.face.identify(
            [detected_face[0].face_id], PERSON_GROUP_ID)
    if len(results) == 0:
        return "unknown"
    result = results[0].as_dict()
    if len(result["candidates"]) == 0:
        return "unknown"
    if result["candidates"][0]["confidence"] < 0.5:
        return "unknown"
    person = FACE_CLIENT.person_group_person.get(
            PERSON_GROUP_ID, result["candidates"][0]["person_id"]
            )
    return person.name
        
def azure_describe(url):
    SUBSCRIPTION_KEY = os.getenv("detection_key")
    ENDPOINT = os.getenv("detection_endpoint")
    CV_CLIENT = ComputerVisionClient(
        ENDPOINT, CognitiveServicesCredentials(SUBSCRIPTION_KEY)
    )
    
    description_results = CV_CLIENT.describe_image(url)
    output = ""
    for caption in description_results.captions:
        output += "'{}' with confidence {:.2f}% \n".format(
            caption.text, caption.confidence * 100
        )
    return(output)
    
def azure_ocr(url):
    SUBSCRIPTION_KEY = os.getenv("detection_key")
    ENDPOINT = os.getenv("detection_endpoint")
    CV_CLIENT = ComputerVisionClient(
        ENDPOINT, CognitiveServicesCredentials(SUBSCRIPTION_KEY)
    )
    
    ocr_results = CV_CLIENT.read(url, raw=True)
    operation_location_remote = \
    ocr_results.headers["Operation-Location"]
    operation_id = operation_location_remote.split("/")[-1]
    status = ["notStarted", "running"]
    while True:
        get_handw_text_results = \
        CV_CLIENT.get_read_result(operation_id)
        if get_handw_text_results.status not in status:
            break
        time.sleep(1)
    text = []
    succeeded = OperationStatusCodes.succeeded
    if get_handw_text_results.status == succeeded:
        res = get_handw_text_results.analyze_result.read_results
        for text_result in res:
            for line in text_result.lines:
                if len(line.text) <= 8:
                    text.append(line.text)
                    
    r = re.compile("[0-9A-Z]{2,4}[.-]{1}[0-9A-Z]{2,4}")
    text = list(filter(r.match, text))
    return text[0].replace('.','-') if len(text) > 0 else ""

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
        LINE_BOT.reply_message(event.reply_token, message)
    except:
        message = TextSendMessage(text=event.message.text)
        LINE_BOT.reply_message(event.reply_token, message)

@HANDLER.add(MessageEvent, message=ImageMessage)
def handle_content_message(event):
    
    print(event.message)
    print(event.source.user_id)
    print(event.message.id)
    
    filename = "{}.jpg".format(event.message.id)
    message_content = LINE_BOT.get_message_content(event.message.id)
    with open(filename, "wb") as f_w:
        for chunk in message_content.iter_content():
            f_w.write(chunk)
    f_w.close()
    
    image = IMGUR_CLIENT.image_upload(filename, "title", "description")
    link = image["response"]["data"]["link"]
    name = azure_face_recongition(filename)
    
    if name != "":
        now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
        output_name = name
        output_content = now
    else:
        plate = azure_ocr(link)
        link_ob = azure_object_detection(link, filename)
        
        if len(plate) > 0:
            output_name = "License Plate"
            output_content = plate
        else:
            output_name = "Result"
            output_content = azure_describe(link)
            
        link = link_ob
    with open("flex_message.json", "r") as f_r:
        bubble = json.load(f_r)
    f_r.close()
# 依情況更動 components
    bubble["body"]["contents"][0]["contents"][0]["url"]=link
    bubble["body"]["contents"][1]["contents"][0]["contents"][0]["contents"][0]\
    ["text"]=output_name
    bubble["body"]["contents"][1]["contents"][0]["contents"][0]["contents"][2]\
    ["text"]=output_content
    LINE_BOT.reply_message(
        event.reply_token, 
        [
            FlexSendMessage(alt_text="Report", contents=bubble)
            ]
    )

if __name__=="__main__":
    app.run()
