import boto3
import os
from dotenv import load_dotenv
from datetime import datetime
import mimetypes
import uuid
import json

# 環境変数を読み込み
load_dotenv()

class S3ImageUploader:
    def __init__(self):
        """S3クライアントを初期化"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'ap-northeast-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.region = os.getenv('AWS_REGION', 'ap-northeast-1')
        
    def create_process_directory(self, process_name=None):
        """
        処理用のUUIDディレクトリを作成
        
        Args:
            process_name (str): 処理の名前（オプション）
            
        Returns:
            str: 生成されたUUID
        """
        process_uuid = str(uuid.uuid4())
        
        # メタデータを作成
        metadata = {
            'uuid': process_uuid,
            'process_name': process_name or 'unnamed_process',
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        # メタデータをS3に保存
        metadata_key = f"{process_uuid}/metadata.json"
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=metadata_key,
            Body=json.dumps(metadata, ensure_ascii=False, indent=2),
            ContentType='application/json'
        )
        
        print(f"処理ディレクトリを作成しました: {process_uuid}")
        print(f"処理名: {process_name or 'unnamed_process'}")
        
        return process_uuid
    
    def upload_to_process(self, process_uuid, file_path, subfolder='images'):
        """
        特定の処理ディレクトリに画像をアップロード
        
        Args:
            process_uuid (str): 処理のUUID
            file_path (str): アップロードするファイルのローカルパス
            subfolder (str): サブフォルダ名（images, data, etc）
            
        Returns:
            dict: アップロード結果の詳細情報
        """
        try:
            # ファイルが存在するか確認
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
            
            # ファイル名を生成
            file_name = os.path.basename(file_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(file_name)
            
            # S3キーを生成（UUID/subfolder/filename_timestamp.ext）
            s3_key = f"{process_uuid}/{subfolder}/{name}_{timestamp}{ext}"
            
            # MIMEタイプを推測
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            # ファイルサイズを取得
            file_size = os.path.getsize(file_path)
            
            # S3にアップロード（ACLを削除）
            with open(file_path, 'rb') as file:
                self.s3_client.upload_fileobj(
                    file,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'Metadata': {
                            'process-uuid': process_uuid,
                            'original-filename': file_name,
                            'upload-timestamp': timestamp
                        }
                    }
                )
            
            # 公開URLを生成
            public_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            result = {
                'success': True,
                'file_name': file_name,
                's3_key': s3_key,
                'public_url': public_url,
                'content_type': content_type,
                'file_size': file_size,
                'process_uuid': process_uuid,
                'uploaded_at': datetime.now().isoformat()
            }
            
            print(f"アップロード成功: {file_name}")
            print(f"保存先: {s3_key}")
            print(f"公開URL: {public_url}")
            
            return result
            
        except Exception as e:
            print(f"アップロードエラー: {str(e)}")
            return {
                'success': False,
                'file_name': os.path.basename(file_path),
                'error': str(e)
            }
    
    def upload_card_image(self, process_uuid, file_path):
        """
        カード画像をimages/card/ディレクトリにアップロード
        
        Args:
            process_uuid (str): 処理のUUID
            file_path (str): アップロードする画像ファイルのパス
            
        Returns:
            str: アップロードされた画像のS3パス（成功時）、None（失敗時）
        """
        result = self.upload_to_process(process_uuid, file_path, 'images/card')
        if result['success']:
            return result['s3_key']
        else:
            print(f"カード画像のアップロードに失敗: {result['error']}")
            return None
    
    def upload_add_image(self, process_uuid, file_path):
        """
        追加画像をimages/add/ディレクトリにアップロード
        
        Args:
            process_uuid (str): 処理のUUID
            file_path (str): アップロードする画像ファイルのパス
            
        Returns:
            str: アップロードされた画像のS3パス（成功時）、None（失敗時）
        """
        result = self.upload_to_process(process_uuid, file_path, 'images/add')
        if result['success']:
            return result['s3_key']
        else:
            print(f"追加画像のアップロードに失敗: {result['error']}")
            return None
    
    def upload_multiple_card_images(self, process_uuid, file_paths):
        """
        複数のカード画像を一括アップロード
        
        Args:
            process_uuid (str): 処理のUUID
            file_paths (list): アップロードする画像ファイルパスのリスト
            
        Returns:
            list: アップロードされた画像のS3パスのリスト
        """
        uploaded_paths = []
        for file_path in file_paths:
            s3_path = self.upload_card_image(process_uuid, file_path)
            if s3_path:
                uploaded_paths.append(s3_path)
        return uploaded_paths
    
    def upload_multiple_add_images(self, process_uuid, file_paths):
        """
        複数の追加画像を一括アップロード
        
        Args:
            process_uuid (str): 処理のUUID
            file_paths (list): アップロードする画像ファイルパスのリスト
            
        Returns:
            list: アップロードされた画像のS3パスのリスト
        """
        uploaded_paths = []
        for file_path in file_paths:
            s3_path = self.upload_add_image(process_uuid, file_path)
            if s3_path:
                uploaded_paths.append(s3_path)
        return uploaded_paths
    
    def upload_multiple_to_process(self, process_uuid, file_paths, subfolder='images'):
        """
        特定の処理ディレクトリに複数ファイルを一括アップロード
        
        Args:
            process_uuid (str): 処理のUUID
            file_paths (list): アップロードするファイルパスのリスト
            subfolder (str): サブフォルダ名
            
        Returns:
            dict: アップロード結果のサマリー
        """
        results = {
            'process_uuid': process_uuid,
            'total_files': len(file_paths),
            'successful_uploads': 0,
            'failed_uploads': 0,
            'files': []
        }
        
        for file_path in file_paths:
            result = self.upload_to_process(process_uuid, file_path, subfolder)
            results['files'].append(result)
            
            if result['success']:
                results['successful_uploads'] += 1
            else:
                results['failed_uploads'] += 1
        
        # サマリーをS3に保存
        self._save_upload_summary(process_uuid, results)
        
        return results
    
    def _save_upload_summary(self, process_uuid, results):
        """アップロード結果のサマリーをS3に保存"""
        summary_key = f"{process_uuid}/upload_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=summary_key,
            Body=json.dumps(results, ensure_ascii=False, indent=2),
            ContentType='application/json'
        )
    
    def get_process_contents(self, process_uuid):
        """
        特定の処理ディレクトリの内容を取得
        
        Args:
            process_uuid (str): 処理のUUID
            
        Returns:
            dict: ディレクトリ内のファイル情報
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{process_uuid}/"
            )
            
            contents = {
                'process_uuid': process_uuid,
                'metadata': None,
                'images': {
                    'card': [],
                    'add': [],
                    'other': []
                },
                'data': [],
                'other': []
            }
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    file_info = {
                        'key': key,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'url': f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
                    }
                    
                    # ファイルを分類
                    if key.endswith('metadata.json'):
                        # メタデータを読み込み
                        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                        contents['metadata'] = json.loads(response['Body'].read())
                    elif '/images/card/' in key:
                        contents['images']['card'].append(file_info)
                    elif '/images/add/' in key:
                        contents['images']['add'].append(file_info)
                    elif '/images/' in key:
                        contents['images']['other'].append(file_info)
                    elif '/data/' in key:
                        contents['data'].append(file_info)
                    else:
                        contents['other'].append(file_info)
            
            return contents
            
        except Exception as e:
            print(f"取得エラー: {str(e)}")
            raise
    
    def get_card_images(self, process_uuid):
        """
        特定の処理のカード画像一覧を取得
        
        Args:
            process_uuid (str): 処理のUUID
            
        Returns:
            list: カード画像のS3パスのリスト
        """
        contents = self.get_process_contents(process_uuid)
        return [img['key'] for img in contents['images']['card']]
    
    def get_add_images(self, process_uuid):
        """
        特定の処理の追加画像一覧を取得
        
        Args:
            process_uuid (str): 処理のUUID
            
        Returns:
            list: 追加画像のS3パスのリスト
        """
        contents = self.get_process_contents(process_uuid)
        return [img['key'] for img in contents['images']['add']]
    
    def delete_process_directory(self, process_uuid):
        """
        処理ディレクトリ全体を削除
        
        Args:
            process_uuid (str): 削除する処理のUUID
        """
        try:
            # ディレクトリ内の全オブジェクトを取得
            objects_to_delete = []
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{process_uuid}/"
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
                
                # バッチ削除
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
                
                print(f"処理ディレクトリを削除しました: {process_uuid}")
                print(f"削除されたファイル数: {len(objects_to_delete)}")
            else:
                print(f"削除対象が見つかりません: {process_uuid}")
                
        except Exception as e:
            print(f"削除エラー: {str(e)}")
            raise
    
    def list_all_processes(self):
        """
        すべての処理ディレクトリの一覧を取得
        
        Returns:
            list: 処理情報のリスト
        """
        try:
            # ルートレベルのディレクトリを取得
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Delimiter='/'
            )
            
            processes = []
            
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    process_uuid = prefix['Prefix'].rstrip('/')
                    
                    # メタデータを取得
                    try:
                        metadata_response = self.s3_client.get_object(
                            Bucket=self.bucket_name,
                            Key=f"{process_uuid}/metadata.json"
                        )
                        metadata = json.loads(metadata_response['Body'].read())
                        processes.append(metadata)
                    except:
                        # メタデータがない場合は基本情報のみ
                        processes.append({
                            'uuid': process_uuid,
                            'process_name': 'unknown',
                            'created_at': 'unknown'
                        })
            
            return processes
            
        except Exception as e:
            print(f"一覧取得エラー: {str(e)}")
            raise


# 使用例
if __name__ == "__main__":
    # アップローダーのインスタンスを作成
    uploader = S3ImageUploader()
    
    # 新しい処理を開始（UUIDディレクトリを作成）
    process_uuid = uploader.create_process_directory("画像認識処理_2024")
    
    # カード画像をアップロード
    # card_path = uploader.upload_card_image(
    #     process_uuid=process_uuid,
    #     file_path="path/to/card_image.jpg"
    # )
    # print(f"カード画像のパス: {card_path}")
    
    # 追加画像をアップロード
    # add_path = uploader.upload_add_image(
    #     process_uuid=process_uuid,
    #     file_path="path/to/additional_image.jpg"
    # )
    # print(f"追加画像のパス: {add_path}")
    
    # 複数のカード画像を一括アップロード
    # card_files = ["card1.jpg", "card2.jpg", "card3.jpg"]
    # card_paths = uploader.upload_multiple_card_images(
    #     process_uuid=process_uuid,
    #     file_paths=card_files
    # )
    # print(f"カード画像のパス一覧: {card_paths}")
    
    # 複数の追加画像を一括アップロード
    # add_files = ["add1.jpg", "add2.jpg"]
    # add_paths = uploader.upload_multiple_add_images(
    #     process_uuid=process_uuid,
    #     file_paths=add_files
    # )
    # print(f"追加画像のパス一覧: {add_paths}")
    
    # データファイルもアップロード可能
    # data_result = uploader.upload_to_process(
    #     process_uuid=process_uuid,
    #     file_path="data.json",
    #     subfolder="data"
    # )
    
    # 処理ディレクトリの内容を確認
    # contents = uploader.get_process_contents(process_uuid)
    # print(json.dumps(contents, indent=2, ensure_ascii=False))
    
    # カード画像のパス一覧を取得
    # card_images = uploader.get_card_images(process_uuid)
    # print(f"カード画像: {card_images}")
    
    # 追加画像のパス一覧を取得
    # add_images = uploader.get_add_images(process_uuid)
    # print(f"追加画像: {add_images}")
    
    # すべての処理の一覧を取得
    # all_processes = uploader.list_all_processes()
    # for process in all_processes:
    #     print(f"UUID: {process['uuid']}, 名前: {process['process_name']}")