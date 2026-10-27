#!/bin/bash
# Build a macOS 15-targeted Apple Silicon app using Xcode 26.5+ on a Mac.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
python3 port_sequoia.py
xcodebuild -version
DERIVED="${RUNNER_TEMP:-$ROOT/.sequoia-build}/RunCatNeoDerivedData"
mkdir -p "$(dirname "$DERIVED")"
xcodebuild \
  -project RunCatNeo.xcodeproj \
  -scheme RunCatNeo \
  -configuration Release \
  -destination 'generic/platform=macOS' \
  -derivedDataPath "$DERIVED" \
  -skipPackagePluginValidation \
  ARCHS=arm64 \
  ONLY_ACTIVE_ARCH=YES \
  CODE_SIGNING_ALLOWED=NO \
  build
APP="$DERIVED/Build/Products/Release/RunCatNeo.app"
if [[ ! -d "$APP" ]]; then echo "Build did not produce $APP" >&2; exit 1; fi
/usr/bin/codesign --force --deep --sign - "$APP"
/usr/bin/codesign --verify --deep --strict "$APP"
/usr/bin/lipo -info "$APP/Contents/MacOS/RunCatNeo"
/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' "$APP/Contents/Info.plist"
OUTPUT="$ROOT/RunCatNeo-Sequoia-macOS15-arm64.zip"
/usr/bin/ditto -c -k --keepParent "$APP" "$OUTPUT"
/usr/bin/shasum -a 256 "$OUTPUT"
echo "Build complete: $OUTPUT"
