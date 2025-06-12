#!/usr/bin/env python3
"""
S3画像一括回転ツール

S3バケット内の全ての画像を右に90度回転させるスクリプト
既存の画像が全て横向きになっている問題を修正するためのツール

使用方法:
    python s3_image_rotator.py --bucket your-bucket-name [--dry-run] [--prefix path/]

要件:
    - boto3
    - Pillow (PIL)
    - python-dotenv
"""

import boto3
import os
import sys
import argparse
import io
import logging
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), "src", "aws", ".env"))

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f's3_rotation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class S3ImageRotator:
    def __init__(self, bucket_name, aws_access_key_id=None, aws_secret_access_key=None, region='ap-northeast-1'):
        """
        S3画像回転ツールを初期化
        
        Args:
            bucket_name (str): S3バケット名
            aws_access_key_id (str): AWSアクセスキー（Noneの場合は環境変数から取得）
            aws_secret_access_key (str): AWSシークレットキー（Noneの場合は環境変数から取得）
            region (str): AWSリージョン
        """
        self.bucket_name = bucket_name
        self.region = region
        
        # AWS認証情報の設定
        if aws_access_key_id and aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region
            )
        else:
            # 環境変数から取得
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=region
            )
        
        # サポートする画像形式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        
        # 統計情報
        self.stats = {
            'total_files': 0,
            'image_files': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def list_all_objects(self, prefix=''):
        """
        S3バケット内の全オブジェクトを取得
        
        Args:
            prefix (str): フィルタ用のプレフィックス
            
        Returns:
            list: S3オブジェクトのリスト
        """
        logger.info(f"S3バケット '{self.bucket_name}' からオブジェクト一覧を取得中...")
        
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            for page in page_iterator:
                if 'Contents' in page:
                    objects.extend(page['Contents'])
            
            logger.info(f"合計 {len(objects)} 個のオブジェクトを発見")
            self.stats['total_files'] = len(objects)
            
            return objects
            
        except Exception as e:
            logger.error(f"オブジェクト一覧取得エラー: {str(e)}")
            raise
    
    def is_image_file(self, key):
        """
        ファイルが画像かどうかを判定
        
        Args:
            key (str): S3オブジェクトキー
            
        Returns:
            bool: 画像ファイルかどうか
        """
        _, ext = os.path.splitext(key.lower())
        return ext in self.supported_formats
    
    def download_image(self, key):
        """
        S3から画像をダウンロード
        
        Args:
            key (str): S3オブジェクトキー
            
        Returns:
            tuple: (PIL.Image, メタデータ)
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            
            # メタデータを保存
            metadata = {
                'content_type': response.get('ContentType', 'image/jpeg'),
                'user_metadata': response.get('Metadata', {})
            }
            
            # 画像データを読み込み
            image_data = response['Body'].read()
            image = Image.open(io.BytesIO(image_data))
            
            logger.debug(f"画像ダウンロード成功: {key} ({image.size[0]}x{image.size[1]})")
            
            return image, metadata
            
        except Exception as e:
            logger.error(f"画像ダウンロードエラー {key}: {str(e)}")
            raise
    
    def rotate_image(self, image):
        """
        画像を右に90度回転
        
        Args:
            image (PIL.Image): 元の画像
            
        Returns:
            PIL.Image: 回転後の画像
        """
        try:
            # 右に90度回転（270度反時計回り）
            rotated = image.rotate(-90, expand=True)
            logger.debug(f"画像回転完了: {image.size} -> {rotated.size}")
            return rotated
            
        except Exception as e:
            logger.error(f"画像回転エラー: {str(e)}")
            raise
    
    def upload_image(self, image, key, metadata):
        """
        回転した画像をS3にアップロード
        
        Args:
            image (PIL.Image): 回転後の画像
            key (str): S3オブジェクトキー
            metadata (dict): メタデータ
        """
        try:
            # 画像をバイトストリームに変換
            buffer = io.BytesIO()
            
            # 形式を決定
            if metadata['content_type'] == 'image/png':
                image.save(buffer, format='PNG', optimize=True)
            else:
                # JPEGとして保存（品質95%）
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                image.save(buffer, format='JPEG', quality=95, optimize=True)
                metadata['content_type'] = 'image/jpeg'
            
            buffer.seek(0)
            
            # S3にアップロード
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=buffer.getvalue(),
                ContentType=metadata['content_type'],
                Metadata=metadata['user_metadata']
            )
            
            logger.debug(f"画像アップロード成功: {key}")
            
        except Exception as e:
            logger.error(f"画像アップロードエラー {key}: {str(e)}")
            raise
    
    def create_backup_key(self, original_key):
        """
        バックアップ用のキーを生成
        
        Args:
            original_key (str): 元のオブジェクトキー
            
        Returns:
            str: バックアップキー
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path_parts = original_key.split('/')
        filename = path_parts[-1]
        directory = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ''
        
        name, ext = os.path.splitext(filename)
        backup_filename = f"{name}_backup_{timestamp}{ext}"
        
        if directory:
            return f"{directory}/backup/{backup_filename}"
        else:
            return f"backup/{backup_filename}"
    
    def backup_original(self, key):
        """
        元の画像をバックアップ
        
        Args:
            key (str): 元のオブジェクトキー
        """
        try:
            backup_key = self.create_backup_key(key)
            
            # コピー実行
            copy_source = {'Bucket': self.bucket_name, 'Key': key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=backup_key
            )
            
            logger.debug(f"バックアップ作成: {key} -> {backup_key}")
            
        except Exception as e:
            logger.warning(f"バックアップ作成失敗 {key}: {str(e)}")
    
    def process_single_image(self, key, create_backup=True, dry_run=False):
        """
        単一の画像を処理
        
        Args:
            key (str): S3オブジェクトキー
            create_backup (bool): バックアップを作成するか
            dry_run (bool): ドライランモード
            
        Returns:
            bool: 処理成功かどうか
        """
        try:
            logger.info(f"処理中: {key}")
            
            if dry_run:
                logger.info(f"[DRY RUN] {key} を右に90度回転します")
                self.stats['processed'] += 1
                return True
            
            # バックアップ作成
            if create_backup:
                self.backup_original(key)
            
            # 画像ダウンロード
            image, metadata = self.download_image(key)
            
            # 画像回転
            rotated_image = self.rotate_image(image)
            
            # アップロード
            self.upload_image(rotated_image, key, metadata)
            
            self.stats['processed'] += 1
            logger.info(f"処理完了: {key}")
            
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"処理失敗 {key}: {str(e)}")
            return False
    
    def rotate_all_images(self, prefix='', create_backup=True, dry_run=False):
        """
        バケット内の全画像を回転
        
        Args:
            prefix (str): フィルタ用のプレフィックス
            create_backup (bool): バックアップを作成するか
            dry_run (bool): ドライランモード
        """
        logger.info("="*60)
        logger.info("S3画像一括回転処理を開始")
        logger.info(f"バケット: {self.bucket_name}")
        logger.info(f"プレフィックス: {prefix or '(なし)'}")
        logger.info(f"バックアップ作成: {create_backup}")
        logger.info(f"ドライランモード: {dry_run}")
        logger.info("="*60)
        
        # オブジェクト一覧取得
        objects = self.list_all_objects(prefix)
        
        if not objects:
            logger.info("処理対象の画像が見つかりませんでした")
            return
        
        # 画像ファイルをフィルタリング
        image_objects = [obj for obj in objects if self.is_image_file(obj['Key'])]
        self.stats['image_files'] = len(image_objects)
        
        logger.info(f"画像ファイル: {len(image_objects)} 個")
        
        if not image_objects:
            logger.info("処理対象の画像ファイルが見つかりませんでした")
            return
        
        # 処理実行
        for i, obj in enumerate(image_objects, 1):
            key = obj['Key']
            logger.info(f"[{i}/{len(image_objects)}] 処理中...")
            
            success = self.process_single_image(key, create_backup, dry_run)
            
            if not success:
                self.stats['skipped'] += 1
        
        # 結果レポート
        self.print_summary()
    
    def print_summary(self):
        """処理結果のサマリーを表示"""
        logger.info("="*60)
        logger.info("処理完了サマリー")
        logger.info("="*60)
        logger.info(f"総ファイル数: {self.stats['total_files']}")
        logger.info(f"画像ファイル数: {self.stats['image_files']}")
        logger.info(f"処理成功: {self.stats['processed']}")
        logger.info(f"スキップ: {self.stats['skipped']}")
        logger.info(f"エラー: {self.stats['errors']}")
        logger.info("="*60)


def main():
    parser = argparse.ArgumentParser(description='S3画像一括回転ツール')
    parser.add_argument('--bucket', required=True, help='S3バケット名')
    parser.add_argument('--prefix', default='', help='フィルタ用プレフィックス（例: images/）')
    parser.add_argument('--no-backup', action='store_true', help='バックアップを作成しない')
    parser.add_argument('--dry-run', action='store_true', help='実際には実行せず、処理内容のみ表示')
    parser.add_argument('--aws-access-key-id', help='AWSアクセスキー（環境変数優先）')
    parser.add_argument('--aws-secret-access-key', help='AWSシークレットキー（環境変数優先）')
    parser.add_argument('--region', default='ap-northeast-1', help='AWSリージョン')
    
    args = parser.parse_args()
    
    # 確認プロンプト
    if not args.dry_run:
        print("⚠️  警告: この操作はS3バケット内の全ての画像を変更します。")
        print(f"バケット: {args.bucket}")
        print(f"プレフィックス: {args.prefix or '(全ファイル)'}")
        print(f"バックアップ作成: {'いいえ' if args.no_backup else 'はい'}")
        print()
        
        confirm = input("続行しますか？ (yes/no): ").lower().strip()
        if confirm not in ['yes', 'y']:
            print("処理をキャンセルしました。")
            sys.exit(0)
    
    try:
        # S3ImageRotatorのインスタンスを作成
        rotator = S3ImageRotator(
            bucket_name=args.bucket,
            aws_access_key_id=args.aws_access_key_id,
            aws_secret_access_key=args.aws_secret_access_key,
            region=args.region
        )
        
        # 回転処理実行
        rotator.rotate_all_images(
            prefix=args.prefix,
            create_backup=not args.no_backup,
            dry_run=args.dry_run
        )
        
    except KeyboardInterrupt:
        logger.info("処理が中断されました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()