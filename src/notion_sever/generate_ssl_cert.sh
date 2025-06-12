#!/bin/bash

# SSL証明書生成スクリプト
# 自己署名証明書を生成（開発・テスト用）

echo "SSL証明書を生成しています..."

# ssl ディレクトリを作成
mkdir -p ssl

# 秘密鍵を生成
openssl genrsa -out ssl/private.key 2048

# 証明書署名要求（CSR）を生成
openssl req -new -key ssl/private.key -out ssl/cert.csr -subj "/C=JP/ST=Tokyo/L=Tokyo/O=NotionBizCard/OU=IT/CN=localhost"

# 自己署名証明書を生成（有効期限365日）
openssl x509 -req -days 365 -in ssl/cert.csr -signkey ssl/private.key -out ssl/cert.pem

# 権限設定
chmod 600 ssl/private.key
chmod 644 ssl/cert.pem

echo "SSL証明書の生成が完了しました:"
echo "- 秘密鍵: ssl/private.key"
echo "- 証明書: ssl/cert.pem"
echo ""
echo "注意: これは自己署名証明書です。本番環境では適切なCA署名証明書を使用してください。"