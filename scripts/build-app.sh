#!/usr/bin/env bash
# 一键构建「人物志」桌面 App(macOS arm64)。
# 产出:desktop/dist/Chronicle-1.0.0-arm64.dmg / .zip(内含人物志.app)
#
# 依赖均已本地安装、不污染系统环境:
#   - fronted_Nuxt/node_modules (Nuxt 3)
#   - backend/.venv (FastAPI + pyinstaller)
#   - desktop/node_modules (electron + electron-builder)
#
# App 图标源文件:backend/local_data/icons/星图_朱砂_圆角.png(自动转成 .icns)
# 注:electron-builder 无开发者证书时跳过签名,故第 5 步补一次正确的 ad-hoc 签名,
#     否则下载后会被 Gatekeeper 误判「已损坏」。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONT="$ROOT/fronted_Nuxt"
BACKEND="$ROOT/backend"
DESKTOP="$ROOT/desktop"
UV="${UV:-/opt/homebrew/bin/uv}"

echo "==> 1/5 构建前端静态资源 (nuxi generate)"
( cd "$FRONT" && npx nuxi generate )

echo "==> 2/5 打包后端 (PyInstaller --onedir)"
# 确保 pyinstaller 已安装
"$BACKEND/.venv/bin/python" -c "import PyInstaller" 2>/dev/null || \
  "$UV" pip install --python "$BACKEND/.venv/bin/python" pyinstaller
( cd "$BACKEND" && \
  .venv/bin/python -m PyInstaller \
    --onedir \
    --name chronicle-backend \
    --distpath "$DESKTOP/build" \
    --workpath "$BACKEND/build/pyinstaller" \
    --specpath "$BACKEND/build/pyinstaller" \
    --add-data "$FRONT/.output/public:frontend" \
    --add-data "$BACKEND/local_data/avatars:avatars" \
    --noconfirm \
    run.py )

echo "==> 3/5 生成 App 图标 (.icns)"
ICON_PNG="$BACKEND/local_data/icons/星图_朱砂_圆角.png"
ICONSET="$DESKTOP/build/icon.iconset"
rm -rf "$ICONSET" && mkdir -p "$ICONSET"
for spec in \
  "16:icon_16x16.png" "32:icon_16x16@2x.png" \
  "32:icon_32x32.png" "64:icon_32x32@2x.png" \
  "128:icon_128x128.png" "256:icon_128x128@2x.png" \
  "256:icon_256x256.png" "512:icon_256x256@2x.png" \
  "512:icon_512x512.png" "1024:icon_512x512@2x.png"; do
  size="${spec%%:*}"; name="${spec##*:}"
  sips -z "$size" "$size" "$ICON_PNG" --out "$ICONSET/$name" >/dev/null 2>&1
done
iconutil -c icns "$ICONSET" -o "$DESKTOP/build/icon.icns"

echo "==> 4/5 打包 Electron App (electron-builder)"
( cd "$DESKTOP" && \
  [ -d node_modules ] || npm install
  npx electron-builder )

echo "==> 5/5 补 ad-hoc 签名并重做 DMG/zip"
# electron-builder 没有开发者证书时会跳过签名,App 只剩链接器的残缺签名,
# 下载后被 Gatekeeper 判「已损坏」。这里重新密封签名,再重做安装包。
APP="$DESKTOP/dist/mac-arm64/人物志.app"
VERSION="$(node -p "require('$DESKTOP/package.json').version")"
codesign --force --deep --sign - "$APP"
STAGE="$(mktemp -d)"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$DESKTOP/dist"/Chronicle-*.dmg "$DESKTOP/dist"/Chronicle-*.zip "$DESKTOP/dist"/Chronicle-*.blockmap
hdiutil create -volname "人物志" -srcfolder "$STAGE" -ov -format UDZO \
  "$DESKTOP/dist/Chronicle-${VERSION}-arm64.dmg" >/dev/null
( cd "$STAGE" && ditto -c -k --keepParent "人物志.app" \
  "$DESKTOP/dist/Chronicle-${VERSION}-arm64.zip" )
rm -rf "$STAGE"

echo "完成!产物在 $DESKTOP/dist/"
