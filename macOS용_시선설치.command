#!/bin/bash
# macOS 공용 설치: 더블클릭 → 바탕화면에 시선.app 생성 (더블클릭 실행 가능)
# Finder 별칭/셸 .app 은 macOS에서 실행이 막히는 경우가 많아,
# AppleScript 앱으로 만들어 어느 Mac에서나 더블클릭되게 함.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
RUN_SRC="$ROOT/dashboard/packaging/macos/run_sisun.sh"
DESKTOP="${HOME}/Desktop"
OUT_APP="$DESKTOP/시선.app"
ICON="$ROOT/dashboard/packaging/icons/sisun.icns"

fail() {
  osascript -e "display alert \"시선 설치\" message \"$1\"" 2>/dev/null || echo "$1" >&2
  exit 1
}

if [ ! -f "$ROOT/dashboard_desktop.py" ]; then
  fail "dashboard_desktop.py 가 없습니다.\n프로젝트 폴더를 통째로 풀었는지 확인하세요."
fi
if [ ! -f "$RUN_SRC" ]; then
  fail "run_sisun.sh 가 없습니다.\ndashboard/packaging/macos/ 를 확인하세요."
fi
if [ ! -f "$ICON" ]; then
  fail "아이콘이 없습니다.\n$ICON"
fi

chmod +x "$RUN_SRC" "$ROOT/macOS용_시선설치.command" 2>/dev/null || true
xattr -cr "$ROOT/macOS용_시선설치.command" "$RUN_SRC" 2>/dev/null || true

# 예전 설치물 제거
rm -rf "$DESKTOP/시선.app" "$DESKTOP/시선" "$DESKTOP/시선.command" 2>/dev/null || true
osascript <<'EOF' 2>/dev/null || true
tell application "Finder"
  try
    delete (every item of desktop whose name is "시선.app" or name is "시선" or name is "시선.command")
  end try
end tell
EOF

# AppleScript 앱: 앱  bundle 안의 실행기만 호출 (외부 .sh 직접 실행은 TCC 에 막힘)
TMP_AS="$(mktemp /tmp/sisun_launch.XXXXXX.applescript)"
cat > "$TMP_AS" <<'EOF'
set appPath to POSIX path of (path to me)
set runSh to appPath & "Contents/Resources/run_sisun.sh"
do shell script "/bin/bash " & quoted form of runSh
EOF

osacompile -o "$OUT_APP" "$TMP_AS" >/dev/null
rm -f "$TMP_AS"

if [ ! -d "$OUT_APP" ]; then
  fail "바탕화면 시선.app 을 만들지 못했습니다."
fi

RES="$OUT_APP/Contents/Resources"
PLIST="$OUT_APP/Contents/Info.plist"
mkdir -p "$RES"

# 프로젝트 루트를 앱 안에 기록 + 실행기 복사 (앱이 자기 Resources 만 실행)
printf '%s\n' "$ROOT" > "$RES/sisun_root"
cp -f "$RUN_SRC" "$RES/run_sisun.sh"
chmod +x "$RES/run_sisun.sh"
xattr -cr "$RES/run_sisun.sh" 2>/dev/null || true

# 아이콘: osacompile 기본 Assets.car 가 커스텀 icns 를 덮음
rm -f "$RES/Assets.car"
cp -f "$ICON" "$RES/applet.icns"
cp -f "$ICON" "$RES/sisun.icns"
/usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile applet" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string applet" "$PLIST" 2>/dev/null || true

# 리소스 변경 후 ad-hoc 서명 (서명 없이 두면 Operation not permitted 126)
rm -rf "$OUT_APP/Contents/_CodeSignature"
codesign --force --deep -s - "$OUT_APP" >/dev/null 2>&1 || true

xattr -cr "$OUT_APP" 2>/dev/null || true
chmod -R u+rwX "$OUT_APP" 2>/dev/null || true
touch "$OUT_APP" "$RES/applet.icns" 2>/dev/null || true
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$OUT_APP" 2>/dev/null || true

osascript -e 'display alert "시선 설치" message "설치가 끝났습니다."'

osascript <<'EOF' >/dev/null 2>&1 || true
tell application "Terminal"
  try
    close front window
  end try
end tell
EOF
exit 0
