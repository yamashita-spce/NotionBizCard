from get_notion import query_database_all_position
import gmail_api
import create_gmail 

def main():
    # notionデータベースからgmailの下書きを作成するスクリプト
    
    # notionデータベースの取得
    database = query_database_all_position()
    
    # gamil文の作成
    input_json = create_gmail.generate_email_with_gemini(database, exhibition_name="[展示会名]")
    
    # Gmail APIを使用してメールの下書きを作成
    input_json, token = gmail_api.push_gmail(input_json, CONFIG)
    
    return 0


if __name__ == "__main__":
    main()
    