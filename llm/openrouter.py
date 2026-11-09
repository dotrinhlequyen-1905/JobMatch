"""Client tối giản cho OpenRouter (API tương thích OpenAI)."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://openrouter.ai/api/v1"


def api_key():
    """Đọc OPENROUTER_API_KEY từ biến môi trường hoặc file cấu hình tại root."""
    if value := os.environ.get("OPENROUTER_API_KEY"):
        return value
    if not (ROOT / ".env").exists():
        raise RuntimeError("Chưa cấu hình OPENROUTER_API_KEY")
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if "=" not in line:
            continue
        name, val = line.split("=", 1)
        val = val.strip().strip('"').strip("'").strip()
        if name.strip() == "OPENROUTER_API_KEY" and val:
            return val
    raise RuntimeError("Không tìm thấy OpenRouter key trong .env")


def _request(path, payload=None, timeout=120):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json",
                 "X-Title": "jobmatch-cv-jd"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def list_models():
    return _request("/models")["data"]


def chat(model, messages, temperature=0.3, max_tokens=2000, json_mode=False, retries=3):
    """Trả về (text, info). info gồm thời gian, token, lỗi nếu có."""
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    last = None
    for attempt in range(retries):
        t0 = time.time()
        try:
            r = _request("/chat/completions", payload)
            if "error" in r:
                raise RuntimeError(r["error"])
            msg = r["choices"][0]["message"]
            return msg.get("content") or "", {"sec": round(time.time() - t0, 1), "usage": r.get("usage", {})}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode(errors='ignore')[:300]}"
            if e.code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            if e.code in (400, 401, 402, 403, 404):
                break
        except Exception as e:  # timeout, lỗi mạng, lỗi từ provider
            last = str(e)[:300]
        time.sleep(3)
    return None, {"error": last}
