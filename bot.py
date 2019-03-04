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

@app.route("/test/dialogflow", methods=['GET'])
def test_dialogflow():
    if 'keyword' in request.args:
        keyword = request.args['keyword']
        return detect_intent_texts('daimoku-keeper', 'hello', keyword, 'TH')

@app.route("/test/explicit", methods=['GET'])
def test_explicit():
    return explicit()

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
    if GCS_KEYFILE_PATH != '':
        storage_client = storage.Client.from_service_account_json(GCS_KEYFILE_PATH)
    else:
        storage_client = storage.Client.from_service_account_json(GCS_KEYFILE)

    # Make an authenticated API request
    buckets = list(storage_client.list_buckets())
    print(buckets)
    return buckets

def detect_intent_texts(project_id, session_id, texts, language_code):
    """Returns the result of detect intent with texts as inputs.
    Using the same `session_id` between requests allows continuation
    of the conversation."""

    import dialogflow_v2 as dialogflow
    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    print('Session path: {}\n'.format(session))

    for text in texts:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)

        query_input = dialogflow.types.QueryInput(text=text_input)

        response = session_client.detect_intent(
            session=session, query_input=query_input)

        print('=' * 20)
        print('Query text: {}'.format(response.query_result.query_text))
        print('Detected intent: {} (confidence: {})\n'.format(
            response.query_result.intent.display_name,
            response.query_result.intent_detection_confidence))
        return('Fulfillment text: {}\n'.format(
            response.query_result.fulfillment_text))

if __name__ == "__main__":
    app.run()