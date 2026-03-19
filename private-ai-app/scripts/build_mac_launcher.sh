#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Private AI Hub"
APP_PATH="$ROOT_DIR/${APP_NAME}.app"
ICON_PNG="$ROOT_DIR/desktop/src-tauri/icons/icon.png"
COMMAND_FILE="$ROOT_DIR/scripts/open_app_local.command"
TMP_DIR="$(mktemp -d)"
APP_EXEC_NAME="private-ai-hub-launcher"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [[ "$(uname)" != "Darwin" ]]; then
  echo "[ERROR] This launcher builder only supports macOS."
  exit 1
fi

if [[ ! -f "$ICON_PNG" ]]; then
  echo "[ERROR] Icon source missing: $ICON_PNG"
  exit 1
fi

if [[ ! -x "$COMMAND_FILE" ]]; then
  echo "[ERROR] Missing executable command launcher: $COMMAND_FILE"
  exit 1
fi

rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS" "$APP_PATH/Contents/Resources"

cat >"$APP_PATH/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>${APP_EXEC_NAME}</string>
  <key>CFBundleIdentifier</key>
  <string>com.privateai.hub.launcher</string>
  <key>CFBundleName</key>
  <string>${APP_NAME}</string>
  <key>CFBundleDisplayName</key>
  <string>${APP_NAME}</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
</dict>
</plist>
EOF

cat >"$APP_PATH/Contents/MacOS/$APP_EXEC_NAME" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/open -a Terminal "$COMMAND_FILE"
EOF
chmod +x "$APP_PATH/Contents/MacOS/$APP_EXEC_NAME"

ICON_ICNS="$TMP_DIR/AppIcon.icns"
ICON_CREATED=0
ICONSET_DIR="$TMP_DIR/icon.iconset"
mkdir -p "$ICONSET_DIR"

sips -z 16 16 "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32 "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64 "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$ICON_PNG" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$ICON_PNG" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null

if command -v iconutil >/dev/null 2>&1 && iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS" >/dev/null 2>&1; then
  ICON_CREATED=1
fi

if [[ "$ICON_CREATED" -eq 0 ]] && command -v python3 >/dev/null 2>&1; then
  if python3 - "$ICON_PNG" "$ICON_ICNS" <<'PY'
from PIL import Image
import sys

src, dst = sys.argv[1], sys.argv[2]
img = Image.open(src).convert("RGBA")
img.save(
    dst,
    format="ICNS",
    sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
)
PY
  then
    ICON_CREATED=1
  fi
fi

if [[ "$ICON_CREATED" -eq 1 ]]; then
  cp "$ICON_ICNS" "$APP_PATH/Contents/Resources/AppIcon.icns"
else
  echo "[WARN] Failed to generate .icns icon. Launcher app will use default icon."
fi

echo "[OK] Launcher created: $APP_PATH"
echo "[INFO] Double-click \"$APP_NAME.app\" to start backend + desktop app."
