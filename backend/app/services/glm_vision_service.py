"""智谱 GLM 视觉模型调用。"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import httpx

from app.core.config import settings

SETTLEMENT_PROMPT = """你是汽车维修结算单识别助手。请仔细阅读图片中的「维修结算单」，提取结构化信息。
只输出 JSON，不要 markdown 代码块，不要解释。

JSON 格式：
{
  "order_no": "委托单号或结算单号",
  "plate_number": "车牌号",
  "vehicle_model": "车型",
  "owner": "车主或单位",
  "shop_name": "维修厂/接待单位名称，没有则空字符串",
  "mileage_in": 进厂里程数字,
  "service_date": "YYYY-MM-DD",
  "total_amount": 实收金额数字,
  "items": [
    {
      "name": "维修项目名称",
      "part_name": "配件名称，没有则空",
      "quantity": 数量数字,
      "unit": "单位",
      "labor_fee": 工时费数字,
      "part_fee": 材料费数字,
      "amount": 行金额数字
    }
  ]
}

若某字段无法识别，字符串用空字符串，数字用 0。items 需包含结算单上所有维修/材料行。"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def recognize_settlement_image(image_path: Path) -> dict:
    if not settings.zhipu_api_key:
        raise RuntimeError("未配置 ZHIPU_API_KEY，无法识别结算单")
    suffix = image_path.suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(suffix, "jpeg")
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    payload = {
        "model": settings.zhipu_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
                    {"type": "text", "text": SETTLEMENT_PROMPT},
                ],
            }
        ],
        "temperature": 0.1,
    }
    url = f"{settings.zhipu_api_base.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.zhipu_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"GLM 识别失败 HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return _extract_json(content)
