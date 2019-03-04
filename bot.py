import os
import json
import uuid
from flask import Flask, request, abort, Response, jsonify
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
from google.protobuf.json_format import MessageToDict, MessageToJson

LINE_CHANNEL_SECRET = os.environ['LINE_CHANNEL_SECRET']
LINE_CHANNEL_ID = os.environ['LINE_CHANNEL_ID']
LINE_CHANNEL_ACCESS_TOKEN = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
GCS_KEYFILE = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
GCS_KEYFILE_PATH = ''
DIALOGFLOW_PROJECT_ID = 'daimoku-keeper'
DIALOGFLOW_SESSION_ID = uuid.uuid4().hex

if not os.path.exists(GCS_KEYFILE):
    # Create file path for GCS by parsing the string to json file
    print('here')
    GCS_KEYFILE_PATH = os.path.join(os.getcwd(), 'gcs_keyfile.json')
    with open(GCS_KEYFILE_PATH, 'w') as gcs_keyfile_file:
        json.dump(json.loads(GCS_KEYFILE), gcs_keyfile_file, indent=4)
        gcs_keyfile_file.close()
else:
    GCS_KEYFILE_PATH = GCS_KEYFILE

app = Flask(__name__)
app.config['DEBUG'] = True

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/", methods=['GET', 'POST'])
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
        detected_intents = detect_intent_texts(DIALOGFLOW_PROJECT_ID, DIALOGFLOW_SESSION_ID, keyword, 'TH')
        response = {}
        for detected_intent in detected_intents:
            response['intentName'] = detected_intent.query_result.intent.display_name
            response['parameters'] = MessageToDict(detected_intent.query_result.parameters)
        
        return jsonify(response)

@app.route("/test/explicit", methods=['GET'])
def test_explicit():
    return explicit()

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    detected_intents = detect_intent_texts(DIALOGFLOW_PROJECT_ID, DIALOGFLOW_SESSION_ID, text, 'TH')

    source_userId = event.source.user_id

    for detected_intent in detected_intents:
        intentName = detected_intent.query_result.intent.display_name
        if intentName == 'RequestToKeepDaimokuIntent':
            parameters = MessageToDict(detected_intent.query_result.parameters)
            daimoku_count = None
            if parameters['DaimokuCountEntryEntity'] != '' and parameters['DaimokuCountEntryEntity1'] != '':
                daimoku_count = int(parameters['DaimokuCountEntryEntity']['number'] + parameters['DaimokuCountEntryEntity1']['number'])
            elif parameters['DaimokuCountEntryEntity'] != '':
                daimoku_count = int(parameters['DaimokuCountEntryEntity']['number'])
            elif parameters['DaimokuCountEntryEntity1'] != '':
                daimoku_count = int(parameters['DaimokuCountEntryEntity']['number'])
            text = 'รับทราบครับ {} สวดได้ {} ช่อง'.format(source_userId, daimoku_count)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=text)
            )
        elif intentName == 'Default Fallback Intent':
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
    session_client = dialogflow.SessionsClient.from_service_account_json(GCS_KEYFILE_PATH)

    session = session_client.session_path(project_id, session_id)
    print('Session path: {}\n'.format(session))

    if type(texts) is str   :
        texts = [texts]
    
    detected_intents = []
    for text in texts:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)

        query_input = dialogflow.types.QueryInput(text=text_input)

        response = session_client.detect_intent(
            session=session, query_input=query_input)
        
        detected_intents.append(response)

    return detected_intents

def keep_daimoku(query_result):
    
    pass

if __name__ == "__main__":
    app.run()