# -*- coding: utf-8 -*-
"""油卡余额与加油流水同步脚本。

从 95504 油卡平台拉取数据，与 bus_fuel_card_lookup 按卡号关联车间/车号，
全量写入 bus_fuel_balance、bus_fuel_record，供 /app/fuel 页面展示。

在 backend 目录执行：
    python scripts/run_query.py
    python scripts/run_query.py --date-from 2026-05-01 --date-to 2026-05-31

环境变量（可选）：
    OIL_PG_DSN / OIL_PG_HOST / OIL_PG_PORT / OIL_PG_DB / OIL_PG_PASSWORD / OIL_PG_SSLMODE
"""
import argparse
import asyncio
import base64
import json
import os
import random
import re
import time
import traceback
from datetime import date, datetime
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import aiohttp
import ddddocr
import execjs
import pandas as pd
import rsa
from loguru import logger
from PIL import Image, ImageOps
from psycopg2 import connect
from psycopg2.extras import execute_values
from psycopg2 import OperationalError
from psycopg2 import sql

# Kljyk_Ykcx 接口字段（volumn 无则尝试 volume）
YKCX_API_COLUMNS = (
    "cardAsn",
    "amount",
    "balance",
    "orgName",
    "occurTime",
    "giftName",
    "volumn",
)
# 流水记录列：接口字段 + 与 bus_fuel_card_lookup 关联带出的车间、车号
YKCX_RECORD_COLUMNS = YKCX_API_COLUMNS + ("车间", "车号")

# PostgreSQL 配置（油卡余额/流水同步到 bus_system_test）
# 优先使用环境变量 OIL_PG_DSN（整段 postgresql://用户:密码@主机:端口/数据库名）
# 未设置时默认连 Sealos 集群内开发库；密码建议用环境变量 OIL_PG_PASSWORD
_OIL_PG_DSN_ENV = os.environ.get("OIL_PG_DSN", "").strip()
if _OIL_PG_DSN_ENV:
    _parsed = urlparse(_OIL_PG_DSN_ENV)
    PG_HOST = _parsed.hostname or "bus-system-postgresql.ns-1ht608x0.svc"
    PG_PORT = int(_parsed.port or 5432)
    PG_DB = (_parsed.path or "/bus_system_test").lstrip("/") or "bus_system_test"
    PG_USER = unquote(_parsed.username) if _parsed.username else "postgres"
    _netloc_pw = unquote(_parsed.password) if _parsed.password else ""
    PG_PASSWORD = os.environ.get("OIL_PG_PASSWORD", "").strip() or _netloc_pw
else:
    PG_HOST = os.environ.get("OIL_PG_HOST", "bus-system-postgresql.ns-1ht608x0.svc")
    PG_PORT = int(os.environ.get("OIL_PG_PORT", "5432"))
    PG_DB = os.environ.get("OIL_PG_DB", "bus_system_test")
    PG_USER = os.environ.get("OIL_PG_USER", "postgres")
    PG_PASSWORD = os.environ.get("OIL_PG_PASSWORD", "tf549zg8")

# 集群内网默认 disable；外网连接可设为 require
PG_SSLMODE = os.environ.get("OIL_PG_SSLMODE", "disable")

PG_LOOKUP_TABLE = "bus_fuel_card_lookup"
PG_BALANCE_TABLE = "bus_fuel_balance"
PG_RECORD_TABLE = "bus_fuel_record"

ProgressCallback = Callable[[str], None]


def _parse_cli_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return datetime.strptime(raw.strip(), "%Y-%m-%d").date()


def resolve_date_range(
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    """未传日期时默认：当月 1 日 ~ 今天。"""
    today = date.today()
    end = date_to or today
    start = date_from or end.replace(day=1)
    if start > end:
        start, end = end, start
    return start, end


def month_start_dates(date_from: date, date_to: date) -> list[str]:
    """返回日期范围内每个月 1 号（Data_DanWei 参数）。"""
    cur = date_from.replace(day=1)
    end_month = date_to.replace(day=1)
    out: list[str] = []
    while cur <= end_month:
        out.append(cur.strftime("%Y-%m-%d"))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return out


class OilCardBalanceQuery:
    def __init__(
        self,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        df = date_from if isinstance(date_from, date) else _parse_cli_date(date_from)
        dt = date_to if isinstance(date_to, date) else _parse_cli_date(date_to)
        self.date_from, self.date_to = resolve_date_range(df, dt)
        self.on_progress = on_progress
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": "https://www.95504.net/NewIndex.aspx",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        self.url = "https://www.95504.net/NewKljyk/Querylist.ashx"
        self.ykcx_url = "https://www.95504.net/NewKljyk/Kljyk_Ykcx.ashx"
        self.capture_url = "https://www.95504.net/UserControl/Image.aspx"
        self.login_url = "https://www.95504.net/LoginHandler.ashx"
        self.ykcx_data_danwei = self.date_from.replace(day=1).strftime("%Y-%m-%d")
        self.username = "hg9130190004588286"
        self.password = "hy112411"

    def _emit(self, message: str) -> None:
        logger.info(message)
        if self.on_progress:
            self.on_progress(message)

    def encode(self, cipher: str) -> str:
        """登录加密函数，使用RSA公钥加密"""
        pub_key_b64 = (
            "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCyZ/wVj9oe5n/k99TBv3xNMNhW"
            "3kaavvjTb3O/PjsSIRj8wFAQTmgEQamdj/HoWO3gHtIcJi6I2cI1OLxu/PdhSPG8"
            "dJCIM4RwcXaGem3zt8RcPoXKE4QIJT+xrdvuQ7CK/VJQiWNU2wVbjqeG5fM67Zb4"
            "oky9lmDbIqXHLugK5QIDAQAB"
        )
        pub_key_der = base64.b64decode(pub_key_b64)
        pub_key = rsa.PublicKey.load_pkcs1_openssl_der(pub_key_der)
        encrypted = rsa.encrypt(cipher.encode("utf-8"), pub_key)
        return base64.b64encode(encrypted).decode("utf-8")

    @staticmethod
    def _http_timeout(total: float) -> aiohttp.ClientTimeout:
        return aiohttp.ClientTimeout(total=total)

    async def pass_capture(
        self, session: aiohttp.ClientSession, max_retries: int = 5
    ) -> Optional[str]:
        """获取验证码并识别"""

        def get_capture_code(image_bytes: bytes) -> str:
            image = Image.open(BytesIO(image_bytes))
            # 灰度化处理
            gray_image = ImageOps.grayscale(image)
            # 黑白化处理（设置阈值）
            threshold = 128
            bw_image = gray_image.point(lambda x: 0 if x < threshold else 255, "L")
            buf = BytesIO()
            bw_image.save(buf, format="PNG")
            ocr = ddddocr.DdddOcr()
            return ocr.classification(buf.getvalue())

        headers = {
            "Accept": (
                "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": "https://www.95504.net/NewIndex.aspx",
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        for attempt in range(max_retries):
            try:
                current_time = datetime.now()
                formatted_time = current_time.strftime("%Y/%m/%d %H:%M:%S")
                params = {"code": f"newcode?{formatted_time}"}
                async with session.get(
                    self.capture_url,
                    headers=headers,
                    params=params,
                    timeout=self._http_timeout(10),
                ) as response:
                    image_bytes = await response.read()
                code = get_capture_code(image_bytes)
                logger.info(
                    f"验证码识别结果：{code} (尝试 {attempt + 1}/{max_retries})"
                )
                return code
            except Exception as e:
                logger.warning(
                    f"获取验证码失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                )
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)

        return None

    async def login(self, session: aiohttp.ClientSession, max_retries: int = 3) -> bool:
        """登录函数"""
        for attempt in range(max_retries):
            try:
                code = await self.pass_capture(session)
                if not code:
                    logger.error("无法获取验证码")
                    continue

                logger.info(f"获取到验证码：{code}")
                login_data = {
                    "action": "login",
                    "id": self.encode(self.username).replace("+", "%2B"),
                    "code": code,
                    "pwd": self.encode(self.password).replace("+", "%2B"),
                }
                async with session.post(
                    self.login_url,
                    headers=self.headers,
                    data=login_data,
                    timeout=self._http_timeout(10),
                ) as resp:
                    response = await resp.json(content_type=None)
                if response["status"] == "1":
                    logger.success(f"{self.username} 登录成功")
                    return True
                logger.error(f'{self.username} 登录失败：{response["msg"]}')
                if attempt < max_retries - 1:
                    logger.info("等待 5 秒后重试...")
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"登录异常 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)

        return False

    async def query_balance(
        self, session: aiohttp.ClientSession, num: int
    ) -> List[Dict[str, Any]]:
        """油卡余额查询，返回每一页的字典数据"""
        try:
            timestamp = int(time.time() * 1000 * 1000)
            params = {
                "cardAsn": "",
                "deptNo": "",
                "currPage": str(num),
                "date": f"0.496971673305496960.{timestamp}",
            }
            async with session.get(
                self.url,
                headers=self.headers,
                params=params,
                timeout=self._http_timeout(15),
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    list_data = execjs.eval(text)["data"]
                    return list_data
                logger.error(f"获取第 {num} 页失败：HTTP {response.status}")
                return []
        except Exception as e:
            logger.error(f"查询第 {num} 页异常：{e}")
            return []

    async def _fetch_all_balance_pages(
        self, session: aiohttp.ClientSession
    ) -> Dict[str, Dict[str, float]]:
        """分页拉取余额列表并解析为 {卡号: {金额, 备用金}}（与原先每类接口各 5 并发一致）。"""
        balance_dict: Dict[str, Dict[str, float]] = {}
        logger.info("开始获取油卡余额数据（共 36 页）...")
        sem = asyncio.Semaphore(5)

        async def fetch_page(n: int) -> Tuple[int, List[Dict[str, Any]]]:
            async with sem:
                try:
                    data = await self.query_balance(session, n)
                    return n, data
                except Exception as exc:
                    logger.error(f"获取第 {n} 页数据时出错：{exc}")
                    return n, []

        tasks = [asyncio.create_task(fetch_page(n)) for n in range(1, 37)]
        completed = 0
        for coro in asyncio.as_completed(tasks):
            n, list_data = await coro
            completed += 1
            logger.info(f"进度：{completed}/36 - 完成获取第 {n} 页数据")
            if list_data:
                balance_dict.update(self.parse_data(list_data))
        return balance_dict

    def _parse_ykcx_json(self, text: str) -> Dict[str, Any]:
        """Kljyk_Ykcx 返回非标准 JSON（单引号、未加引号的键）。"""
        text_json = text.replace("'", '"')
        text_json = re.sub(
            r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', text_json
        )
        return json.loads(text_json)

    async def _query_ykcx_page(
        self,
        session: aiohttp.ClientSession,
        data_danwei: str,
        curr_page: int,
    ) -> Optional[Dict[str, Any]]:
        params = {
            "Data_DanWei": data_danwei,
            "OWNER_ID": "",
            "Card_No": "",
            "currPage": str(curr_page),
            "date": str(random.random()),
            "date1": str(random.random()),
        }
        try:
            async with session.get(
                self.ykcx_url,
                headers=self.headers,
                params=params,
                timeout=self._http_timeout(15),
            ) as response:
                if response.status != 200:
                    logger.error(
                        f"Kljyk_Ykcx 第 {curr_page} 页 HTTP {response.status}"
                    )
                    return None
                text = await response.text()
            return self._parse_ykcx_json(text)
        except Exception as e:
            logger.error(f"Kljyk_Ykcx 第 {curr_page} 页解析或请求异常：{e}")
            return None

    async def _fetch_ykcx_page_data(
        self,
        session: aiohttp.ClientSession,
        data_danwei: str,
        curr_page: int,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """单页拉取，返回 (页码, data 列表)，供协程并发合并。"""
        blk = await self._query_ykcx_page(session, data_danwei, curr_page)
        if not blk:
            return curr_page, []
        return curr_page, list(blk.get("data") or [])

    async def fetch_ykcx_all(
        self,
        session: aiohttp.ClientSession,
        data_danwei: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """油卡查询：先请求第 1 页取 pageCount，再协程并发拉取第 2..N 页。"""
        data_danwei = data_danwei if data_danwei is not None else self.ykcx_data_danwei
        # 第一次请求，currPage 固定为 1，响应 JSON 中带 pageCount
        first = await self._query_ykcx_page(session, data_danwei, 1)
        if first is None:
            return []
        try:
            page_count = max(1, int(first.get("pageCount", 1) or 1))
        except (TypeError, ValueError):
            page_count = 1
        rows = list(first.get("data") or [])
        logger.info(
            f"Kljyk_Ykcx 进度：第 1/{page_count} 页完成，本页 {len(rows)} 条，累计 {len(rows)} 条"
        )
        if page_count <= 1:
            logger.info(f"Kljyk_Ykcx 全部完成：共 {page_count} 页，合计 {len(rows)} 条")
            return rows

        extra_pages = page_count - 1
        page_data: Dict[int, List[Dict[str, Any]]] = {}
        sem = asyncio.Semaphore(5)

        async def fetch_one(p: int) -> Tuple[int, List[Dict[str, Any]]]:
            async with sem:
                try:
                    return await self._fetch_ykcx_page_data(session, data_danwei, p)
                except Exception as exc:
                    logger.error(f"Kljyk_Ykcx 第 {p} 页并发任务异常：{exc}")
                    return p, []

        tasks = [
            asyncio.create_task(fetch_one(p)) for p in range(2, page_count + 1)
        ]
        completed = 0
        for coro in asyncio.as_completed(tasks):
            page_no, chunk = await coro
            page_data[page_no] = chunk
            completed += 1
            logger.info(
                f"Kljyk_Ykcx 进度（并发）：{completed}/{extra_pages} - "
                f"完成第 {page_no}/{page_count} 页，本页 {len(chunk)} 条"
            )

        for p in range(2, page_count + 1):
            rows.extend(page_data.get(p, []))
        logger.info(f"Kljyk_Ykcx 全部完成：共 {page_count} 页，合计 {len(rows)} 条")
        return rows

    def _filter_ykcx_by_date(
        self,
        records: List[Dict[str, Any]],
        date_from: date,
        date_to: date,
    ) -> List[Dict[str, Any]]:
        """按 occurTime 过滤到指定日期范围（含起止日）。"""
        filtered: List[Dict[str, Any]] = []
        for row in records:
            occur = self._parse_occur_time(row.get("occurTime"))
            if occur is None:
                continue
            day = occur.date()
            if date_from <= day <= date_to:
                filtered.append(row)
        return filtered

    async def fetch_ykcx_date_range(
        self,
        session: aiohttp.ClientSession,
        date_from: date,
        date_to: date,
    ) -> List[Dict[str, Any]]:
        """按日期范围拉取加油流水（按月请求后过滤）。"""
        month_starts = month_start_dates(date_from, date_to)
        merged: List[Dict[str, Any]] = []
        for month_start in month_starts:
            label = month_start[:7]
            self._emit(f"正在查询中国石油 {label} 月加油流水…")
            rows = await self.fetch_ykcx_all(session, month_start)
            merged.extend(rows)
        filtered = self._filter_ykcx_by_date(merged, date_from, date_to)
        logger.info(
            f"加油流水日期过滤：原始 {len(merged)} 条，"
            f"{date_from} ~ {date_to} 范围内 {len(filtered)} 条"
        )
        return filtered

    def parse_data(self, list_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """将页面数据解析为 {卡号: {金额, 备用金}} 字典"""
        result = {}
        for item in list_data:
            try:
                asn = str(item["asn"]).strip()
                result[asn] = {
                    "金额": float(item["cardBalance"]),
                    "备用金": float(item["balance"]),
                }
            except (KeyError, TypeError, ValueError):
                pass
        return result

    def _project_ykcx_row(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """从单条接口记录中取出写入数据库的字段；volumn 兼容 volume；卡号兼容 asn。"""
        vol = r.get("volumn")
        if vol is None and "volume" in r:
            vol = r.get("volume")
        card = r.get("cardAsn")
        if card is None:
            card = r.get("asn")
        return {
            "cardAsn": card,
            "amount": r.get("amount"),
            "balance": r.get("balance"),
            "orgName": r.get("orgName"),
            "occurTime": r.get("occurTime"),
            "giftName": r.get("giftName"),
            "volumn": vol,
        }

    def build_ykcx_records_df(
        self, ykcx_records: List[Dict[str, Any]], card_lookup_df: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """cardAsn 与 bus_fuel_card_lookup 内连接，带出车间、车号；lookup 按卡号去重。"""
        if not ykcx_records:
            return None
        rows = [self._project_ykcx_row(r) for r in ykcx_records]
        df = pd.DataFrame(rows, columns=list(YKCX_API_COLUMNS))
        df["cardAsn"] = df["cardAsn"].astype(str).str.strip()
        lookup = card_lookup_df[["卡号", "车间", "车号"]].copy()
        lookup["卡号"] = lookup["卡号"].astype(str).str.strip()
        lookup = lookup.drop_duplicates(subset=["卡号"], keep="first")
        merged = df.merge(lookup, left_on="cardAsn", right_on="卡号", how="inner")
        merged = merged.drop(columns=["卡号"])
        merged = merged.reindex(columns=list(YKCX_RECORD_COLUMNS))
        return merged

    def _load_card_lookup_from_pg(self) -> pd.DataFrame:
        """从 bus_fuel_card_lookup 读取卡号-车间-车号对照表。"""
        conn = None
        try:
            conn = self._get_pg_conn()
            df = pd.read_sql(
                f"""
                SELECT card_no AS "卡号", workshop AS "车间", vehicle_no AS "车号"
                FROM {PG_LOOKUP_TABLE}
                ORDER BY id
                """,
                conn,
            )
            df["卡号"] = df["卡号"].astype(str).str.strip()
            return df
        finally:
            if conn:
                conn.close()

    def _get_pg_conn(self):
        """创建 PostgreSQL 连接。"""
        return connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
            sslmode=PG_SSLMODE,
            connect_timeout=8,
            application_name="oil_card_balance_sync",
        )

    def _safe_decimal(self, val: Any) -> Optional[float]:
        """将数值安全转成 float，失败返回 None。"""
        if val is None:
            return None
        try:
            if pd.isna(val):
                return None
        except Exception:
            pass
        text = str(val).strip()
        if text == "":
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_occur_time(val: Any) -> Optional[datetime]:
        """解析加油流水发生时间。"""
        if val is None:
            return None
        text = str(val).strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def _replace_balance_to_pg(self, df_balance: pd.DataFrame) -> int:
        """将油卡余额全量覆盖写入 bus_fuel_balance（先清空后插入）。"""
        if df_balance is None or df_balance.empty:
            logger.info("油卡余额 DataFrame 为空，跳过 PostgreSQL 覆盖写入")
            return 0

        rows: List[Tuple[Any, ...]] = []
        now = datetime.now()
        for _, row in df_balance.iterrows():
            card_no = str(row.get("卡号", "")).strip()
            if not card_no:
                continue
            amount = self._safe_decimal(row.get("金额")) or 0.0
            reserve_fund = self._safe_decimal(row.get("备用金")) or 0.0
            total = self._safe_decimal(row.get("合计"))
            if total is None:
                total = amount + reserve_fund
            rows.append(
                (
                    card_no,
                    str(row.get("车间", "")).strip(),
                    str(row.get("车号", "")).strip(),
                    amount,
                    reserve_fund,
                    total,
                    now,
                )
            )

        if not rows:
            logger.warning("油卡余额无有效记录可写入 PostgreSQL（卡号为空）")
            return 0

        conn = None
        try:
            conn = self._get_pg_conn()
            table_ident = sql.Identifier(PG_BALANCE_TABLE)
            insert_stmt = sql.SQL(
                """
                INSERT INTO {} (
                    card_no, workshop, vehicle_no, amount, reserve_fund, total, updated_at
                ) VALUES %s
                """
            ).format(table_ident)
            with conn.cursor() as cur:
                cur.execute(sql.SQL("TRUNCATE TABLE {}").format(table_ident))
                execute_values(cur, insert_stmt.as_string(conn), rows, page_size=500)
            conn.commit()
            logger.success(
                f"油卡余额已覆盖写入 PostgreSQL：表 {PG_BALANCE_TABLE}，写入 {len(rows)} 条"
            )
            return len(rows)
        except Exception as e:
            if conn:
                conn.rollback()
            self._log_pg_error(e, PG_BALANCE_TABLE)
            return 0
        finally:
            if conn:
                conn.close()

    def _replace_ykcx_to_pg_record(self, df_ykcx: Optional[pd.DataFrame]) -> int:
        """将加油流水全量覆盖写入 bus_fuel_record（先清空后插入，字段与后端 ORM 一致）。"""
        if df_ykcx is None or df_ykcx.empty:
            logger.info("加油流水 DataFrame 为空，跳过 bus_fuel_record 写入")
            return 0

        rows: List[Tuple[Any, ...]] = []
        now = datetime.now()
        for _, row in df_ykcx.iterrows():
            card_asn = str(row.get("cardAsn", "")).strip()
            if not card_asn:
                continue
            occur_time = self._parse_occur_time(row.get("occurTime"))
            if occur_time is None:
                logger.warning(f"跳过无法解析 occurTime 的流水：cardAsn={card_asn}")
                continue
            rows.append(
                (
                    card_asn,
                    self._safe_decimal(row.get("amount")) or 0.0,
                    self._safe_decimal(row.get("balance")) or 0.0,
                    str(row.get("orgName", "")).strip(),
                    occur_time,
                    str(row.get("giftName", "")).strip(),
                    self._safe_decimal(row.get("volumn")) or 0.0,
                    str(row.get("车间", "")).strip(),
                    str(row.get("车号", "")).strip(),
                    now,
                )
            )

        if not rows:
            logger.warning("加油流水无有效记录可写入 bus_fuel_record（cardAsn 为空或时间无效）")
            return 0

        conn = None
        try:
            conn = self._get_pg_conn()
            table_ident = sql.Identifier(PG_RECORD_TABLE)
            insert_stmt = sql.SQL(
                """
                INSERT INTO {} (
                    card_asn, amount, balance, org_name, occur_time, gift_name,
                    volumn, workshop, car_no, updated_at
                ) VALUES %s
                """
            ).format(table_ident)
            with conn.cursor() as cur:
                cur.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY").format(table_ident))
                execute_values(cur, insert_stmt.as_string(conn), rows, page_size=500)
            conn.commit()
            logger.success(
                f"加油流水已同步 PostgreSQL：表 {PG_RECORD_TABLE}，覆盖写入 {len(rows)} 条"
            )
            return len(rows)
        except Exception as e:
            if conn:
                conn.rollback()
            self._log_pg_error(e, PG_RECORD_TABLE)
            return 0
        finally:
            if conn:
                conn.close()

    def _log_pg_error(self, e: Exception, table_name: str) -> None:
        logger.error(
            "写入 PostgreSQL 失败：type={} repr={} host={} port={} db={} user={} table={}",
            type(e).__name__,
            repr(e),
            PG_HOST,
            PG_PORT,
            PG_DB,
            PG_USER,
            table_name,
        )
        if isinstance(e, OperationalError):
            logger.error("请检查 PostgreSQL 服务状态、账号密码、数据库名和 pg_hba.conf 认证规则")
        pgerror = getattr(e, "pgerror", None)
        if pgerror:
            logger.error("PostgreSQL pgerror: {}", pgerror)
        logger.error(traceback.format_exc())

    def sync_to_database(
        self,
        balance_dict: Dict[str, Dict[str, float]],
        ykcx_records: Optional[List[Dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """从 bus_fuel_card_lookup 关联车间/车号，将余额与流水写入 PostgreSQL。"""
        lookup_df = self._load_card_lookup_from_pg()
        if lookup_df.empty:
            logger.error(
                f"表 {PG_LOOKUP_TABLE} 为空，请先将「卡号-车间-车号清单.xlsx」导入数据库"
            )
            return {"ok": False, "error": f"{PG_LOOKUP_TABLE} 表为空"}

        df_balance = lookup_df.copy()
        df_balance["金额"] = pd.to_numeric(
            df_balance["卡号"].map(lambda x: balance_dict.get(x, {}).get("金额")),
            errors="coerce",
        )
        df_balance["备用金"] = pd.to_numeric(
            df_balance["卡号"].map(lambda x: balance_dict.get(x, {}).get("备用金")),
            errors="coerce",
        )
        df_balance["合计"] = df_balance["金额"].fillna(0) + df_balance["备用金"].fillna(0)

        df_ykcx = None
        if ykcx_records:
            df_ykcx = self.build_ykcx_records_df(ykcx_records, lookup_df)

        pg_balance_written = self._replace_balance_to_pg(df_balance)
        pg_record_written = self._replace_ykcx_to_pg_record(df_ykcx)
        matched = int(df_balance["金额"].notna().sum())
        ykcx_matched = len(df_ykcx) if df_ykcx is not None and not df_ykcx.empty else 0
        ykcx_raw = len(ykcx_records) if ykcx_records else 0

        logger.success(
            f"数据库同步完成：lookup {len(lookup_df)} 条，"
            f"余额匹配 {matched}/{len(df_balance)} 条（写入 {pg_balance_written}），"
            f"流水原始 {ykcx_raw} 条、关联后 {ykcx_matched} 条（写入 {pg_record_written}）"
        )
        return {
            "ok": pg_balance_written > 0 or pg_record_written > 0,
            "lookup_count": len(lookup_df),
            "balance_matched": matched,
            "balance_written": pg_balance_written,
            "record_raw": ykcx_raw,
            "record_matched": ykcx_matched,
            "record_written": pg_record_written,
            "date_from": self.date_from.isoformat(),
            "date_to": self.date_to.isoformat(),
        }

    async def run_sync(self) -> dict[str, Any]:
        """登录油卡平台，拉取余额与流水并同步到 PostgreSQL。"""
        self._emit("正在连接中国石油油卡平台…")
        timeout = aiohttp.ClientTimeout(total=300, connect=15, sock_read=60)
        async with aiohttp.ClientSession(headers=self.headers, timeout=timeout) as session:
            self._emit("正在登录中国石油，识别验证码…")
            if not await self.login(session):
                return {"ok": False, "error": "登录中国石油失败，请稍后重试"}

            self._emit("登录成功，正在查询油卡余额…")
            balance_dict = await self._fetch_all_balance_pages(session)

            self._emit(
                f"正在查询加油流水（{self.date_from.isoformat()} 至 {self.date_to.isoformat()}）…"
            )
            ykcx_records = await self.fetch_ykcx_date_range(
                session, self.date_from, self.date_to
            )

            if not balance_dict and not ykcx_records:
                return {"ok": False, "error": "未从中国石油获取到任何数据"}

            self._emit("正在写入数据库并关联车间、车号…")
            result = self.sync_to_database(
                balance_dict,
                ykcx_records if ykcx_records else None,
            )
            if result.get("ok"):
                self._emit("同步完成，正在刷新页面数据…")
            return result

    async def main(self) -> bool:
        """CLI 入口。"""
        result = await self.run_sync()
        if result.get("ok"):
            logger.success(
                f"本次查询完成：余额写入 {result.get('balance_written', 0)} 条，"
                f"流水写入 {result.get('record_written', 0)} 条"
            )
            return True
        logger.error(result.get("error") or "同步失败")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="油卡余额与加油流水同步")
    parser.add_argument("--date-from", dest="date_from", help="查询起始日期 YYYY-MM-DD")
    parser.add_argument("--date-to", dest="date_to", help="查询截止日期 YYYY-MM-DD")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("油卡余额查询程序启动")
    logger.info("=" * 60)

    query_tool = OilCardBalanceQuery(date_from=args.date_from, date_to=args.date_to)

    try:
        success = asyncio.run(query_tool.main())
        if success:
            logger.success("程序执行完成")
        else:
            logger.error("程序执行失败")
    except Exception as e:
        logger.error(f"程序运行出错：{e}")
        logger.error(traceback.format_exc())
