import os
import sys
from urllib.parse import urlparse
import configparser

import ocr
import pub_internet
import creteNotionPerties as cnp
import create_gmail as gm

# 環境変数の設定
config = configparser.ConfigParser()
config.read("../config.ini")

#public file sever
UPLOAD_URL = config["HOST"]["UPLOAD_URL"]

def remove_files(business_card_input, hearing_seed_inputs):
    os.remove("./uploads/" + os.path.basename(business_card_input))
    for hearing_seed_input in hearing_seed_inputs:
        os.remove("./uploads/" + os.path.basename(hearing_seed_input))
        

def main(business_card_input, hearing_seed_inputs, lead_date_str, context):
        
        # 0) リモートサーバに画像をアップロード
        unique_id, remote_base = pub_internet.scp_upload_via_key(business_card_input, hearing_seed_inputs)

        # 1) openAIでテキスト抽出
        url = UPLOAD_URL + unique_id + "/card/" + os.path.basename(business_card_input)
        analysis_result = ocr.ocr_image_from_url(url)

        # 2) メール文面の組み立て
        message, tokens = gm.generate_email_with_gemini(
            context,
            analysis_result,
            exhibition_name="業務改善EXPO"
        )
        
        # 3) notion に送るためのプロパティを組み立てる
        properties = cnp.build_notion_properties(analysis_result, lead_date_str, context, message)

        # 4) Notion APIでページ作成
        page_id = cnp.create_notion_page(properties)
        
        # 5) Notion APIで画像ブロック追加
        rt = cnp.append_image_blocks(page_id, unique_id, business_card_input, hearing_seed_inputs)

        # 6) リモートサーバのフォルダを削除
        # pub_internet.delete_remote_folder(unique_id)
        
        # 7) upload ファイルの削除
        print("upload files remove")
        remove_files(business_card_input, hearing_seed_inputs)
        
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

