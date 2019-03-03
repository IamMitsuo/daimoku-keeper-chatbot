import os
import json
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, URITemplateAction, PostbackTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent
)

LINE_CHANNEL_SECRET = os.environ['LINE_CHANNEL_SECRET']
LINE_CHANNEL_ID = os.environ['LINE_CHANNEL_ID']
LINE_CHANNEL_ACCESS_TOKEN = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
GCS_KEYFILE = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
GCS_KEYFILE_PATH = ''

if not os.path.exists(GCS_KEYFILE):
    # Create file path for GCS by parsing the string to json file
    print('here')
    GCS_KEYFILE_PATH = os.path.join(os.getcwd(), 'gcs_keyfile.json')
    with open(GCS_KEYFILE_PATH, 'w') as gcs_keyfile_file:
        json.dump(json.loads(GCS_KEYFILE), gcs_keyfile_file, indent=4)
        gcs_keyfile_file.close()


app = Flask(__name__)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    # Get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # Get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # Handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=text)
    )

def explicit():
    from google.cloud import storage

    # Explicitly use service account credentials by specifying the private key
    # file.
    storage_client = storage.Client.from_service_account_json(
        GCS_KEYFILE_PATH)

    # Make an authenticated API request
    buckets = list(storage_client.list_buckets())
    print(buckets)

if __name__ == "__main__":
    app.run()