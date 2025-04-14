import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import configparser
import json


def push_gmail(input_json, CONFIG):
    """
    Gmail API を使用してメールの下書きを作成する関数
    inout_json: {"sender1": "送信者", "recipient": "受信者", "title": "件名", "message_text": "本文"}
    CONFIG: configparser.ConfigParser() のインスタンス
    """
    
    input_json["gmail"]["sender"] = config[CONFIG]["SENDER"] 
    input_json["gmail"]["recipient"] = input_json["メール"]
    
    # Gmail API を使用してメールの下書きを作成するための関数を呼び出す
    # input_json, token, flag = generate_gmail_content_for_GPT(input_json, CONFIG)
    input_json, token = generate_gmail_content_for_gemini(input_json, CONFIG)
    
    if token == 0:
        return input_json, 0
    
    # 認証情報の読み込み。必要なスコープは「gmail.compose」
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.compose'])
    service = build('gmail', 'v1', credentials=creds)

    # メッセージ作成
    message = create_message(input_json["gmail"]["sender"],
                             input_json["gmail"]["recipient"],
                             input_json["gmail"]["title"],
                             input_json["gmail"]["message_text"])
    
    # 下書きの作成（ユーザID は "me" で自分自身）
    draft = create_draft(service, 'me', message)
    input_json["gmail"]["id"] = draft["id"]
    
    return input_json, token