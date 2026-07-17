"""Giao diện dòng lệnh tạm cho TNT Listing Image.

Đây chỉ là "mặt tiền" đầu tiên để thử nghiệm. Sau này PySide6 sẽ gọi cùng
các hàm trong core/ (không phải viết lại logic).

Cách dùng:
    python cli.py login     # đăng nhập ChatGPT & lưu session
"""
from __future__ import annotations

import argparse

from tnt_license import check_license
from core.browser import ChatGPTBrowser
from config import profile_path


def cmd_login(args) -> None:
    """Mở Chrome, để user đăng nhập ChatGPT, rồi lưu session lại (theo profile)."""
    pdir = profile_path(args.profile)
    br = ChatGPTBrowser(profile_dir=pdir)
    print(f"→ Đang mở Chrome (profile: {args.profile or 'default'} → {pdir.name})...")
    br.start()
    br.open_chatgpt()

    if br.is_logged_in(timeout_ms=6000):
        print("✓ Đã đăng nhập sẵn (session cũ còn hiệu lực).")
        print("  Muốn đổi tài khoản khác thì dùng: python cli.py login --profile <tên_khác>")
    else:
        print("→ Chưa đăng nhập. Hãy ĐĂNG NHẬP ChatGPT trong cửa sổ vừa mở.")
        print("  (Đang chờ tối đa 5 phút...)")
        if br.wait_for_login():
            print(f"✓ Đăng nhập thành công. Session lưu vào {pdir.name}/")
            print(f"  Lần sau chạy pipeline thêm: --profile {args.profile or 'default'}")
        else:
            print("✗ Hết thời gian chờ. Chạy lại: python cli.py login")

    input("\nNhấn Enter để đóng trình duyệt...")
    br.close()


def main() -> None:
    check_license("TNT_Listing")   # BẢO MẬT LICENSE
    parser = argparse.ArgumentParser(
        description="TNT Listing Image — tạo ảnh listing hàng loạt qua ChatGPT web"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_login = sub.add_parser("login", help="Đăng nhập ChatGPT & lưu session")
    p_login.add_argument("--profile", default=None,
                         help="Tên tài khoản/profile (vd: acc2). Bỏ trống = mặc định")
    p_login.set_defaults(func=cmd_login)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
