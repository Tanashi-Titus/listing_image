#!/usr/bin/env bash
# ============================================================================
#  Dựng TNT Listing Image thành .app trên macOS  ->  dist/TNT_Listing_MAC.zip
#
#  CHẠY TRÊN MÁY MAC (PyInstaller không cross-compile — không build từ Windows được):
#      bash build_mac.sh
#
#  Yêu cầu: macOS 11+, python3, và máy NGƯỜI DÙNG cần cài sẵn Google Chrome
#  (tool mở Chrome thật qua channel="chrome").
#
#  Zip xuất ra KHÔNG chứa license.key / machine_id.txt — mỗi máy tự xin license.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="TNT_Listing"
APP="dist/${APP_NAME}.app"

echo "==> 1/5 Tạo venv + cài thư viện"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller
# Lớp license cần cryptography (requirements.txt có thể chưa liệt kê).
pip install cryptography PySide6

echo "==> 2/5 Nạp driver Playwright"
python -m playwright install chromium || true
# Ghi chú: tool ưu tiên Chrome thật (channel="chrome"). Chromium chỉ là dự phòng và
# KHÔNG được nhúng vào .app (giống bản Windows) -> máy đích nên cài Google Chrome.

echo "==> 3/5 Build .app"
rm -rf build dist
pyinstaller "${APP_NAME}_mac.spec"

if [ ! -d "$APP" ]; then
  echo "!! Build thất bại: không thấy $APP"; exit 1
fi

echo "==> 4/5 Ad-hoc codesign (đỡ bị Gatekeeper chặn)"
# --deep hiểu cấu trúc bundle, ký gọn cả app.
codesign --force --deep --sign - "$APP" || echo "   (codesign lỗi — vẫn dùng được, xem ghi chú quarantine bên dưới)"

echo "==> 5/5 Dọn file riêng tư + đóng gói zip"
# TUYỆT ĐỐI không đưa license.key / machine_id.txt của máy build vào bản phát hành.
find "$APP" -name 'license.key' -o -name 'license.key.off' -o -name 'machine_id.txt' \
  | while read -r f; do rm -f "$f"; echo "   đã loại: $f"; done

ZIP="dist/${APP_NAME}_MAC.zip"
rm -f "$ZIP"
# ditto giữ nguyên metadata/quyền thực thi của .app (zip thường có thể làm hỏng app).
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"

echo ""
echo "=============================================================="
echo " XONG:  $ZIP"
echo "=============================================================="
echo " Gửi file zip này cho người dùng Mac. Họ giải nén rồi làm 1 lần:"
echo "     xattr -dr com.apple.quarantine ${APP_NAME}.app"
echo " (hoặc chuột phải -> Open). Sau đó mở app:"
echo "   - Lần đầu chưa có license -> app hiện MÃ MÁY + nút Copy."
echo "   - Gửi mã máy cho quản trị -> nhận license.key -> đặt CẠNH app"
echo "     hoặc /Library/Application Support/TNT/license.key"
echo "=============================================================="
