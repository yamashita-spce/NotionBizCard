import google.generativeai as genai
import json
import os
import re
import traceback # For detailed error logging if needed
import configparser

# --- 設定 ---
config = configparser.ConfigParser()
config.read("../config.ini", encoding="utf-8")

API_KEY = config["HOST"]["GEMINI_TOKEN"]  # Gemini APIキー
MODEL_NAME = config["HOST"]["GEMINI_MODEL"]  # 使用するGeminiモデル名


# --- プロンプト生成関数  ---
def build_gemini_prompt(context, recipient_details, exhibition_name="[展示会名]"):
    
    """Gemini API用の単一プロンプトを作成する"""
    context_string = "\n".join([f"* {key}: {value}" for key, value in context.items() if value])
    
    # 送り元（自分）の情報
    sender_name = context.get('tantosha_value', '[送信者名]')
    sender_company = "mocomoco株式会社" 
    
    # 送り先の情報
    recipient_name_context = recipient_details.get('担当者氏名', '[担当者名]') 
    recipient_company_info = recipient_details.get('会社名', '[送り先会社名]') 

    
    # timing_value = context.get('timing_value')
    # timing_jp = timing_map.get(timing_value, '不明')
    
    # ヒアリング情報の取得
    current_situation = context.get('current_situation_value') or '(空欄)'
    problem = context.get('problem_value') or '(空欄)'
    most_important_need = context.get('most_important_need_value') or '(空欄)'
    interested_service = context.get('proposal_plan_value', '[サービス名]')


    prompt = f"""
あなたはプロの営業担当者（{sender_name}、{sender_company}所属）です。以下の展示会でのヒアリング情報（context）をもとに、パーソナライズされたフォローアップメールの「件名」と「本文（署名なし）」を作成してください。

**メール作成の要件:**
* **タイトル** : パーソナライズされたタイトルで、冒頭に「{recipient_name_context}様」を含めてください。
* **宛先:** {recipient_company_info} {recipient_name_context} 様 
* **トーン:** 丁寧、親しみやすい、パーソナル。強い売り込みは避け、相手に寄り添う姿勢を示す。「御礼」「感銘を受ける」のような大袈裟な言葉は使わないでください。
* **目的:** {exhibition_name}訪問のお礼と、会話内容を踏まえた軽いフォローアップ。しつこくない提案。
* **必須要素:**
    * {exhibition_name}への言及と訪問のお礼。
    * 相手が興味を示したサービス「{interested_service}」への言及。
    * 簡単な情報交換のための短いWeb会議（30分-60分程度）の提案。（ただし、具体的な予約リンクやトライアル案内は含めないでください。後続の固定テキストで案内します。）
* **重要：相手の状況・課題・ニーズの考慮:**
    * 以下のcontext情報を確認してください：
        * 現状: {current_situation}
        * 問題: {problem}
        * 最重要ニーズ: {most_important_need}
        * 
    * **もしこれらの情報（現状、問題、最重要ニーズ）に具体的な記述があれば、** その会話内容に具体的に触れる。（「〇〇といった点で特に印象が残っております」など、可能なら推測、難しければ汎用的な表現で）。
    * **提案するサービス「{interested_service}」が、例えば「{problem}」といった課題の解決や「{most_important_need}」というニーズの充足にどのように貢献できる可能性があるかを、相手の言葉を引用するなどして示唆してください。
    * **もしこれらの情報が空欄または記述が少ない場合は、** 相手の具体的な状況を決めつけず、「もしよろしければ、現在お困りの点や重視されている点など、もう少し詳しくお聞かせいただけますでしょうか」といった、相手からヒアリングしたい丁寧な姿勢を示しつつ、サービスへの関心に対する感謝と一般的なメリットに焦点を当ててください。
* **重要：後続テキストとの連携:**
    * 生成する本文の後には、オンライン打ち合わせ予約や無料トライアルに関する以下の固定テキストが続きます。本文の終わり方は、この後続テキストに自然につながるように調整してください。本文の最後で具体的な日程調整やトライアルの申し込みを促すのではなく、情報提供や次のステップへの意欲を示す程度に留めてください。（例：「もしよろしければ、貴社の状況に合わせて、より詳しい情報提供やデモンストレーションをさせていただければ幸いです。」などで結ぶ）
    * （後続テキストの開始部分： ▼オンラインお打ち合わせのご予約（Timerex）...）

**ヒアリング情報 (context):**
{context_string}

**重要：出力形式**
以下のJSON形式**のみ**を、他の説明文や```json ```のようなマークダウンなしで出力してください。
{{
    "title": "ここにメールの件名",
    "message_text": "ここにメールの本文（必ず'{recipient_name_context} 様\\n{recipient_company_info}'のように、宛名と改行、会社名で始めてください。署名は含めないでください。）"
}}
"""
    return prompt

# --- メインのメール生成関数 ---
def generate_email_with_gemini(context, recipient_details, exhibition_name="[展示会名]"):
    """
    Gemini APIを1回呼び出してメールのタイトルと本文(JSON)を取得し、
    最終的なJSON（署名なし）とトークン数を返す関数。

    Args:
        context (dict): 展示会のヒアリング情報。
        recipient_details (dict): *送り先*の情報。
        exhibition_name (str): 展示会の名前。

    Returns:
        tuple: (JSON文字列, 合計トークン数)
               エラー時は (エラー情報JSON文字列, 0)
    """
    if not API_KEY:
        return json.dumps({"error": "APIキーが設定されていません。"}, ensure_ascii=False, indent=2), 0

    try:
        # APIキーとモデルを設定
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)

        # プロンプトを生成
        prompt = build_gemini_prompt(context, recipient_details, exhibition_name)

        # APIリクエストを送信
        response = model.generate_content(prompt)
        usage_metadata = response.usage_metadata
        total_tokens = usage_metadata.total_token_count if usage_metadata else 0

        # レスポンスからJSONテキストを抽出・整形
        generated_text = response.text
        cleaned_text = re.sub(r'^```(?:json)?\s*|\s*```$', '', generated_text.strip(), flags=re.MULTILINE | re.DOTALL)

        # JSONとしてパース
        generated_json = {}
        generated_title = "[件名抽出エラー]"
        generated_message_text = "[本文抽出エラー]"
        try:
            generated_json = json.loads(cleaned_text)
            generated_title = generated_json.get("title", generated_title)
            generated_message_text = generated_json.get("message_text", generated_message_text)
        except json.JSONDecodeError as json_err:
            print(f"Error decoding JSON from response: {json_err}")
            print(f"Response text was: {cleaned_text}")
            generated_title = "[件名JSON解析エラー]"
            generated_message_text = f"[本文JSON解析エラー]\nAPI応答:\n{cleaned_text}"

        # ★修正箇所: 宛名の追加処理を削除 (AIが本文に含めるため)
        final_body = generated_message_text.strip() # AIが生成した本文をそのまま使用

        # 結果をJSON形式で整形
        result_json = {
            "タイトル": generated_title,
            "本文": final_body # 署名なしの本文
        }
        
        text_block = """
    
▼オンラインお打ち合わせのご予約（Timerex）
(ここに予約リンクを挿入)
すぐのお打ち合わせが難しい場合は、14日間、全機能をお試しいただける無料トライアルもございます。「試してみたい」と思われましたら、このメールにご返信ください。詳細をご案内します。 （可能であれば、直接お話しして最適な使い方を見つけられたら嬉しいです。）
お忙しいところ恐縮ですが、ご連絡をお待ちしております。
"""
        
        result_json["本文"] += text_block # 固定テキストを追加
        
        return json.dumps(result_json, ensure_ascii=False, indent=2), total_tokens

    except Exception as e:
        print(f"[ERROR] Gemini API の呼び出しまたは処理中にエラーが発生しました:", e)
        # traceback.print_exc() # 詳細なトレースバックが必要な場合
        return json.dumps({"error": f"メール生成中に予期せぬエラーが発生しました: {e}"}, ensure_ascii=False, indent=2), 0







# テストデータ

# --- 送り先情報 (旧 sender_info) ---
recipient_info_example = {
    "会社名": "送り先株式会社",
    "業種": "情報通信業",
    "部署": "営業部",
    "役職": "部長",
    "担当者氏名": "山田 太郎",
    "住所": "東京都千代田区...",
    "正式部署名": "営業本部 第一営業部",
    "役職区分": "管理職",
    "住所の都道府県": "東京都",
    "電話番号": "03-xxxx-xxxx",
    "携帯番号": "090-xxxx-xxxx",
    "Eメール": "taro.yamada@example.com",
    "郵便番号": "100-0000"
}


# --- ダミーの context データ (展示会でのヒアリング情報) ---
context_filled = {
    'message': '', 'success': '1',
    'tantosha_value': '高橋 次郎',
    'proposal_plan_value': 'mocoVoice Web Business',
    'current_situation_value': '現在、部署内で議事録作成に毎月合計40時間かかっている。精度も担当者によってばらつきがある。',
    'problem_value': '議事録作成の工数削減と品質の均一化が課題。特に専門用語の認識精度が低い。',
    'most_important_need_value': '月20時間以上の工数削減と、専門用語認識率90%以上を達成したい。',
    'proposal_content_value': '', 'consideration_reason_value': '', 'lead_date_value': '',
    'needs_value': '3', 'authority_value': '2', 'timing_value': '3', 'source_tantosha': '山田 太郎'
}
context_empty = {
    'message': '不明なエラーが発生しました。', 'success': '0',
    'tantosha_value': '鈴木 一郎',
    'proposal_plan_value': 'mocoVoice Web Standard',
    'current_situation_value': '', 'problem_value': '', 'most_important_need_value': '',
    'proposal_content_value': '', 'consideration_reason_value': '', 'lead_date_value': '',
    'needs_value': '3', 'authority_value': '1', 'timing_value': '3', 'source_tantosha': '佐藤 花子'
}

# --- 実行例 ---
if __name__ == "__main__":# または "gemini-1.5-pro-latest" など

    print("\n--- 詳細情報がある場合のメール生成例 ---")
    email_json, tokens_filled = generate_email_with_gemini(
        context_filled,
        recipient_info_example,
        exhibition_name="業務改善EXPO"
    )
  
  # 固定テキストを追加
    print(email_json)
    print(f"Total tokens used: {tokens_filled}")


