import requests
import json
import os
import asyncio
from openai import AsyncOpenAI
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "aws", ".env"))

# OpenAI APIキー
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o"

# S3設定
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")


async def ocr_image_from_url_async(image_url, max_retries=5) -> dict:
    """
    非同期版：指定した画像の公開URLから、GPTにOCR解析を依頼し、
    抽出されたテキストを、階層構造を持たない単純なJSON形式で返す関数です。
    最大5回まで再試行します。
    """

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    content = """ 
    これは名刺の画像です。名刺に記載されている文字情報をそのまま抽出してください。会社名、部署、役職、担当者氏名、住所、電話番号、携帯番号、Eメール、郵便番号の情報を有効なJSON形式のみで返してください。推論や推測は行わず、名刺に明確に記載されている情報のみを抽出してください。"""
            
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
