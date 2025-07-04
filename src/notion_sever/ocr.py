import requests
import json
import configparser
import os
import asyncio
from openai import AsyncOpenAI
from openai import OpenAI

config = configparser.ConfigParser()
# 現在のスクリプトの場所を基準に設定ファイルのパスを決定
config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.ini")
config.read(config_path, encoding="utf-8")

# OpenAI APIキー
OPENAI_API_KEY = config["HOST"]["GPTAPI_TOKEN"]
MODEL = "gpt-4o"

# 画像アップロード用のURL
UPLOAD_URL = config["HOST"]["UPLOAD_URL"]


async def ocr_image_from_url_async(image_url, max_retries=5) -> dict:
    """
    非同期版：指定した画像の公開URLから、GPTにOCR解析を依頼し、
    抽出されたテキストを、階層構造を持たない単純なJSON形式で返す関数です。
    最大5回まで再試行します。
    """

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    content = """ 
    これは名刺の画像です。会社名、業種、部署、役職、担当者氏名、住所、正式部署名、役職区分、住所の都道府県、電話番号、携帯番号、Eメール、郵便番号の情報を有効なJSON形式のみで返してください。ただし、業種、部署、役職は以下のリストから一つ選択してください。
    【推論項目】
    1. 業種：以下のリストから必ず一つ選んでください。
        [01農業, 02林業, 03漁業, 04水産養殖業, 05鉱業・採石業・砂利採取業, 06総合工事業, 07職別工事業, 08設備工事業, 09食料品製造業, 10飲料・たばこ・飼料製造業,
        11繊維工業, 12木材・木製品製造業, 13家具・装備品製造業, 14パルプ・紙・紙加工品製造業, 15印刷・同関連業, 16化学工業, 17石油製品・石炭製品製造業, 18プラスチック製品製造業, 19ゴム製品製造業, 20なめし革・同製品・毛皮製造業,
        21窯業・土石製品製造業, 22鉄鋼業, 23非鉄金属製造業, 24金属製品製造業, 25はん用機械器具製造業, 26生産用機械器具製造業, 27業務用機械器具製造業, 28電子部品・回路・デバイス製造業, 29電気機械器具製造業, 30情報通信機械器具製造業, 
        31輸送用機械器具製造業, 32その他の製造業, 33電気業, 34ガス業, 35熱供給業, 36水道業, 37通信業, 38放送業, 39情報サービス業, 40インターネット附随サービス業, 
        41映像・音声・文字情報制作業, 42鉄道業, 43道路旅客運送業, 44道路貨物運送業, 45水運業, 46航空運輸業, 47倉庫業, 48運輸に附帯するサービス業, 49郵便業, 50各種商品卸売業, 
        51繊維・衣服等卸売業, 52飲食料品卸売業, 53建築材料・鉱物・金属材料卸売業, 54機械器具卸売業, 55その他の卸売業, 56各種商品小売業, 57織物・衣服・身の回り品小売業, 58飲食料品小売業, 59機械器具小売業, 60その他の小売業,
        61無店舗小売業, 62銀行業, 63協同組織金融業, 64貸金業・クレジットカード業, 65金融商品取引・商品先物取引業, 66補助的金融業等, 67保険業, 68不動産取引業, 69不動産賃貸業・管理業, 70物品賃貸業, 
        71学術・開発研究機関, 72専門サービス業, 73広告業, 75宿泊業, 76飲食店, 77持ち帰り・配達飲食サービス業, 78洗濯・理容・美容・浴場業, 79その他の生活関連サービス業, 80娯楽業, 
        81学校教育, 82その他の教育・学習支援業, 83医療業, 84保健衛生, 85社会保険・社会福祉・介護事業, 86郵便局, 87協同組合, 88廃棄物処理業, 89自動車整備業, 
        90機械等修理業, 91職業紹介・労働者派遣業, 92その他の事業サービス業, 93政治・経済・文化団体, 94宗教, 95その他のサービス業, 97国家公務, 98地方公務]
    2. 部署：以下のリストから必ず一つ選んでください。
        [CS部, ITソルーション部, コーポレート本部, なし, マーケティング部, 営業部, 企画開発部, 技術部, 経営企画部, 経営管理部, 経理部, 人事部, 総務部, 品質管理部, 法務部, 業務部, その他]
    3. 役職：以下のリストから必ず一つ選んでください。
        [部長, 本部長, 事務部長, 不明, 一般社員, 課長, シニアエキスパート, 役員・理事, 代表取締役, 係長(リーダー・班長), マネージャ, 副部長, フリーランス, 係長, 課長代理, 主任]"""
            
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[OCR] 試行 {attempt}/{max_retries}: {image_url}")
            
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": content},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                }],
            )
               
            response_text = response.choices[0].message.content
            print(f"[OCR] 試行 {attempt} レスポンス:", response_text[:100] + "..." if len(response_text) > 100 else response_text)
            
            # GPTが拒否した場合の処理
            if "I'm sorry" in response_text or "I can't" in response_text or "cannot" in response_text.lower():
                print(f"[警告] 試行 {attempt}: GPT-4oがリクエストを拒否しました。")
                if attempt < max_retries:
                    print("[リトライ] すぐに再試行します...")
                    continue
                else:
                    print("[エラー] 最大試行回数に達しました。空のデータを返します。")
                    return {}
            
            response_clean = remove_code_block_fences(response_text)
            
            # JSON形式の検証
            try:
                result = json.loads(response_clean)
                print(f"[成功] 試行 {attempt}でOCR処理が完了しました。")
                return result
            except json.JSONDecodeError as je:
                print(f"[警告] 試行 {attempt}: JSONパースエラー: {je}")
                if attempt < max_retries:
                    print("[リトライ] すぐに再試行します...")
                    continue
                else:
                    print(f"[エラー] JSONパース失敗: {response_clean}")
                    return {}
        
        except Exception as e:
            print(f"[エラー] 試行 {attempt}: {e}")
            if attempt < max_retries:
                print("[リトライ] すぐに再試行します...")
                continue
            else:
                print("[エラー] 最大試行回数に達しました。空のデータを返します。")
                return {}

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


def ocr_image_from_url(image_url, max_retries=5) -> dict:
    """
    同期版：既存のコードとの互換性のため残しておく
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 既に実行中のループがある場合は新しいタスクとして実行
            return asyncio.run_coroutine_threadsafe(
                ocr_image_from_url_async(image_url, max_retries), loop
            ).result()
        else:
            return loop.run_until_complete(ocr_image_from_url_async(image_url, max_retries))
    except RuntimeError:
        # ループが取得できない場合は新しいループを作成
        return asyncio.run(ocr_image_from_url_async(image_url, max_retries))


async def ocr_multiple_images_async(image_urls, max_retries=5) -> list:
    """
    複数の画像を並行処理でOCR解析する関数
    """
    tasks = [ocr_image_from_url_async(url, max_retries) for url in image_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 例外が発生した場合は空の辞書を返す
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"[エラー] 画像 {i+1} の処理でエラーが発生: {result}")
            processed_results.append({})
        else:
            processed_results.append(result)
    
    return processed_results


if __name__ == "__main__":
    # 解析したい画像の公開URLを指定してください
    image_url = UPLOAD_URL + "sample.jpg"
    result = ocr_image_from_url(image_url)
    print("OCR抽出結果:")
    print(result)
