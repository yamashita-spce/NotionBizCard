

# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload


# # Googleドライブの認証情報と公開フォルダのID（事前に「リンクを知っている全員が閲覧可能」に設定済み）
# CREDENTIALS_FILE = "path/to/service_account_credentials.json"
# PUBLIC_FOLDER_ID = "1FzKB8uXJWVfMR1kioel5GYQ-3Sl_Q83p"

# def upload_file_to_drive(file_path, folder_id=PUBLIC_FOLDER_ID):
#     """
#     指定した画像ファイルをGoogleドライブの公開フォルダにアップロードし、
#     公開URL（webViewLink）を返す関数です。
#     """
#     SCOPES = ['https://www.googleapis.com/auth/drive']
#     creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
#     service = build('drive', 'v3', credentials=creds)
    
#     file_metadata = {
#         'name': os.path.basename(file_path),
#         'parents': [folder_id]
#     }
#     media = MediaFileUpload(file_path, mimetype='image/jpeg')
#     file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
#     file_id = file.get('id')
    
#     # 公開URL (webViewLink) を取得
#     file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
#     public_url = file_info.get('webViewLink')
#     return public_url


#  def ocr_image(image_path)
#     """
#     画像ファイルをBase64エンコードし、GPT-4oの画像入力対応APIを呼び出して
#     画像内のテキストを抽出する関数です。
#     ※ このコードは、GPT-4oの画像入力機能が利用可能な環境でのみ動作します。
#     """
#      # Googleドライブに画像をアップロードして公開URLを取得
#     public_url = upload_file_to_drive(image_path)
#     print("Public URL:", public_url)

#     # Markdown形式で画像を埋め込んだメッセージを作成
#     user_message = (
#         f"以下の画像からテキストを抽出してください。\n![image]({public_url})"
#     )
    
#     data = {
#         "model": "gpt-4o",  # 画像入力に対応したモデル（例）
#         "messages": [
#             {
#                 "role": "system",
#                 "content": (
#                     "あなたはOCRエンジンです。提供された名刺の画像から全てのテキストを抽出し、"
#                     "抽出したテキストのみを返してください。結果はJSON形式で出力してください。"
#                 )
#             },
#             {
#                 "role": "user",
#                 "content": user_message
#             }
#         ],
#         "response_format": {"type": "json_object"},
#         "temperature": 0.0
#     }
#     response = requests.post(url, headers=headers, json=data)
#     if response.status_code == 200:
#         res_json = response.json()
#         content = res_json["choices"][0]["message"]["content"]
#         print("=== DEBUG: OCR result ===")
#         print(content)
#         print("=== end of debug ===")
#         try:
#             # 返されたJSON文字列をパースして 'text' キーの内容を取得
#             result = json.loads(content)
#             extracted_text = result.get("text", "")
#             return extracted_text
#         except Exception as e:
#             print("JSONパースエラー:", e)
#             return content
#     else:
#         print("Error:", response.text)
#         return None