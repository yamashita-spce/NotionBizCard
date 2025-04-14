import configParser
import requests
import configparser
import os
import re


# 共通ヘッダーの設定
headers = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}


def query_database_all_position():
    """
    Notion データベース内の既存ページを全てクエリして取得する
    ただし、役職フィールドが指定のものに一致するデータのみを対象とする
    """
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    all_results = []
    # 指定の役職に一致する条件をORで連結
    payload = {
        "filter": {
            "or": [
                {"property": "役職", "multi_select": {"contains": "部長"}},
                {"property": "役職", "multi_select": {"contains": "本部長"}},
                {"property": "役職", "multi_select": {"contains": "事務部長"}},
                {"property": "役職", "multi_select": {"contains": "課長"}},
                {"property": "役職", "multi_select": {"contains": "役員・理事"}},
                {"property": "役職", "multi_select": {"contains": "代表取締役"}},
                {"property": "役職", "multi_select": {"contains": "マネージャ"}},
                {"property": "役職", "multi_select": {"contains": "副部長"}},
                {"property": "役職", "multi_select": {"contains": "課長代理"}}
            ]
        }
    }

    while True:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # 今回のクエリ結果を蓄積
        all_results.extend(data['results'])
        
        # もし次のページがなければ終了
        if not data.get('has_more'):
            break
        
        # 次のページがある場合は、start_cursor に next_cursor を追加
        payload['start_cursor'] = data.get('next_cursor')
    
    
    return all_results