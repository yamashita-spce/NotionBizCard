# リードのデータベース自動化ツール

- 展示会などで入手した情報，ヒアリングシートをnotionリードデータベースに保管するための自動化ツール

## 動作確認環境
- アーキテクチャ：arm64 
- OS：macOS Sequoia (version 15.3.1)
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
0. サーバーのssh　公開鍵認証を設定
- config.iniファイルのKEY_PATHを公開鍵のパスに変更
- config.iniでapiキー，データベースIDなどの変更が可能
1. Webサーバーを立ち上げる
```Shell
(NotionBizCard) python server.py
```
2. ブラウザから，127.0.0.1:5001 もしくは，ローカルIP:5001でアクセス
3. APIキー，データベースIDを設定の上，画像をアップロードし実行
4. Webサーバーの終了 ctrl+C
5. gmailの下書きを作成


# 各種ファイル構成
- feature/separete　では，notion登録と，gmail作成でフェーズを分ける. 一気にやると動作が重い．



