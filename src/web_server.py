# web_server.py
from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for
import os
import re
import time
from main import main as process_cards
from werkzeug.utils import secure_filename
from PIL import Image
import datetime
from pathlib import Path
import subprocess
import socket
import shutil


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

HTML_TEMPLATE = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>名刺処理アップローダー</title>
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@^2/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
  <div class="w-full max-w-md bg-white rounded-xl shadow-lg p-6">
    <h1 class="text-2xl font-semibold text-center mb-6">リードデータベース</h1>
    <form method="post" enctype="multipart/form-data" id="upload-form" class="space-y-6">
      <!-- 名刺画像 -->
      <div>
        <label class="block font-medium mb-1">名刺画像</label>
        <label for="business-card-input" class="cursor-pointer inline-flex items-center px-4 py-2 bg-indigo-100 rounded-lg hover:bg-indigo-200 transition">
          ファイルを選択
        </label>
        <input type="file" name="business_card" id="business-card-input" accept="image/*" class="hidden" required>
        <div id="business-card-preview" class="mt-2 grid grid-cols-1 gap-2"></div>
      </div>

      <!-- ヒアリングシート -->
      <div>
        <label class="block font-medium mb-1">ヒアリングシート画像（複数可）</label>
        <label for="hearing-seed-input" class="cursor-pointer inline-flex items-center px-4 py-2 bg-indigo-100 rounded-lg hover:bg-indigo-200 transition">
          ファイルを選択
        </label>
        <input type="file" name="hearing_seed" id="hearing-seed-input" multiple accept="image/*" class="hidden">
        <div id="hearing-seed-preview" class="mt-2 grid grid-cols-3 gap-2"></div>
      </div>

      <!-- その他 -->
      <div>
        <label class="block font-medium">リード獲得日 (YYYY/M/D形式)</label>
        <input type="text" name="date" id="date-input" placeholder="例: 2025/3/12" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500">
      </div>

      <!--
      <div>
        <label class="block font-medium">※OpenAI API Key</label>
        <input type="text" name="chatgpt_key" id="chatgpt-key-input" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500">
      </div>
      <div>
        <label class="block font-medium">※Notion API Key</label>
        <input type="text" name="notion_key" id="notion-key-input" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500">
      </div>
      <div>
        <label class="block font-medium">※Notion Database ID</label>
        <input type="text" name="notion_db_id" id="notion-db-id-input" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500">
      </div>
      -->

      <!-- 送信ボタン -->
      <button id="submit-btn" type="submit" class="w-full py-2 px-4 bg-indigo-600 text-white font-semibold rounded-lg shadow hover:bg-indigo-700 transition flex items-center justify-center">
        <span id="btn-text">アップロードして処理開始</span>
        <svg id="btn-spinner" class="hidden animate-spin ml-2 h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
      </button>
    </form>
    {% if message %}
      <p class="mt-4 text-center {{ 'text-green-600' if success == '1' else 'text-red-600' }}">
        {{ message|safe }}
      </p>
    {% endif %}
  </div>

  <script>
    // 名刺プレビュー
    document.getElementById("business-card-input").addEventListener("change", e => {
      const container = document.getElementById("business-card-preview");
      container.innerHTML = "";
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = ev => {
          const img = document.createElement("img");
          img.src = ev.target.result;
          img.alt = file.name;
          img.className = "w-16 h-16 object-cover rounded";
          container.appendChild(img);
        };
        reader.readAsDataURL(file);
      }
    });

    // ヒアリングシートプレビュー（累積表示）
    const hearingInput = document.getElementById("hearing-seed-input");
    const hearingPreview = document.getElementById("hearing-seed-preview");
    const selectedHearing = [];

    hearingInput.addEventListener("change", e => {
      Array.from(e.target.files).forEach(file => {
        if (!selectedHearing.some(f => f.name === file.name && f.size === file.size)) {
          selectedHearing.push(file);
          const reader = new FileReader();
          reader.onload = ev => {
            const img = document.createElement("img");
            img.src = ev.target.result;
            img.alt = file.name;
            img.className = "w-16 h-16 object-cover rounded";
            hearingPreview.appendChild(img);
          };
          reader.readAsDataURL(file);
        }
      });
      // リセット input して再選択可能に
    //   hearingInput.value = "";
    });

    // 送信時にボタン無効化＆スピナー表示
    document.getElementById("upload-form").addEventListener("submit", () => {
    const btn = document.getElementById("submit-btn");
    document.getElementById("btn-text").classList.add("hidden");
    document.getElementById("btn-spinner").classList.remove("hidden");
    btn.disabled = true;
    });
  </script>
</body>
</html>
"""


def convert_to_jpeg(src_path, dest_path):
    # 一時ファイルパス
    temp_path = src_path + ".tmp"

    # 1) 画像を開いてリサイズ＆JPEG保存（必ず閉じられる）
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        img.thumbnail((512, 512), Image.LANCZOS)
        img.save(temp_path, format="JPEG", quality=85)

    # 2) 元ファイルを削除
    os.remove(src_path)

    # 3) 一時ファイルを最終パスにリネーム
    os.replace(temp_path, dest_path)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/", methods=["GET", "POST"])
def index():
    message = message = request.args.get("message", "")
    success = request.args.get("success", "0")
    
    if request.method == "POST":
        # 各ファイルを個別に取得（単一の名刺画像、複数のヒアリングシード画像）
        business_card_file = request.files.get("business_card")
        hearing_seed_files = [f for f in request.files.getlist("hearing_seed") if f and f.filename.strip()]
        raw_date = request.form.get("date", "").strip()


        # 日付処理
        if raw_date == "":
            today = datetime.date.today()
            lead_date = f"{today.year}/{today.month}/{today.day}"
        elif re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", raw_date):
            lead_date = raw_date
        else:
            message = "日付は YYYY/M/D 形式で入力してください。"
            return render_template_string(HTML_TEMPLATE, message=message)
        

        # APIキー等の入力値の上書き（card.py のグローバル変数更新）
        import main
        if request.form.get("chatgpt_key", "").strip():
            main.CHATGPT4OAPI_TOKEN = request.form.get("chatgpt_key", "").strip()
        if request.form.get("notion_key", "").strip():
            main.NOTION_API_TOKEN = request.form.get("notion_key", "").strip()
        if request.form.get("notion_db_id", "").strip():
            main.DATABASE_ID = request.form.get("notion_db_id", "").strip()

        # 画像ファイルのパス
        business_card_path = None
        hearing_seed_paths = []

        # 名刺画像の保存とJPEG変換
        if business_card_file and business_card_file.filename:
            filename = secure_filename(business_card_file.filename)
            bc_filepath = os.path.join(UPLOAD_FOLDER, filename)
            business_card_file.save(bc_filepath)
            print("Saved to disk:", os.path.exists(bc_filepath))

            base, _ = os.path.splitext(bc_filepath)
            business_card_path = base + ".jpeg"

            success = False
            for attempt in range(5):
                try:
                    convert_to_jpeg(bc_filepath, business_card_path)
                    success = True
                    break
                except Exception as e:
                    print(f"[名刺変換試行 {attempt+1}/5] エラー: {e}")
                    time.sleep(1)

            if not success:
                message = "名刺画像の変換に失敗しました。再度アップロードしてください。"
                return render_template_string(HTML_TEMPLATE, message=message)
        else:
            message = "名刺画像が選択されていません。"
            return render_template_string(HTML_TEMPLATE, message=message)
        

        # ヒアリングシード画像の保存とJPEG変換（複数枚）
        for file in hearing_seed_files:
            if not file.filename:
                continue

            filename = secure_filename(file.filename)
            hs_filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(hs_filepath)
            # print("Saved seed to disk:", os.path.exists(hs_filepath))

            try:
                base, _ = os.path.splitext(hs_filepath)
                jpeg_path = base + ".jpeg"
                convert_to_jpeg(hs_filepath, jpeg_path)
                # print("Converted seed exists:", os.path.exists(jpeg_path))
                hearing_seed_paths.append(jpeg_path)
            except Exception as e:
                print("ヒアリングシード画像変換エラー:", e)


        # 変換後のファイルパスをローカルURLに変換
        if business_card_path:
            
            business_card_url = os.path.abspath(business_card_path)
            hearing_seed_urls = [os.path.abspath(p) for p in hearing_seed_paths]
            
            # card.main() がURLを受け取るように実装している前提
            print("名刺画像URL:", business_card_url)
            print("ヒアリングシードURL:")
            for f in hearing_seed_urls:
                print(f)
            print("リード獲得日:", lead_date)
            
            try:
                main.main(business_card_url, hearing_seed_urls, lead_date)
                message="notionデータベースに登録しました。"
                return redirect(url_for("index", message=message, success="1"))
            except Exception as e:
                print("処理エラー:", e)
                error_note = "アップロードできませんでした。<br><small>※名刺画像は名刺がしっかり見えるものを選択してください。</small>"
                return redirect(url_for("index", message=error_note, success="0"))
       
        else:
            message = "名刺画像のアップロードまたは変換に失敗しました。"

    return render_template_string(HTML_TEMPLATE, message=message, success=success)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)