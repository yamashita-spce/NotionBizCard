# リードのデータベース自動化ツール

- 展示会などで入手した情報，ヒアリングシートをnotionリードデータベースに保管するための自動化ツール

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

## 使い方
0. 構成ファイルの設定
- 外部閲覧可能なサーバーを準備し、ssh公開鍵認証方式でアクセス可能な状態にする
- config.iniファイルの作成
```Shell
[HOST_WIN]
SCP_KEY_PATH = C:\Users\xxx\.ssh\xxx
SERVER = xxx
USER = xxx
UPLOAD_PATH = /home/user/www/xxx
UPLOAD_URL = https;//xxx
GPTAPI_TOKEN = sk-proj-xxx
NOTION_API_TOKEN = ntn_xxx
DATABASE_ID = xxx
NOTION_VERSION = 2022-06-28
```
- SCP_KEY_PATH: サーバーへの秘密鍵の絶対パス
- SERVER: sshサーバーのドメイン、もしくはIPアドレス
- USER:　sshのユーザー名
- UPLOAD_PATH: 画像をアップロードするサーバーのパス
- UPLOAD_URL: 公開されたURL（この配下に画像がアップロードされます）
- GPTAPI_TOKEN: openAIのAPIキー
- NOTION_API_TOKEN: notionのAPIキー
- DATABASE_ID: notionのデータベースキー
- NOTION_VERSION: notionのバージョン
  
1. Webサーバーを立ち上げる
```Shell
(NotionBizCard) cd src
(NotionBizCard) python web_server.py
```
2. ブラウザから，127.0.0.1:5001 もしくは，ローカルIP:5001でアクセス
3. APIキー，データベースIDを設定の上，画像をアップロードし実行
4. Webサーバーの終了 ctrl+C
