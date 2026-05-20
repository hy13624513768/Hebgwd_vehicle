"""为各车间创建 workshop_admin 账号（登录名：{车间名}管理员，默认密码 hebgwd_123）。

在 backend 目录下执行：

    python scripts/seed_workshop_admins.py

重置已存在账号的密码为默认初始密码：

    python scripts/seed_workshop_admins.py --reset-password
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.db.session import SessionLocal
from app.services.seed_service import collect_workshop_names, seed_workshop_admin_accounts

DEFAULT_PASSWORD = "hebgwd_123"


def main() -> None:
    parser = argparse.ArgumentParser(description="批量创建各车间管理员账号")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="已存在的车间管理员账号也重置为默认初始密码",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"初始密码（默认 {DEFAULT_PASSWORD}）",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        workshops = collect_workshop_names(db)
        print(f"共识别 {len(workshops)} 个车间：")
        for ws in workshops:
            print(f"  - {ws}")
        created = seed_workshop_admin_accounts(
            db,
            password=args.password,
            reset_password=args.reset_password,
        )
        print(f"\n新建账号 {len(created)} 个：")
        for name in created:
            print(f"  + {name}")
        if args.reset_password:
            print("\n已按 --reset-password 将已存在账号密码同步为初始密码。")
        print("\n登录说明：用户名为「{车间名}管理员」，初始密码为上述默认密码。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
