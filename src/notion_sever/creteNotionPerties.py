import datetime
import requests
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "aws", ".env"))

# Notion 
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")  # NotionデータベースIDの部分のみ
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")

# Notion タグ設定
DEFAULT_TAG = os.getenv("DEFAULT_TAG", "未設定").replace('"', '')

# S3 設定
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")

def get_perusona(context):
    """
    ペルソナを決定する関数。
    """
    # ペルソナのマッピング
    persona_map = {
        3: "D",
        4: "C",
        5: "C",
        6: "B",
        7: "B",
        8: "A",
        9: "A",
    }
    
    try:
        needs = int(context.get("needs_value", "").strip())
        authirity = int(context.get("authority_value", "").strip())
        timing = int(context.get("timing_value", "").strip())
        
    except ValueError:
        needs = 0
        authirity = 0
        timing = 0
    
    index = (needs + authirity + timing) 
    return persona_map.get(index, "D")
    
    
# notion データベースプロパティの組み立て
def build_notion_properties(business_card_data, lead_date_str, context):
    # OCR結果がNoneまたは空の場合の処理
    if business_card_data is None:
        print("[警告] OCR結果がNoneです。空のデータで処理を続行します。")
        business_card_data = {}
    elif not isinstance(business_card_data, dict):
        print(f"[警告] OCR結果が辞書型ではありません: {type(business_card_data)}")
        business_card_data = {}
    # リード獲得日の変換（例："2025/3/12" → "2025-03-12T00:00:00"）
    lead_date = None
    if lead_date_str:
        try:
            year, month, day = map(int, lead_date_str.split("/"))
            lead_date = datetime.datetime(year, month, day).isoformat()
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
    name = business_card_data.get("担当者氏名", "").strip()
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

    # ▼ 部署名: rich_text 型（OCR抽出結果をそのまま使用）
    department = business_card_data.get("部署", "").strip()
    if department:
        properties["部署名"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": department}
                }
            ]
        }
    else:
        properties["部署名"] = {"rich_text": []}

    # ▼ 役職名: rich_text 型（OCR抽出結果をそのまま使用）
    title_extracted = business_card_data.get("役職", "").strip()
    if title_extracted:
        properties["役職名"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": title_extracted}
                }
            ]
        }
    else:
        properties["役職名"] = {"rich_text": []}

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

    # ▼ 担当者: multi_select 型
    tantou_list = [
        context.get("tantosha_value","").strip(), 
        context.get("source_tantosha","").strip()
        ]
    
    tantou = []
    for person in tantou_list: 
        if person: 
            tantou.append({"name": person})
    
    if tantou:
        properties["担当"] = {"multi_select": tantou}
    else:
        properties["担当"] = {"multi_select": [{"name": "担当者不明"}]}
    
    # ▼ ヒアリングメモ: rich_text 型（統合されたヒアリング情報）
    memo_items = {
        'current_situation_value': '現状',
        'problem_value': '問題',
        'most_important_need_value': '最重要ニーズ',
        'proposal_content_value': '提案内容',
        'consideration_reason_value': '検討理由'
    }
    
    # メモの内容を生成
    memo_content_lines = []
    for key, label in memo_items.items():
        value = context.get(key, "").strip()
        if value:
            memo_content_lines.append(f"■{label}\n{value}")
    
    # 全ての行を結合（各項目の後に空行を入れる）
    memo_full_content = "\n\n".join(memo_content_lines)
    
    if memo_full_content:
        properties["ヒアリングメモ"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": memo_full_content}
                }
            ]
        }
    else:
        properties["ヒアリングメモ"] = {"rich_text": []}
    
    # ▼ ボイレコ貸し出し: rich_text 型
    voice_record = context.get("voice_recorder_loan_value", "").strip()
    if voice_record:
        properties["ボイレコ貸し出し"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": voice_record}
                }
            ]
        }
    else:
        properties["ボイレコ貸し出し"] = {"rich_text": []}
    
        
    # ▼ 製品: multi select 型
    product = context.get("proposal_plan_value", "")
    if product:
        properties["製品"] = {"multi_select": [{"name": product}]}
    else:
        properties["製品"] = {"multi_select": []}
        
    
    # ▼ 以下、空欄の項目は Notion の型に合わせたデフォルト値
    properties["タグ"] = {"select": {"name": DEFAULT_TAG}}
    properties["ステータス"] = {"multi_select": [{"name": "メール予定"}]}
    properties["ペルソナ"] = {"select": {"name": get_perusona(context)}}
    properties["契約開始日"] = {"date": None}
    properties["料金形態"] = {"select": None}
    properties["割引"] = {"number": None}

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
    # print("=== DEBUG: properties ===")
    # for k, v in properties.items():
    #     print(k, v)
    # print("=== end of debug ===")

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
        print("[*]Notionページの作成に成功しました。")
        page = response.json()
        return page.get("id")
    else:
        print(f"Notionページ作成エラー: {response.text}")


def append_image_blocks(page_id, unique_id, card_image, hearing_images):
    """
    作成済みのページ（page_id）の本文に、S3の画像URLを用いた画像ブロックを追加する関数です。
    """
    from s3_upload import NotionBizCardS3Uploader
    
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    children = []
    
    # S3アップローダーを初期化
    s3_uploader = NotionBizCardS3Uploader()
    
    # 名刺画像の追加（手入力モードでない場合）
    if card_image:
        card_url = s3_uploader.get_card_image_url(unique_id, os.path.basename(card_image))
        if card_url:
            children.append({
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": card_url}
                }
            })
    
    # ヒアリングシート画像の追加
    hearing_urls = s3_uploader.get_hearing_image_urls(unique_id)
    for img_url in hearing_urls:
        children.append({
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {"url": img_url}
            }
        })

    if not children:
        print("[*]追加する画像がありません。")
        return 0

    data = {"children": children}
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("[*]画像ブロックの追加に成功しました。")
        return 0
    else:
        print(f"画像ブロック追加エラー: {response.text}")
        return 1


def append_hearing_images_only(page_id, unique_id, hearing_images):
    """
    ヒアリングシート画像のみをS3からページに追加する関数（手入力モード用）
    """
    from s3_upload import NotionBizCardS3Uploader
    
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    children = []
    
    # S3アップローダーを初期化
    s3_uploader = NotionBizCardS3Uploader()
    
    # ヒアリングシート画像の追加
    hearing_urls = s3_uploader.get_hearing_image_urls(unique_id)
    for img_url in hearing_urls:
        children.append({
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {"url": img_url}
            }
        })

    if not children:
        print("[*]追加する画像がありません。")
        return 0

    data = {"children": children}
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("[*]ヒアリングシート画像ブロックの追加に成功しました。")
        return 0
    else:
        print(f"ヒアリングシート画像ブロック追加エラー: {response.text}")
        return 1

