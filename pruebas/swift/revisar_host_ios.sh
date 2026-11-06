#!/usr/bin/env bash
# La pieza «host-ios» en un Mac con Xcode: revisa los tipos con el SDK del iPhone (Swift no compila aquí en Linux).
#   bash pruebas/swift/revisar_host_ios.sh
set -euo pipefail
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
xcrun --sdk iphoneos swiftc -typecheck -swift-version 5 -sdk "$SDK" -target arm64-apple-ios17.0 "$BASE"/piezas/host-ios/ios/*.swift
echo "✓ host-ios revisa sus tipos con el SDK de iOS"
