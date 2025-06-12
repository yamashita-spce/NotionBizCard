#!/bin/bash

# 本番環境用 Nginx + Let's Encrypt セットアップスクリプト
# 使用前にドメイン名を設定してください

DOMAIN="your-domain.com"  # ここを実際のドメイン名に変更
EMAIL="your-email@example.com"  # ここを実際のメールアドレスに変更

echo "🚀 Nginx + Let's Encrypt HTTPS セットアップを開始します"
echo "ドメイン: $DOMAIN"
echo "メール: $EMAIL"
echo ""

# Nginxをインストール
echo "📦 Nginxをインストールしています..."
sudo apt update
sudo apt install -y nginx

# Certbotをインストール
echo "📦 Certbotをインストールしています..."
sudo apt install -y certbot python3-certbot-nginx

# Nginx設定ファイルを作成
echo "⚙️  Nginx設定ファイルを作成しています..."
sudo tee /etc/nginx/sites-available/notionbizcard << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Increase timeout for file uploads
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # Static files (if any)
    location /static/ {
        alias /path/to/your/static/files/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
EOF

# サイトを有効化
echo "🔗 サイトを有効化しています..."
sudo ln -sf /etc/nginx/sites-available/notionbizcard /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx設定をテスト
echo "🧪 Nginx設定をテストしています..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx設定が正常です"
    
    # Nginxを再起動
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    echo "🔐 Let's Encrypt SSL証明書を取得しています..."
    echo "注意: ドメインが正しくこのサーバーを指している必要があります"
    
    # SSL証明書を取得
    sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive
    
    if [ $? -eq 0 ]; then
        echo "🎉 HTTPS設定が完了しました！"
        echo ""
        echo "アクセスURL: https://$DOMAIN"
        echo ""
        echo "📝 自動更新を設定するには:"
        echo "sudo crontab -e"
        echo "以下の行を追加:"
        echo "0 12 * * * /usr/bin/certbot renew --quiet"
        
        # Flask設定をHTTPに戻す（Nginxがプロキシするため）
        echo ""
        echo "⚙️  Flask設定を変更してください:"
        echo "export USE_HTTPS=False"
        echo "export PORT=5001"
        
    else
        echo "❌ SSL証明書の取得に失敗しました"
        echo "ドメインの設定を確認してください"
    fi
else
    echo "❌ Nginx設定にエラーがあります"
fi