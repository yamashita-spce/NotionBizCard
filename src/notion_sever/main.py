import os
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv

import ocr
import s3_upload
import creteNotionPerties as cnp
# import create_gmail as gm

# 環境変数を読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "aws", ".env"))

# S3設定
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")

def remove_files(business_card_input, hearing_seed_inputs):
    if business_card_input:
        os.remove("./uploads/" + os.path.basename(business_card_input))
    for hearing_seed_input in hearing_seed_inputs:
        os.remove("./uploads/" + os.path.basename(hearing_seed_input))
        

def main(business_card_input, hearing_seed_inputs, lead_date_str, context):
        
        # 入力方法のチェック
        input_method = context.get('input_method', 'image')
        
        if input_method == 'manual':
            # 手入力モード: OCRをスキップして手入力データを使用
            manual_data = context.get('manual_data', {})
            analysis_result = {
                '会社名': manual_data.get('manual_company', ''),
                '部署': manual_data.get('manual_department', ''),
                '役職': manual_data.get('manual_position', ''),
                '担当者氏名': manual_data.get('manual_name', ''),
                'Eメール': manual_data.get('manual_email', ''),
                '電話番号': manual_data.get('manual_phone', '')
            }
            print("[手入力モード] OCRをスキップして手入力データを使用します")
            
            # ヒアリングシートがある場合のみS3アップロード
            if hearing_seed_inputs:
                unique_id, base_url = s3_upload.scp_upload_via_key(None, hearing_seed_inputs)
            else:
                unique_id = None
        else:
            # 名刺画像モード: S3アップロード処理
            # 0) S3に画像をアップロード
            unique_id, base_url = s3_upload.scp_upload_via_key(business_card_input, hearing_seed_inputs)

            # 1) S3のカード画像URLを取得してOCR処理
            s3_uploader = s3_upload.NotionBizCardS3Uploader()
            card_url = s3_uploader.get_card_image_url(unique_id, os.path.basename(business_card_input))
            if card_url:
                analysis_result = ocr.ocr_image_from_url(card_url)
            else:
                print("[Error] S3からカード画像URLを取得できませんでした")
                return 1

        # 2) メール文面の組み立て

        # message, tokens = gm.generate_email_with_gemini(
        #     context,
        #     analysis_result,
        #     exhibition_name="業務改善EXPO"
        # )
        
        # 3) notion に送るためのプロパティを組み立てる
        properties = cnp.build_notion_properties(analysis_result, lead_date_str, context)

        # 4) Notion APIでページ作成
        page_id = cnp.create_notion_page(properties)
        
        # 5) Notion APIで画像ブロック追加（手入力モードではスキップ）
        if input_method == 'manual':
            if unique_id and hearing_seed_inputs:
                # ヒアリングシートのみ追加
                rt = cnp.append_hearing_images_only(page_id, unique_id, hearing_seed_inputs)
            else:
                rt = 0  # 画像なしの場合は成功として扱う
        else:
            # 従来の処理（名刺とヒアリングシート両方）
            rt = cnp.append_image_blocks(page_id, unique_id, business_card_input, hearing_seed_inputs)

        # 6) S3の処理ディレクトリを削除（オプション）
        # 処理完了後にS3のファイルを保持したい場合はコメントアウト
        # if unique_id:
        #     s3_upload.delete_remote_folder(unique_id)
        
        # 7) upload ファイルの削除
        print("upload files remove")
        if input_method == 'image' and business_card_input:
            remove_files(business_card_input, hearing_seed_inputs)
        elif hearing_seed_inputs:
            # 手入力モードでヒアリングシートのみ削除
            for hearing_seed_input in hearing_seed_inputs:
                os.remove("./uploads/" + os.path.basename(hearing_seed_input))
        
        if rt == 1:
            return 1
        else:
            return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <image_folder_path> [lead_date in M/D format, e.g. 2025/3/12]")
    else:
        image_url = sys.argv[1]
        lead_date_input = sys.argv[2] if len(sys.argv) > 2 else None
        add_image_urls = sys.argv[3] 

        main(image_url, add_image_urls, lead_date_input)

