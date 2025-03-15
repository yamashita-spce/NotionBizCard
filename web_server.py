# web_server.py
from flask import Flask, request, render_template_string, send_from_directory
import os
from card import main as process_cards
import subprocess
import socket


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>名刺処理アップローダー</title>
</head>
<body>
    <h1>名刺画像アップロード</h1>
    <form method="post" enctype="multipart/form-data" id="upload-form">
        <label>名刺画像:</label>
        <input type="file" name="business_card">
        <br><br>
        <label>ヒアリングシード画像:</label>
        <input type="file" name="hearing_seed" multiple>
        <br><br>
        <label>リード獲得日 (M/D形式, 例: 3/12):</label>
        <input type="text" name="date" id="date-input">
        <br><br>
        <label>ChatGPT API Key:</label>
        <input type="text" name="chatgpt_key" id="chatgpt-key-input">
        <br><br>
        <label>Notion API Key:</label>
        <input type="text" name="notion_key" id="notion-key-input">
        <br><br>
        <label>Notion Database ID:</label>
        <input type="text" name="notion_db_id" id="notion-db-id-input">
        <br><br>
        <input type="submit" value="アップロードして処理開始">
    </form>
    {% if message %}
    <p>{{ message }}</p>
    {% endif %}

    <script>
      // ページ読み込み時に localStorage から値を読み込む
      window.addEventListener("DOMContentLoaded", function() {
        const dateInput = document.getElementById("date-input");
        const chatgptKeyInput = document.getElementById("chatgpt-key-input");
        const notionKeyInput = document.getElementById("notion-key-input");
        const notionDbIdInput = document.getElementById("notion-db-id-input");

        dateInput.value = localStorage.getItem("date") || "";
        chatgptKeyInput.value = localStorage.getItem("chatgpt_key") || "";
        notionKeyInput.value = localStorage.getItem("notion_key") || "";
        notionDbIdInput.value = localStorage.getItem("notion_db_id") || "";

        // フォーム送信時に localStorage へ保存する
        const form = document.getElementById("upload-form");
        form.addEventListener("submit", function() {
          localStorage.setItem("date", dateInput.value);
          localStorage.setItem("chatgpt_key", chatgptKeyInput.value);
          localStorage.setItem("notion_key", notionKeyInput.value);
          localStorage.setItem("notion_db_id", notionDbIdInput.value);
        });
      });
    </script>
</body>
</html>
"""



@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        # 各ファイルを個別に取得（単一の名刺画像、複数のヒアリングシード画像）
        business_card_file = request.files.get("business_card")
        hearing_seed_files = request.files.getlist("hearing_seed")
        lead_date = request.form.get("date", None)

        # APIキー等の入力値の上書き（card.py のグローバル変数更新）
        import card
        if request.form.get("chatgpt_key", "").strip():
            card.CHATGPT4OAPI_TOKEN = request.form.get("chatgpt_key", "").strip()
        if request.form.get("notion_key", "").strip():
            card.NOTION_API_TOKEN = request.form.get("notion_key", "").strip()
        if request.form.get("notion_db_id", "").strip():
            card.DATABASE_ID = request.form.get("notion_db_id", "").strip()

        business_card_path = None
        hearing_seed_paths = []

        # 名刺画像の保存とJPEG変換
        if business_card_file and business_card_file.filename:
            bc_filepath = os.path.join(UPLOAD_FOLDER, business_card_file.filename)
            business_card_file.save(bc_filepath)
            try:
                base, _ = os.path.splitext(bc_filepath)
                business_card_path = base + ".jpeg"
                subprocess.run(["magick", "convert", bc_filepath, business_card_path], check=True)
                os.remove(bc_filepath)
                print(f"Converted {bc_filepath} to {business_card_path}")
            except Exception as e:
                print("名刺画像変換エラー:", e)

        # ヒアリングシード画像の保存とJPEG変換（複数枚）
        if hearing_seed_files:
            for file in hearing_seed_files:
                if file.filename == "":
                    continue
                hs_filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(hs_filepath)
                try:
                    base, _ = os.path.splitext(hs_filepath)
                    jpeg_path = base + ".jpeg"
                    subprocess.run(["magick", "convert", hs_filepath, jpeg_path], check=True)
                    os.remove(hs_filepath)
                    print(f"Converted {hs_filepath} to {jpeg_path}")
                    hearing_seed_paths.append(jpeg_path)
                except Exception as e:
                    print("ヒアリングシード画像変換エラー:", e)

        # 変換後のファイルパスをローカルURLに変換
        if business_card_path:
            # 例: http://127.0.0.1:5000/uploads/ファイル名.jpeg
            business_card_url = request.host_url + "uploads/" + os.path.basename(business_card_path)
            hearing_seed_urls = [request.host_url + "uploads/" + os.path.basename(p) for p in hearing_seed_paths]

            # card.main() がURLを受け取るように実装している前提
            card.main(business_card_url, lead_date, hearing_seed_urls)
            message = "アップロードした画像の処理が完了しました。"
        else:
            message = "名刺画像のアップロードまたは変換に失敗しました。"

    return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)