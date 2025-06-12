#!/bin/bash

# HTTPS対応Flask起動スクリプト

echo "🔐 NotionBizCard HTTPS サーバーを起動します"

# 環境変数を設定
export USE_HTTPS=True
export PORT=5001

# SSL証明書の存在確認
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/private.key" ]; then
    echo "❌ SSL証明書が見つかりません"
    echo "SSL証明書を生成しますか？ (y/n)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "🔧 SSL証明書を生成しています..."
        chmod +x generate_ssl_cert.sh
        ./generate_ssl_cert.sh
        
        if [ $? -eq 0 ]; then
            echo "✅ SSL証明書の生成が完了しました"
        else
            echo "❌ SSL証明書の生成に失敗しました"
            exit 1
        fi
    else
        echo "HTTPS起動をキャンセルしました"
        exit 1
    fi
fi

# ポート5001がHTTPSで利用可能か確認（セキュリティグループ設定）
echo "⚠️  セキュリティグループでポート5001のHTTPSアクセスが許可されていることを確認してください"
echo ""

# Flaskサーバーを起動
echo "🚀 HTTPS対応Flaskサーバーを起動しています..."
echo "アクセスURL: https://[パブリックIP]:5001"
echo "⚠️  自己署名証明書のため、ブラウザで警告が表示されます"
echo ""

python3 sever.py