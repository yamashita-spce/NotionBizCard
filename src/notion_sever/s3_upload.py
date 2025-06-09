import os
import sys
import uuid
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "aws", ".env"))

# 親ディレクトリのaws/connection.pyをインポート
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from aws.connection import S3ImageUploader


class NotionBizCardS3Uploader:
    def __init__(self):
        """S3アップローダーを初期化"""
        self.uploader = S3ImageUploader()
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.region = os.getenv('AWS_REGION', 'ap-northeast-1')
    
    def s3_upload_via_key(self, card_path, hearing_paths):
        """
        名刺画像とヒアリングシート画像をS3にアップロード
        
        Args:
            card_path (str): 名刺画像のローカルパス（Noneの場合は手入力モード）
            hearing_paths (list): ヒアリングシート画像のローカルパスのリスト
            
        Returns:
            tuple: (unique_id, base_url)
        """
        try:
            # 新しい処理ディレクトリを作成
            unique_id = self.uploader.create_process_directory("notion_bizcard_processing")
            print(f"[S3] 処理ID: {unique_id}")
            
            # 名刺画像をアップロード（手入力モードの場合はスキップ）
            if card_path and os.path.exists(card_path):
                card_result = self.uploader.upload_card_image(unique_id, card_path)
                if card_result:
                    print(f"[S3] 名刺画像アップロード成功: {os.path.basename(card_path)}")
                else:
                    print(f"[S3] 名刺画像アップロード失敗: {os.path.basename(card_path)}")
            else:
                print("[S3] 名刺画像なし（手入力モード）")
            
            # ヒアリングシート画像をアップロード
            if hearing_paths:
                for hearing_path in hearing_paths:
                    if os.path.exists(hearing_path):
                        hearing_result = self.uploader.upload_add_image(unique_id, hearing_path)
                        if hearing_result:
                            print(f"[S3] ヒアリングシート画像アップロード成功: {os.path.basename(hearing_path)}")
                        else:
                            print(f"[S3] ヒアリングシート画像アップロード失敗: {os.path.basename(hearing_path)}")
                    else:
                        print(f"[S3] ファイルが見つかりません: {hearing_path}")
            else:
                print("[S3] ヒアリングシート画像なし")
            
            # ベースURLを生成
            base_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{unique_id}"
            
            return unique_id, base_url
            
        except Exception as e:
            print(f"[S3] アップロードエラー: {str(e)}")
            raise
    
    def get_card_image_url(self, unique_id, card_filename):
        """
        名刺画像のS3 URLを取得
        
        Args:
            unique_id (str): 処理ID
            card_filename (str): 名刺画像のファイル名
            
        Returns:
            str: S3 URL
        """
        # S3に保存されている実際のファイル名を取得
        try:
            contents = self.uploader.get_process_contents(unique_id)
            card_images = contents['images']['card']
            
            if card_images:
                # 最初のカード画像のURLを返す
                return card_images[0]['url']
            else:
                print(f"[S3] カード画像が見つかりません: {unique_id}")
                return None
                
        except Exception as e:
            print(f"[S3] カード画像URL取得エラー: {str(e)}")
            return None
    
    def get_hearing_image_urls(self, unique_id):
        """
        ヒアリングシート画像のS3 URLリストを取得
        
        Args:
            unique_id (str): 処理ID
            
        Returns:
            list: S3 URLのリスト
        """
        try:
            contents = self.uploader.get_process_contents(unique_id)
            hearing_images = contents['images']['add']
            
            return [img['url'] for img in hearing_images]
            
        except Exception as e:
            print(f"[S3] ヒアリングシート画像URL取得エラー: {str(e)}")
            return []
    
    def delete_remote_folder(self, unique_id):
        """
        S3の処理ディレクトリを削除
        
        Args:
            unique_id (str): 削除する処理ID
        """
        try:
            self.uploader.delete_process_directory(unique_id)
            print(f"[S3] 処理ディレクトリ削除成功: {unique_id}")
            
        except Exception as e:
            print(f"[S3] 処理ディレクトリ削除エラー: {str(e)}")
            raise


# 既存コードとの互換性のための関数
def scp_upload_via_key(card_path, hearing_paths):
    """
    既存のscp_upload_via_key関数の代替
    S3アップロードを実行する
    """
    uploader = NotionBizCardS3Uploader()
    return uploader.s3_upload_via_key(card_path, hearing_paths)


def delete_remote_folder(unique_id):
    """
    既存のdelete_remote_folder関数の代替
    S3の処理ディレクトリを削除する
    """
    uploader = NotionBizCardS3Uploader()
    uploader.delete_remote_folder(unique_id)


# テスト用
if __name__ == "__main__":
    # 使用例
    uploader = NotionBizCardS3Uploader()
    
    # テスト用のダミーファイルパス
    # card_path = "test_card.jpg"
    # hearing_paths = ["test_hearing1.jpg", "test_hearing2.jpg"]
    
    # unique_id, base_url = uploader.s3_upload_via_key(card_path, hearing_paths)
    # print(f"アップロード完了: {unique_id}, {base_url}")
    
    # # 画像URLを取得
    # card_url = uploader.get_card_image_url(unique_id, os.path.basename(card_path))
    # hearing_urls = uploader.get_hearing_image_urls(unique_id)
    
    # print(f"カード画像URL: {card_url}")
    # print(f"ヒアリングシート画像URL: {hearing_urls}")