# web_server.py
import os
import re
import time
import json
import uuid
from datetime import datetime
# render_template を使うために必要
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, session, jsonify, abort, flash
from werkzeug.utils import secure_filename
from PIL import Image
# main.py 内の main 関数を process_cards としてインポート (存在すると仮定)
try:
    from main import main as process_cards
except ImportError:
    # main.py または process_cards が存在しない場合のダミー関数
    print("警告: main.py または process_cards 関数が見つかりません。ダミー関数を使用します。")
    def process_cards(business_card_path, hearing_sheet_paths, lead_date):
        print("--- process_cards (ダミー) ---")
        print(f"  名刺パス: {business_card_path}")
        print(f"  ヒアリングシートパス: {hearing_sheet_paths}")
        print(f"  リード獲得日: {lead_date}")
        # 失敗をシミュレートする場合: return 1
        print("  (処理成功(0)をシミュレート)")
        return 0 # 正常終了
        # print("  (処理失敗(1)をシミュレート)")
        # return 1 # 異常終了

# --- Flask アプリケーション設定 ---
app = Flask(__name__, template_folder='html')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- 定数・設定 ---
UPLOAD_FOLDER = 'uploads'
HANDOVER_DIR = 'handovers'
ASSIGNESS_LIST = [
    "田中康紀", "大西一誉", "阪本浩太郎", "飯田昌直", "飯田昌哉", 
    "山下一樹", "笹木将太", "神宇知一樹", "その他"
]
PLAN_LIST = [
    "受託開発", "mocoVoice Web（書き起こし・議事録）", "mocoVoice Webフルバージョン",
    "mocoDataset", "mocoDrive", "リアルタイム音声認識", "mocoVoice API", "その他", 
]

PERSONA_OPTIONS = {
    'needs': [
        ('3', '高'),
        ('2', '中'),
        ('1', '低'),
    ],
    'authority': [
        ('3', '部長以上'),
        ('2', '課長以上'),
        ('1', '一般社員'),
    ],
    'timing': [
        ('3', '1-3ヶ月以内'),
        ('2', '3-12ヶ月以内'),
        ('1', '不明・未定'),
    ]
}

# --- ディレクトリ作成 ---
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(HANDOVER_DIR): os.makedirs(HANDOVER_DIR)

# --- ヘルパー関数 ---
def convert_to_jpeg(src_path, dest_path):
    """画像をJPEG形式に変換・リサイズして保存する"""
    temp_path = dest_path + ".tmp"
    try:
        with Image.open(src_path) as img:
            img = img.convert("RGB")
            try:
                img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            except AttributeError:
                img.thumbnail((512, 512), Image.LANCZOS)
            img.save(temp_path, format="JPEG", quality=85)
        os.replace(temp_path, dest_path)
        print(f"Converted image to {dest_path}")
    except Exception as e:
        print(f"Error converting {src_path} to JPEG: {e}")
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except OSError: pass
        raise e

# --- 静的ファイル配信ルート ---
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """アップロードされた画像ファイルへのアクセスを提供"""
    try:
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)
    except FileNotFoundError:
        abort(404)


# --- メインのフォーム表示・処理ルート ---
@app.route("/", methods=["GET", "POST"])
def index():
    # --- POSTリクエストの処理 ---
    if request.method == "POST":
        # 1. コンテキスト辞書の初期化
        context = {
            # 1. 初期値の設定
            'message': "不明なエラーが発生しました。",
            'success': "0", # POSTされた値で初期化
            'assignees_list': ASSIGNESS_LIST,
            'proposal_plan_list': PLAN_LIST,
            'persona_options': PERSONA_OPTIONS,
            
            # 2. フォームデータの取得
            'tantosha_value': request.form.get("tantosha", ""), # 担当者 (name="tantosha")
            'proposal_plan_value': request.form.get('proposal_plan', ''), # 提案プラン (name="proposal_plan")
            'current_situation_value': request.form.get('current_situation', ''), # 現状 (name="current_situation")
            'problem_value': request.form.get('problem', ''), # 問題 (name="problem")
            'most_important_need_value': request.form.get('most_important_need', ''), # 最重要ニーズ (name="most_important_need")
            'proposal_content_value': request.form.get('proposal_content', ''), # 提案内容 (name="proposal_content")
            'consideration_reason_value': request.form.get('consideration_reason', ''), # 検討理由 (name="consideration_reason")
            'lead_date_value': request.form.get("lead_date", "").strip(), # リード獲得日 (name="lead_date")
            'needs_value': request.form.get('needs', ''),         # ニーズ (name="needs")
            'authority_value': request.form.get('authority', ''), # 決裁権 (name="authority")
            'timing_value': request.form.get('timing', ''),       # 導入時期 (name="timing")
            'source_tantosha': request.form.get('source_tantosha', ''), # 引き継ぎ元担当者 (name="source_tantosha")
         }
        
        # print (f"Received form data: {context}") # デバッグ用ログ
        
        session['last_tantosha'] = context['tantosha_value'] # セッションも更新

        handover_id_to_delete = request.form.get('delete_handover_id')
        business_card_file = request.files.get("business_card")
        hearing_seed_files = [f for f in request.files.getlist("hearing_seed") if f and f.filename and f.filename.strip()]

        temp_files_to_delete = []
        business_card_final_path = None
        hearing_seed_final_paths = []
        processing_successful = False
        lead_date = None

        try:
            # 2. バリデーション
            if not context['tantosha_value']: raise ValueError("担当者名が選択されていません。")
            if not context['proposal_plan_value']: raise ValueError("提案プランが選択されていません。")
            if not context['needs_value']: raise ValueError("ニーズが選択されていません。")
            if not context['authority_value']: raise ValueError("決裁権が選択されていません。")
            if not context['timing_value']: raise ValueError("導入時期が選択されていません。")

            # 3. 日付処理
            raw_date = context['lead_date_value']
            if not raw_date:
                today = datetime.now()
                lead_date = f"{today.year}/{today.month}/{today.day}"
            elif re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", raw_date):
                lead_date = raw_date
            else:
                raise ValueError("日付はYYYY/M/D 形式で入力するか、空欄にしてください。")

            # 4. 名刺画像の処理
            if business_card_file and business_card_file.filename:
                filename = secure_filename(business_card_file.filename)
                base, ext = os.path.splitext(filename)
                timestamp = int(time.time() * 1000)
                temp_filepath = os.path.join(UPLOAD_FOLDER, f"{base}_{timestamp}_temp{ext}")
                business_card_final_path = os.path.join(UPLOAD_FOLDER, f"{base}_{timestamp}.jpeg")
                business_card_file.save(temp_filepath)
                temp_files_to_delete.append(temp_filepath)
                convert_to_jpeg(temp_filepath, business_card_final_path)
            else:
                raise ValueError("名刺画像が選択されていません。")

            # 5. ヒアリングシート画像の処理
            for i, file in enumerate(hearing_seed_files):
                filename = secure_filename(file.filename)
                base, ext = os.path.splitext(filename)
                timestamp = int(time.time() * 1000) + i
                temp_filepath = os.path.join(UPLOAD_FOLDER, f"hs_{base}_{timestamp}_temp{ext}")
                final_path = os.path.join(UPLOAD_FOLDER, f"hs_{base}_{timestamp}.jpeg")
                file.save(temp_filepath)
                temp_files_to_delete.append(temp_filepath)
                try:
                    convert_to_jpeg(temp_filepath, final_path)
                    hearing_seed_final_paths.append(final_path)
                except Exception as conv_e:
                    print(f"ヒアリングシート画像 '{filename}' の変換エラー: {conv_e}")

            # 6. main.py の処理関数呼び出しと結果確認
            result_code = -1 # 初期値
            if business_card_final_path:
                business_card_abs_path = os.path.abspath(business_card_final_path)
                hearing_seed_abs_paths = [os.path.abspath(p) for p in hearing_seed_final_paths]
                print("--- Calling main process ---")
                result_code = process_cards(business_card_abs_path, hearing_seed_abs_paths, lead_date, context)
                print(f"--- main process returned: {result_code} ---")
            else:
                 # このケースは名刺必須チェックで防がれるはず
                 raise ValueError("名刺画像の処理に問題が発生しました。")

            # 7. main関数の結果に基づいてステータスを設定
            if result_code == 0: # 正常終了
                processing_successful = True
                context['message'] = "notionデータベースに登録しました。"
                context['success'] = "1"
            elif result_code == 1: # main関数が異常終了コードを返した場合
                processing_successful = False # ★ 失敗フラグを立てる
                context['message'] = "Notionへの登録処理でエラーが発生しました。入力内容や連携設定を確認してください。" # ★ 専用のエラーメッセージ
                context['success'] = "0"
            else: # 予期せぬリターンコード
                processing_successful = False
                context['message'] = f"メイン処理で予期せぬリターンコード ({result_code}) が返されました。"
                context['success'] = "0"
                print(f"Warning: Unexpected return code from process_cards: {result_code}")

        except ValueError as ve:
            processing_successful = False # 失敗フラグ
            context['message'] = str(ve)
            context['success'] = "0"
            print(f"Validation Error: {context['message']}")
        except FileNotFoundError as fnfe:
            processing_successful = False # 失敗フラグ
            context['message'] = f"ファイルの処理中にエラーが発生しました: {fnfe}"
            context['success'] = "0"
            print(f"File Not Found Error: {context['message']}")
        except Exception as e:
            processing_successful = False # 失敗フラグ
            context['message'] = f"アップロード処理中に予期せぬエラーが発生しました。<br><small>詳細: {e}</small>"
            context['success'] = "0"
            print(f"!!! Processing Error: {e} !!!")
            import traceback
            traceback.print_exc()
            
        finally:
            # 後処理: 一時ファイルの削除
            for temp_file in temp_files_to_delete:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        print(f"Deleted temp file: {temp_file}")
                    except OSError as e:
                        print(f"Error deleting temp file {temp_file}: {e}")

        # 8. 最終的な処理分岐 (成功ならリダイレクト、失敗なら再レンダリング)
        if processing_successful:
            # 成功時: 引き継ぎファイル削除
            if handover_id_to_delete:
                 # (ファイル削除ロジック)
                if handover_id_to_delete and '..' not in handover_id_to_delete and '/' not in handover_id_to_delete and '\\' not in handover_id_to_delete:
                    filepath_to_delete = os.path.join(HANDOVER_DIR, f"{handover_id_to_delete}.json")
                    try:
                        if os.path.exists(filepath_to_delete):
                            os.remove(filepath_to_delete)
                            print(f"Deleted handover file: {filepath_to_delete}")
                        else:
                            print(f"Handover file not found for deletion: {filepath_to_delete}")
                    except OSError as e:
                        print(f"Error deleting handover file {filepath_to_delete}: {e}")
                else:
                    print(f"Invalid handover ID format received for deletion: '{handover_id_to_delete}'")
            # 成功時はリダイレクト (PRGパターン)
            return redirect(url_for("index", message=context['message'], success=context['success']))
        
        else:
            # ★★★ 失敗時: 入力値を保持してフォームを再レンダリング ★★★
            # (contextにはフォームの値とエラーメッセージが含まれている)
            return render_template('index.html', **context)

    # --- GETリクエストの処理 ---
    else:
        # GETリクエスト用のコンテキストを初期化
        context = {
            'message': request.args.get("message", ""),
            'success': request.args.get("success", "0"),
            'tantosha_value': session.get('last_tantosha', ''),
            'assignees_list': ASSIGNESS_LIST,
            'proposal_plan_list': PLAN_LIST,
            'persona_options': PERSONA_OPTIONS,
            
            'proposal_plan_value': request.args.get('proposal_plan', ''),
            'current_situation_value': request.args.get('current_situation', ''),
            'problem_value': request.args.get('problem', ''),
            'most_important_need_value': request.args.get('most_important_need', ''),
            'proposal_content_value': request.args.get('proposal_content', ''),
            'consideration_reason_value': request.args.get('consideration_reason', ''),
            'lead_date_value': request.args.get('lead_date', ''),
            'needs_value': request.args.get('needs', ''),
            'authority_value': request.form.get('authority', ''),
            'timing_value': request.form.get('timing', ''),
            'source_tantosha': request.form.get('source_tantosha', ''),
         }
        return render_template('index.html', **context)


# --- 引き継ぎ機能 API エンドポイント (変更なし) ---
@app.route('/api/save_handover', methods=['POST'])
def save_handover():
    
    if not request.is_json: 
        return jsonify({'status': 'error', 'message': 'リクエスト形式が不正です(JSONではありません)'}), 400
    
    data = request.get_json()
    if not data: 
        return jsonify({'status': 'error', 'message': 'データが含まれていません'}), 400
    
    if not data.get('handover_source_tantosha'): 
        return jsonify({'status': 'error', 'message': '担当者が選択されていません'}), 400
    
    handover_id = str(uuid.uuid4())
    data['handover_timestamp'] = datetime.now().isoformat()
    
    filename = f"{handover_id}.json"
    filepath = os.path.join(HANDOVER_DIR, filename)
    
    if os.path.dirname(os.path.abspath(filepath)) != os.path.abspath(HANDOVER_DIR): return jsonify({'status': 'error', 'message': '内部エラーが発生しました'}), 500
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f: 
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print(f"Saved handover data to: {filepath}")
        
        return jsonify({'status': 'success', 'id': handover_id})
    
    except IOError as e: 
        print(f"Error saving handover file {filepath}: {e}"); 
        return jsonify({'status': 'error', 'message': 'データの保存に失敗しました'}), 500
    
    except Exception as e: 
        print(f"Unexpected error saving handover file {filepath}: {e}"); 
        return jsonify({'status': 'error', 'message': '予期せぬエラーが発生しました'}), 500


# --- 引き継ぎデータのリスト取得 API エンドポイント ---
@app.route('/api/list_handovers', methods=['GET'])
def list_handovers():

    handovers = []
    try:
        for filename in os.listdir(HANDOVER_DIR):
            if filename.endswith(".json"):
                try:
                    uuid.UUID(filename[:-5], version=4)
                except ValueError: 
                    continue
                
                filepath = os.path.join(HANDOVER_DIR, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
                    handovers.append({'id': filename[:-5],'source_tantosha': data.get('handover_source_tantosha', '不明'),'timestamp': data.get('handover_timestamp')})
                
                except Exception as e: print(f"Err reading {filename}: {e}")
        handovers.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(handovers)
    
    except FileNotFoundError: return jsonify([])
    except Exception as e: print(f"Error listing handovers: {e}"); return jsonify({'status': 'error', 'message': 'リストの取得に失敗しました'}), 500


# --- 引き継ぎデータの取得 API エンドポイント ---
@app.route('/api/get_handover/<string:handover_id>', methods=['GET'])
def get_handover(handover_id):
    try: 
        uuid.UUID(handover_id, version=4)
    except ValueError:
        return jsonify({'status': 'error', 'message': '無効なID形式です'}), 400
    
    filename = f"{handover_id}.json"
    filepath = os.path.join(HANDOVER_DIR, filename)
    
    if os.path.dirname(os.path.abspath(filepath)) != os.path.abspath(HANDOVER_DIR): 
        abort(400)
        
    if not os.path.exists(filepath): 
        return jsonify({'status': 'error', 'message': '指定された引き継ぎデータが見つかりません'}), 404
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
        return jsonify(data)
    
    except json.JSONDecodeError: 
        return jsonify({'status': 'error', 'message': 'データの形式が不正です'}), 500
    
    except Exception as e: 
        print(f"Error getting handover file {handover_id}: {e}"); 
        return jsonify({'status': 'error', 'message': 'データの取得に失敗しました'}), 500


# --- 引き継ぎデータの削除 API エンドポイント ---
@app.route('/api/delete_handover/<string:handover_id>', methods=['DELETE'])
def delete_handover_api(handover_id):
    """
    指定されたIDの引き継ぎデータ（JSONファイル）を削除するAPIエンドポイント。
    JavaScriptから直接呼び出されることを想定。
    """
    print(f"[API] Received DELETE request for handover ID: {handover_id}") # ログ

    # 1. ID形式 (UUID v4) の検証
    try:
        uuid.UUID(handover_id, version=4)
    except ValueError:
        print(f"[API Error] Invalid UUID format for deletion: {handover_id}")
        return jsonify({'status': 'error', 'message': '無効な引き継ぎID形式です。'}), 400 # Bad Request

    # 2. ファイルパスの構築と安全性の確認
    filename = f"{handover_id}.json"
    filepath = os.path.join(HANDOVER_DIR, filename)

    # ディレクトリトラバーサル防止 (save/get と同じチェック)
    if os.path.dirname(os.path.abspath(filepath)) != os.path.abspath(HANDOVER_DIR):
        print(f"[API Security Error] Path traversal attempt detected for ID: {handover_id}")
        # abort(400) の代わりにJSONレスポンスを返す
        return jsonify({'status': 'error', 'message': '不正な引き継ぎIDです。'}), 400 # Bad Request

    print(f"[API] Attempting to delete file: {filepath}") # ログ

    # 3. ファイルの存在確認と削除処理
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[API] Successfully deleted handover file: {filepath}") # ログ
            # 成功レスポンス
            return jsonify({'status': 'success', 'message': '引き継ぎデータを削除しました。'}), 200
        else:
            # ファイルが見つからない場合
            print(f"[API Warn] Handover file not found for deletion: {filepath}") # ログ
            return jsonify({'status': 'error', 'message': '指定された引き継ぎデータが見つかりません。'}), 404 # Not Found

    except OSError as e:
        # ファイル削除時のOSエラー（例: パーミッション不足）
        print(f"[API Error] OSError deleting file {filepath}: {e}") # エラーログ
        return jsonify({'status': 'error', 'message': f'ファイルの削除に失敗しました: {e.strerror}'}), 500 # Internal Server Error
    except Exception as e:
        # その他の予期せぬエラー
        print(f"[API Error] Unexpected error deleting file {filepath}: {e}") # エラーログ
        import traceback
        traceback.print_exc() # 詳細なトレースバックを出力
        return jsonify({'status': 'error', 'message': '予期せぬエラーが発生し、削除に失敗しました。'}), 500 # Internal Server Error
    
    
# --- サーバー起動 ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ["true", "1", "t"]
    print(f"Starting Flask app on port {port} with debug mode: {debug_mode}")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)