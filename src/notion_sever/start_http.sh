#!/bin/bash

# HTTP対応Flask起動スクリプト

echo "🌐 NotionBizCard HTTP サーバーを起動します"

# 環境変数を設定
export USE_HTTPS=False
export PORT=5001

# Flaskサーバーを起動
echo "🚀 HTTP対応Flaskサーバーを起動しています..."
echo "アクセスURL: http://[パブリックIP]:5001"
echo ""

python3 sever.py