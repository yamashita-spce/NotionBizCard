# リードのデータベース自動化ツール

展示会などで入手した名刺とヒアリングシートをOCR処理してNotionリードデータベースに自動登録するWebアプリケーション。

## 主な機能
- **名刺OCR処理**: GPT-4oを使用した高精度名刺データ抽出
- **手入力対応**: 名刺画像がない場合の手動データ入力
- **ヒアリングシート処理**: 複数画像対応
- **レスポンシブUI**: PC・スマートフォン両対応
- **Notion自動登録**: リードデータベースへの自動挿入
- **背景処理**: 非同期処理による快適なUX

## 動作確認環境
- OS：macOS Sequoia (version 15.3.1)、windows10 home
- 環境：python 3.12.6

## インストール方法
### pythonのpkg管理は仮想環境を推奨

### pyenv環境の作成
```Shell
pip install pyenv==2.5.0
pyenv install 3.12.6
pyenv virtualenv 3.12.6 NotionBizCard
pyenv activate NotionBizCard
```
## conda環境の作成
```Shell
conda env create -f environment.yml
```

### 必要なpkgのインストール
```Shell
(NotionBizCard) pip install --update pip==25.0.1
(NotionBizCard) pip -r requirement.txt
```

### 環境の削除
```Shell
(NotionBizCard) pyenv deactivate
pyte uninstall 3.12.6/envs/NotionBizCard
```

## 設定ファイル (config.ini)

外部閲覧可能なサーバーを準備し、SSH公開鍵認証方式でアクセス可能な状態にしてください。

### 設定例
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

### 設定項目説明
- **SCP_KEY_PATH**: サーバーへのSSH秘密鍵の絶対パス
- **SERVER**: SSHサーバーのドメインまたはIPアドレス
- **USER**: SSHユーザー名
- **UPLOAD_PATH**: 画像アップロード先サーバーパス
- **UPLOAD_URL**: 公開画像URL（画像がアップロードされるベースURL）
- **GPTAPI_TOKEN**: OpenAI APIキー（OCR処理用）
- **GEMINI_TOKEN**: Google Gemini APIキー（メール生成用）
- **GEMINI_MODEL**: 使用するGeminiモデル名
- **NOTION_API_TOKEN**: Notion APIトークン
- **DATABASE_ID**: NotionデータベースID
- **NOTION_VERSION**: Notion APIバージョン
- **DEFAULT_TAG**: Notionデータベースに登録するデフォルトタグ名（ダブルクォーテーションで囲む）
## 使い方

### 1. Webサーバーの起動
```bash
(NotionBizCard) cd src/notion_sever
(NotionBizCard) python sever.py
```

### 2. Webアプリへのアクセス
ブラウザで以下のURLにアクセス：
- ローカル: http://127.0.0.1:5001
- ネットワーク: http://[ローカルIP]:5001

### 3. データ入力
#### 名刺画像がある場合：
1. 担当者を選択
2. 「名刺画像」を選択
3. 名刺画像をアップロード（ファイル選択またはカメラ撮影）
4. ヒアリングシート画像をアップロード（複数可）
5. 営業情報・ヒアリング内容を入力
6. 「処理開始」ボタンをクリック

#### 名刺画像がない場合：
1. 担当者を選択
2. 「手入力」を選択
3. 会社名・担当者名等を手動入力
4. その他の項目を入力
5. 「処理開始」ボタンをクリック

### 4. サーバー終了
`Ctrl+C` でWebサーバーを停止

## 技術仕様

### 主要技術スタック
- **Backend**: Python 3.12.6, Flask
- **Frontend**: HTML5, Tailwind CSS, JavaScript (ES6+)
- **OCR**: OpenAI GPT-4o
- **Database**: Notion API
- **Image Processing**: PIL (Python Imaging Library)

### レスポンシブデザイン
- **PC**: 2カラムレイアウト、大きなフォーム要素
- **スマートフォン**: 1カラムレイアウト、タッチ操作最適化

### 処理フロー
1. 画像アップロード・フォーム入力
2. OCR処理（名刺画像の場合）
3. 画像の外部サーバーアップロード
4. Notionデータベースへの自動登録
5. 処理完了通知

