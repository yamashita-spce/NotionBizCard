import os
import sys
import datetime
import argparse
import requests
import pytesseract
from PIL import Image
import json
import re
import io
import base64 
import subprocess
from urllib.parse import urlparse
from PIL import Image
import configparser

# 環境変数の設定
config = configparser.ConfigParser()
config.read("../config.ini")

UPLOAD_FOLDER = config["PRIVATE"]["UPLOAD_FOLDER"]
print(UPLOAD_FOLDER)

# OpenAI APIキー
GPTAPI_TOKEN = config["PRIVATE"]["GPTAPI_TOKEN"]
# Notion 
NOTION_API_TOKEN = config["PRIVATE"]["NOTION_API_TOKEN"]
DATABASE_ID = config["PRIVATE"]["DATABASE_ID"]  # NotionデータベースIDの部分のみ
NOTION_VERSION = config["PRIVATE"]["NOTION_VERSION"]


# def ocr_image(image_path, max_size=(1000, 1000)):
#     img = Image.open(image_path)
#     extracted_text = pytesseract.image_to_string(img, lang='jpn')
#     return extracted_text

def decode_and_save_image(encoded_str, output_filename="recovered_image.jpeg"):
    """
    Base64エンコードされた文字列 encoded_str をデコードして、
    指定されたパス output_path に画像ファイルとして保存します。
    """
    # Base64デコードしてバイナリデータに変換
    image_data = base64.b64decode(encoded_str)

    # カレントディレクトリを取得
    current_dir = os.getcwd()
    output_path = os.path.join(current_dir, output_filename)
    
    # バイナリモードでファイルに書き込み
    with open(output_path, "wb") as f:
        f.write(image_data)
    print(f"画像を {output_path} に保存しました。")


def encode_image(image_path):
    """
    画像ファイルを読み込み、Base64エンコードした文字列を返す。
    """
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return encoded


def encode_and_compress_image_target(image_path, target_length=200000, max_size=(800, 800), initial_quality=95):
    """
    画像ファイルを読み込み、指定した最大サイズ(max_size)にリサイズし、
    JPEG形式で圧縮してBase64エンコードした文字列を返します。
    なお、生成されるBase64文字列の長さがtarget_length（デフォルト200,000文字）以下になるよう
    品質を下げて調整します。

    :param image_path: 画像ファイルのパス
    :param target_length: 目標とするBase64文字列の最大文字数（デフォルト200,000文字）
    :param max_size: リサイズ後の最大幅・高さ（デフォルト800x800）
    :param initial_quality: JPEG圧縮の初期品質（1〜95、デフォルト95）
    :return: Base64エンコードされた文字列
    """
    quality = initial_quality
    best_result = None
    best_length = None

    # 最低品質の閾値は10程度とする
    while quality >= 10:
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=quality)
            encoded_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        current_length = len(encoded_str)
        print(f"Quality {quality}: Base64 length = {current_length}")
        # 目標以下になった場合、その値を返す
        if current_length <= target_length:
            print(f"目標の文字数に達しました（品質 {quality} で {current_length} 文字）。")
            return encoded_str
        else:
            # 保存しておく（あとで最低品質の結果を返すため）
            best_result = encoded_str
            best_length = current_length
        quality -= 5

    print(f"最低品質に達しましたが目標未満にはならなかった（最終品質 10 以上で {best_length} 文字）。")
    return best_result


def ocr_image(image_path):
    """
    画像ファイルをBase64エンコードし、GPT-4oの画像入力対応APIを呼び出して
    画像内のテキストを抽出する関数です。
    ※ このコードは、GPT-4oの画像入力機能が利用可能な環境でのみ動作します。
    """

    # encoded_image = encode_image(image_path)
    encoded_image = encode_and_compress_image_target(image_path)
    # encode_and_compress_image_target(encoded_image)

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GPTAPI_TOKEN}",
        "Content-Type": "application/json"
    }

    # Markdown形式で画像を埋め込んだメッセージを作成
    user_message = (
        "以下の画像からテキストを抽出してください。\n"
        f"![image](data:image/jpeg;base64,{encoded_image})"
    )

    data = {
        "model": "gpt-4o-mini",  # 画像入力に対応したモデル（例）
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたはOCRエンジンです。提供された画像から全てのテキストを抽出し、"
                    "抽出したテキストのみを返してください。結果はJSON形式で出力してください。"
                )
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        res_json = response.json()
        content = res_json["choices"][0]["message"]["content"]
        print("=== DEBUG: OCR result ===")
        print(content)
        print("=== end of debug ===")
        try:
            # 返されたJSON文字列をパースして 'text' キーの内容を取得
            result = json.loads(content)
            extracted_text = result.get("text", "")
            return extracted_text
        except Exception as e:
            print("JSONパースエラー:", e)
            return content
    else:
        print("Error:", response.text)
        return None

def analyze_text_with_openai(extracted_text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GPTAPI_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",  
        "messages": [
            {
                "role": "system",
                "content": "あなたは名刺のテキストから必要な情報を抽出するアシスタントです。テキストデータはOCRによって抽出されたものであるため，誤りが含まれる可能性があります。推測している日本語が正しいか確認し，適切に補ってください"
            },
            {
                "role": "user",
                "content": f"以下のテキストから、会社名、業種、部署、氏名、住所、住所の都道府県、電話番号、携帯番号、Eメール、郵便番号の情報をJSON形式でNullは避ける形で，抽出してください.:\n{extracted_text}"
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        res_json = response.json()
        content = res_json["choices"][0]["message"]["content"]

        print("content:", content)
        return content
    else:
        print("Error:", response.text)
        return None

def remove_code_block_fences(s: str) -> str:
    """
    コードブロック（```json ... ```）を取り除く。
    """
    lines = s.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()

def infer_additional_fields(business_card_data):
    """
    抽出済みの名刺情報から、業種、部署、役職を推論する。
    業種は以下のリストから一つを、役職は指定リストから一つを選ぶこと。
    部署は以下のリストから一つを、役職は指定リストから一つを選ぶこと。
    
    推論対象部署リスト:
    CS部, ITソルーション部, コーポレート本部, なし, マーケティング部, 営業部, 企画開発部, 技術部,
    経営企画部, 経営管理部, 経理部, 人事部, 総務部, 品質管理部, 法務部, 業務部, その他
    
    推論対象役職リスト:
    部長, 本部長, 事務部長, 不明, 一般社員, 課長, シニアエキスパート, 役員・理事, 代表取締役,
    係長(リーダー・班長), マネージャ, 副部長, フリーランス, 係長, 課長代理, 主任
    """
    prompt = f"""
以下は名刺から抽出された情報です。これらをもとに、以下の項目を推論してください。

【推論項目】
1. 業種：以下のリストから必ず一つ選んでください。
   [01農業, 02林業, 03漁業, 04水産養殖業, 05鉱業・採石業・砂利採取業, 06総合工事業, 07職別工事業, 08設備工事業, 09食料品製造業, 10飲料・たばこ・飼料製造業, 11繊維工業, 12木材・木製品製造業, 13家具・装備品製造業, 14パルプ・紙・紙加工品製造業, 15印刷・同関連業, 16化学工業, 17石油製品・石炭製品製造業, 18プラスチック製品製造業, 19ゴム製品製造業, 20なめし革・同製品・毛皮製造業, 21窯業・土石製品製造業, 22鉄鋼業, 23非鉄金属製造業, 24金属製品製造業, 25はん用機械器具製造業, 26生産用機械器具製造業, 27業務用機械器具製造業, 28電子部品・回路・デバイス製造業, 29電気機械器具製造業, 30情報通信機械器具製造業, 31輸送用機械器具製造業, 32その他の製造業, 33電気業, 34ガス業, 35熱供給業, 36水道業, 37通信業, 38放送業, 39情報サービス業, 40インターネット附随サービス業, 41映像・音声・文字情報制作業, 42鉄道業, 43道路旅客運送業, 44道路貨物運送業, 45水運業, 46航空運輸業, 47倉庫業, 48運輸に附帯するサービス業, 49郵便業, 50各種商品卸売業, 51繊維・衣服等卸売業, 52飲食料品卸売業, 53建築材料・鉱物・金属材料卸売業, 54機械器具卸売業, 55その他の卸売業, 56各種商品小売業, 57織物・衣服・身の回り品小売業, 58飲食料品小売業, 59機械器具小売業, 60その他の小売業, 61無店舗小売業, 62銀行業, 63協同組織金融業, 64貸金業・クレジットカード業, 65金融商品取引・商品先物取引業, 66補助的金融業等, 67保険業, 68不動産取引業, 69不動産賃貸業・管理業, 70物品賃貸業, 71学術・開発研究機関, 72専門サービス業, 73広告業, 75宿泊業, 76飲食店, 77持ち帰り・配達飲食サービス業, 78洗濯・理容・美容・浴場業, 79その他の生活関連サービス業, 80娯楽業, 81学校教育, 82その他の教育・学習支援業, 83医療業, 84保健衛生, 85社会保険・社会福祉・介護事業, 86郵便局, 87協同組合, 88廃棄物処理業, 89自動車整備業, 90機械等修理業, 91職業紹介・労働者派遣業, 92その他の事業サービス業, 93政治・経済・文化団体, 94宗教, 95その他のサービス業, 97国家公務, 98地方公務]
2. 部署：以下のリストから必ず一つ選んでください。
   [CS部, ITソルーション部, コーポレート本部, なし, マーケティング部, 営業部, 企画開発部, 技術部, 経営企画部, 経営管理部, 経理部, 人事部, 総務部, 品質管理部, 法務部, 業務部, その他]
3. 役職：以下のリストから必ず一つ選んでください。
   [部長, 本部長, 事務部長, 不明, 一般社員, 課長, シニアエキスパート, 役員・理事, 代表取締役, 係長(リーダー・班長), マネージャ, 副部長, フリーランス, 係長, 課長代理, 主任]

【名刺情報】
{json.dumps(business_card_data, ensure_ascii=False, indent=2)}

出力は有効なJSON形式で、以下のキーを含むものとしてください：
"業種", "部署", "役職"
"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GPTAPI_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",  # 使用するモデル名
        "messages": [
            {
                "role": "system",
                "content": "あなたは名刺情報から適切なタグを推論するアシスタントです。出力は有効なJSONのみを返してください。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        res_json = response.json()
        content = res_json["choices"][0]["message"]["content"]
        content_cleaned = remove_code_block_fences(content)
        try:
            inferred = json.loads(content_cleaned)
            print("推論結果:", inferred)
            return inferred
        except Exception as e:
            print("Infer JSON parse error:", e)
            return {}
    else:
        print("Infer API error:", response.text)
        return {}

def build_notion_properties(business_card_data, inferred_fields, lead_date_str=None):
    # リード獲得日の変換（例："3/12" → "2025-03-12T00:00:00"）
    lead_date = None
    if lead_date_str:
        try:
            month, day = map(int, lead_date_str.split("/"))
            lead_date = datetime.datetime(2025, month, day).isoformat()
            print("リード獲得日:", lead_date)
        except Exception as e:
            print(f"リード獲得日のパースエラー: {e}")
            lead_date = None

    properties = {}

    # ▼ 会社名: Title 型
    # Notion 側で「会社名」が title プロパティとして定義されている場合、
    # 空なら "title": []、値があれば "title": [ { "type": "text", "text": {"content": ...} } ]
    company = business_card_data.get("会社名", "").strip()
    if company:
        properties["会社名"] = {
            "title": [
                {
                    "type": "text",
                    "text": {"content": company}
                }
            ]
        }
    else:
        properties["会社名"] = {"title": []}
    
    # ▼ 担当者氏名: Rich text 型
    # Notion 側で「担当者氏名」が rich_text なら、以下のようにする
    name = business_card_data.get("氏名", "").strip()
    if name:
        properties["担当者氏名"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": name}
                }
            ]
        }
    else:
        properties["担当者氏名"] = {"rich_text": []}

    # ▼ 業種: select 型
    industry = inferred_fields.get("業種", "").strip()
    if industry:
        properties["業種"] = {"select": {"name": industry}}
    else:
        properties["業種"] = {"select": None}

    # ▼ 部署: multi_select 型
    department = inferred_fields.get("部署", "").strip()
    if department:
        properties["部署"] = {"multi_select": [{"name": department}]}
    else:
        properties["部署"] = {"multi_select": []}

    # ▼ 正式部署名: Rich text 型
    dept_raw = business_card_data.get("部署", "").strip()

    if dept_raw:
        properties["正式部署名"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": dept_raw}
                }
            ]
        }
    else:
        properties["正式部署名"] = {"rich_text": []}

    # ▼ 役職: multi_select 型
    title_inferred = inferred_fields.get("役職", "").strip()
    if title_inferred:
        properties["役職"] = {"multi_select": [{"name": title_inferred}]}
    else:
        properties["役職"] = {"multi_select": []}

    # ▼ 役職区分: rich_text 型
    role_raw = business_card_data.get("役職", "").strip() or title_inferred
    if role_raw:
        properties["役職区分"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": role_raw}
                }
            ]
        }
    else:
        properties["役職区分"] = {"rich_text": []}

    # ▼ 電話番号: phone_number 型
    phone = business_card_data.get("電話番号", "").strip()
    if phone:
        properties["電話番号"] = {"phone_number": phone}
    else:
        properties["電話番号"] = {"phone_number": None}

    # ▼ メール: email 型
    email = business_card_data.get("Eメール", "").strip()
    if email:
        properties["メール"] = {"email": email}
    else:
        properties["メール"] = {"email": None}

    # ▼ リード獲得日: date 型
    if lead_date:
        properties["リード獲得日"] = {"date": {"start": lead_date}}
    else:
        properties["リード獲得日"] = {"date": None}

    # ▼ 以下、空欄の項目は Notion の型に合わせたデフォルト値
    properties["リードステータス"] = {"status": None}
    properties["担当"] = {"people": []}
    properties["商談メモ"] = {"rich_text": []}
    properties["ペルソナ"] = {"select": None}
    properties["商談ステータス"] = {"status": None}
    properties["次アクション"] = {"rich_text": []}
    properties["BANT"] = {"rich_text": []}
    properties["契約開始日"] = {"date": None}
    properties["製品"] = {"multi_select": []}
    properties["契約プラン"] = {"select": None}
    properties["料金形態"] = {"select": None}
    properties["割引"] = {"number": None}
    properties["契約ステータス"] = {"select": None}
    properties["自動更新"] = {"checkbox": False}
    properties["チームID"] = {"rich_text": []}
    properties["クレーム"] = {"rich_text": []}
    properties["解約理由"] = {"rich_text": []}

    # ▼ 郵便番号: rich_text 型
    zipcode = business_card_data.get("郵便番号", "").strip()
    if zipcode:
        properties["郵便番号"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": zipcode}
                }
            ]
        }
    else:
        properties["郵便番号"] = {"rich_text": []}

    # ▼ 都道府県: rich_text 型
    address = business_card_data.get("住所", "").strip()
    prefecture = ""
    if address:
        # アドレスの先頭要素だけ取り出す実装例（自由に変更可）
        parts = address.split()
        prefecture = parts[0] if parts else ""
    if prefecture:
        properties["都道府県"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": prefecture}
                }
            ]
        }
    else:
        properties["都道府県"] = {"rich_text": []}

    # ▼ 住所: rich_text 型
    if address:
        properties["住所"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": address}
                }
            ]
        }
    else:
        properties["住所"] = {"rich_text": []}

    # ▼ デバッグ出力
    print("=== DEBUG: properties ===")
    for k, v in properties.items():
        print(k, v)
    print("=== end of debug ===")

    return properties


def create_notion_page(properties):
    """
    Notion API を呼び出してページを作成する関数。
    """
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties,
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("Notionページの作成に成功しました。")
        page = response.json()
        return page.get("id")
    else:
        print(f"Notionページ作成エラー: {response.text}")


def append_image_blocks(page_id, image_urls):
    """
    作成済みのページ（page_id）の本文に、外部画像URLを用いた画像ブロックを追加する関数です。
    image_urls は追加する画像のURLのリスト。
    """
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    children = []
    for img_url in image_urls:
        children.append({
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {"url": img_url}
            }
        })
    data = {"children": children}
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("画像ブロックの追加に成功しました。")
    else:
        print(f"画像ブロック追加エラー: {response.text}")

def url_to_local_path(url):
    """
    画像のURLから、ローカルのファイルパスを生成する。
    例: "http://127.0.0.1:5000/uploads/IMG_0798.jpeg" → "uploads/IMG_0798.jpeg"
    """
    basename = os.path.basename(urlparse(url).path)
    print(f"Downloading: {url} ...")
    return os.path.join(UPLOAD_FOLDER, basename)


def main(business_card_input, hearing_seed_inputs=[], lead_date_str=None):

    # 名刺画像について、もしURLならローカルファイルパスに変換
    if business_card_input.startswith("http"):
        business_card_local = url_to_local_path(business_card_input)
    else:
        business_card_local = business_card_input

    # ヒアリングシード画像についても、URLならローカルファイルパスに変換
    local_hearing_seed_paths = []
    for hs in hearing_seed_inputs:
        if hs.startswith("http"):
            local_hearing_seed_paths.append(url_to_local_path(hs))
        else:
            local_hearing_seed_paths.append(hs)


    if business_card_local.lower().endswith((".png", ".jpg", ".jpeg")):
        
        for add in hearing_seed_inputs:
            if not add.lower().endswith((".png", ".jpg", ".jpeg")):
                print(f"Error: {add} is not an image file.")
                exit(1)

        # business_card_local = os.path.join(folder_path, filename)
        # urlからファイルパスに変換
        print(f"Processing: {business_card_local}")
            
        # 1) OCRでテキスト抽出
        analysis_result = ocr_image(business_card_local)

        # 2) 名刺情報をChatGPTで解析（抽出情報）
        # analysis_result = analyze_text_with_openai(extracted_text)

        # analysis_result = ocr_image(business_card_local)
        analysis_result_cleaned = remove_code_block_fences(analysis_result)
        try:
            extracted_info_dict = json.loads(analysis_result_cleaned)
        except Exception as e:
            print("JSONデコードエラー:", e)

        # 3) 推論が必要な項目（業種、部署、役職）を推論する
        inferred_fields = infer_additional_fields(extracted_info_dict)

        # 4) Notionに送るためのプロパティを組み立てる
        properties = build_notion_properties(extracted_info_dict, inferred_fields, lead_date_str)

        # 5) Notion APIでページ作成
        page_id = create_notion_page(properties)

        # 6) 画像をNotionページに追加
        # ※ ここでは例として、貼り付けたい画像URLを直接指定しています
        # print(business_card_input)
        # append_image_blocks(page_id, business_card_input)
        # for add in hearing_seed_inputs:
        #     append_image_blocks(page_id, add)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <image_folder_path> [lead_date in M/D format, e.g. 3/12]")
    else:
        image_url = sys.argv[1]
        lead_date_input = sys.argv[2] if len(sys.argv) > 2 else None
        add_image_urls = sys.argv[3] 

        main(image_url, add_image_urls, lead_date_input)

