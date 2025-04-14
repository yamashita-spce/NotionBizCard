#!/usr/bin/env zsh

export TESSDATA_PREFIX=/opt/homebrew/share/

# 1) .MPOファイルを探してJPEGに変換
for file in ./jpg/*.jpg; do
  # .MPOファイルが存在しない場合はループを飛ばす
  [ -e "$file" ] || continue

  # 拡張子を取り除いたベース名を取得
  base="${file%.*}"
  
  # ImageMagickの convert コマンドを使ってJPEGに変換
  magick convert "$file" "${base}.jpeg"
  
  # 変換が成功したら元の .MPO を削除
  rm "$file"
done


