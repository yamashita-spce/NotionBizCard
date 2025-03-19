import os
import sys
from urllib.parse import urlparse
import configparser

import ocr
import pub_internet
import creteNotionPerties as cnp

# 環境変数の設定
config = configparser.ConfigParser()
config.read("../config.ini")


#public file sever
UPLOAD_URL = config["HOST_WIN"]["UPLOAD_URL"]


def main(business_card_input, hearing_seed_inputs, lead_date_str):
        
        # 0) リモートサーバに画像をアップロード
        unique_id, remote_base = pub_internet.scp_upload_via_key(business_card_input, hearing_seed_inputs)

        # 1) openAIでテキスト抽出
        url = UPLOAD_URL + unique_id + "/card/" + os.path.basename(business_card_input)
        analysis_result = ocr.ocr_image_from_url(url)

        # 2) notion に送るためのプロパティを組み立てる
        properties = cnp.build_notion_properties(analysis_result, lead_date_str)

        # 4) Notion APIでページ作成
        page_id = cnp.create_notion_page(properties)

        # 5) Notion APIで画像ブロック追加
        cnp.append_image_blocks(page_id, unique_id, hearing_seed_inputs)

        # 6) リモートサーバのフォルダを削除
        # pub_internet.delete_remote_folder(unique_id)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <image_folder_path> [lead_date in M/D format, e.g. 2025/3/12]")
    else:
        image_url = sys.argv[1]
        lead_date_input = sys.argv[2] if len(sys.argv) > 2 else None
        add_image_urls = sys.argv[3] 

        main(image_url, add_image_urls, lead_date_input)

