# NotionBizCard

営業支援ツールの名刺管理システム

## 概要

名刺画像とヒアリングシートをアップロードすることで、OCR（GPT-4o Vision）を使って情報を抽出し、Notionデータベースに自動登録するシステムです。また、登録されたデータを基にGmailの下書きを自動生成する機能も提供します。

## 最新更新（2024年12月）

### HTTPS対応
- SSL証明書による暗号化通信をサポート
- 自己署名証明書による開発環境対応
- セキュリティヘッダー（HSTS, XSS Protection等）の実装

### S3画像保存の改善
- スマートフォンで撮影した画像の自動回転修正
- EXIF回転情報に基づく正しい向きでの画像保存
- 画像品質の最適化とリサイズ機能の向上

## 動作確認環境
- OS：macOS Sequoia (version 15.3.1)、windows10 home
- 環境：python 3.12.6

## 環境構築

### 必要な環境
- Python 3.8以上
- OpenAI API Key
- Notion API Token
- Google Gmail API認証情報
- AWS S3アクセス権限（画像保存用）

### pyenv を使用した環境構築
```bash
pip install pyenv==2.5.0
pyenv install 3.12.6
pyenv virtualenv 3.12.6 NotionBizCard
pyenv activate NotionBizCard
pip install --upgrade pip==25.0.1
pip install -r requirement.txt
```

### conda を使用した環境構築
```bash
conda env create -f environment.yml
```

### 必要なpkgのインストール
```Shell
(NotionBizCard) pip install --upgrade pip==25.0.1
(NotionBizCard) pip install -r requirement.txt
```

### 環境の削除
```Shell
(NotionBizCard) pyenv deactivate
pyenv uninstall 3.12.6/envs/NotionBizCard
```

## 使用方法

### Webサーバーの起動

#### HTTP起動（開発・テスト用）
```bash
cd src/notion_sever
./start_http.sh
# または
python sever.py
```

#### HTTPS起動（セキュア通信）
```bash
cd src/notion_sever
./start_https.sh
```

**アクセスURL:**
- HTTP: `http://127.0.0.1:5001`
- HTTPS: `https://127.0.0.1:5001`（自己署名証明書のためブラウザで警告表示）

#### SSL証明書の生成（初回のみ）
```bash
cd src/notion_sever
./generate_ssl_cert.sh
```

### Gmail下書き生成
```bash
cd src/gmail
python main.py
```

## 機能

### 名刺OCR機能
- GPT-4o Visionを使用した名刺画像からの情報抽出
- 会社名、担当者名、部署、役職、電話番号、メールアドレスの自動認識
- 業界・部署・役職の事前定義リストによる分類
- **スマートフォン撮影画像の自動回転修正**

### 画像処理・保存
- **AWS S3への画像アップロード**
- **EXIF回転情報に基づく自動回転修正**
- GPT-4o Vision最適サイズへの自動リサイズ（長辺2048px、短辺768px以下）
- JPEG品質最適化（品質95%）

### Notion連携
- 抽出した情報をNotionデータベースに自動登録
- ペルソナ（BANT）スコアリングによる顧客分類
- リード獲得日、担当者、ステータス管理
- **手入力モード対応**（名刺画像なしでの直接入力）

### Gmail下書き生成
- Notionデータベースの情報を基にした営業メール下書きの自動生成
- Gemini AIによる自然な文章生成
- Gmail APIを通じた下書き保存

### セキュリティ機能
- **HTTPS通信対応**（SSL/TLS暗号化）
- **セキュリティヘッダー実装**（HSTS, XSS Protection, Content Security Policy）
- **引き継ぎ機能**によるチーム間での顧客情報共有

## 設定ファイル

- `config.ini`: APIキー、データベースID、サーバー設定
  - `[HOST]`: 本番環境設定（mocomocoデータベース）
  - `[LOCAL]`: 開発・テスト環境設定
- `src/aws/.env`: AWS S3設定
  - `AWS_ACCESS_KEY_ID`: AWSアクセスキー
  - `AWS_SECRET_ACCESS_KEY`: AWSシークレットキー
  - `S3_BUCKET_NAME`: S3バケット名
  - `AWS_REGION`: AWSリージョン（デフォルト: ap-northeast-1）

### 設定例（config.ini）
```ini
[HOST]
SCP_KEY_PATH = /path/to/ssh/private_key
SERVER = your-server.com
USER = username
UPLOAD_PATH = /home/user/www/img_temp/
UPLOAD_URL = https://your-server.com/img_temp/
GPTAPI_TOKEN = sk-proj-your-openai-api-key
GEMINI_TOKEN = your-gemini-api-key
GEMINI_MODEL = gemini-2.5-pro-preview-03-25
NOTION_API_TOKEN = ntn_your-notion-api-token
DATABASE_ID = your-notion-database-id
NOTION_VERSION = 2022-06-28
DEFAULT_TAG = "DXPO名古屋'25"
```

## アーキテクチャ

システムは2つの主要フェーズに分かれています（feature/separateブランチで分離）：

1. **Notion登録フェーズ** (`src/notion_sever/`):
   - **Flask Webサーバー**（HTTP/HTTPS対応）
   - 名刺/ヒアリングシート画像のアップロード処理
   - **PIL（Python Imaging Library）**による画像処理・回転修正
   - **GPT-4o Vision**を使用したOCR処理
   - **AWS S3**での画像保存・ホスティング
   - **Notion API**によるデータベース登録
   - **バックグラウンド処理**による非同期実行

2. **Gmail生成フェーズ** (`src/gmail/`):
   - Notionデータベースからのデータ取得
   - **Gemini AI**を使用したメール内容生成
   - **Gmail API**を通じた下書き作成

## 技術スタック

- **Backend**: Python 3.12, Flask
- **AI/ML**: OpenAI GPT-4o Vision, Google Gemini
- **Database**: Notion API
- **Cloud Storage**: AWS S3
- **Image Processing**: PIL (Python Imaging Library)
- **Security**: SSL/TLS, セキュリティヘッダー
- **Authentication**: OAuth 2.0 (Gmail API)

## データ入力方法

### 名刺画像がある場合：
1. 担当者を選択
2. 「名刺画像」を選択
3. 名刺画像をアップロード（ファイル選択またはカメラ撮影）
4. ヒアリングシート画像をアップロード（複数可）
5. 営業情報・ヒアリング内容を入力
6. 「処理開始」ボタンをクリック

### 名刺画像がない場合：
1. 担当者を選択
2. 「手入力」を選択
3. 会社名・担当者名等を手動入力
4. その他の項目を入力
5. 「処理開始」ボタンをクリック

## 主要なコンポーネント

### OCR処理（ocr.py）
- GPT-4oを使用した名刺テキスト抽出
- 業界、部署、役職の事前定義リストによる分類
- 構造化JSONでの抽出情報返却

### Notion統合（creteNotionPerties.py）
- 抽出データのNotionデータベースプロパティへのマッピング
- フィールドタイプ変換（title, rich_text, select, multi_select等）の処理
- BANTスコアリングに基づくペルソナ計算

### 画像処理
- アップロード画像のJPEG形式変換
- GPT-4o Vision最適サイズ（512x512）へのリサイズ
- **EXIF回転情報に基づく自動回転修正**
- AWS S3への公開URL用アップロード

### Webインターフェース（sever.py）
- Flaskアプリケーションによるフォーム処理
- ファイルアップロードとバリデーション
- チーム間でのリード情報引き継ぎ機能

## データベーススキーマ

現在のNotionデータベースフィールド：
- 会社名 (title)
- 担当者氏名、部署名、役職名 (rich_text)
- 電話番号 (phone_number)、メール (email)
- リード獲得日、契約開始日 (date)
- 担当、製品、ステータス (multi_select)
- ペルソナ、タグ (select)
- ヒアリングメモ、ボイレコ貸し出し (rich_text)

## ブランチ戦略

- `main`: メイン安定ブランチ
- `develop`: 開発ブランチ
- `feature/separate`: 処理フェーズ分離済みの現在の作業ブランチ
- `feature/aws`: AWS S3統合とHTTPS対応ブランチ