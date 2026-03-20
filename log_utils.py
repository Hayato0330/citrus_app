# log_utils.py
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote # 本間追加

import requests
import streamlit as st


def normalize_result_for_log(result_value: Any) -> list:
    """
    推薦結果をD1のresultカラムへ保存しやすい形へ正規化する．

    想定入力例：
    - [12, 5, 27]
    - [{"id": 12, "rank": 1}, {"id": 5, "rank": 2}, {"id": 27, "rank": 3}]
    - ["せとか", "不知火", "はるみ"]
    """
    if result_value is None:
        return []

    if isinstance(result_value, (str, int, float, bool)):
        result_value = [result_value]

    normalized = []
    if isinstance(result_value, (list, tuple)):
        for idx, item in enumerate(result_value, start=1):
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("rank", idx)
                normalized.append(row)
            elif isinstance(item, int):
                normalized.append({"id": int(item), "rank": idx})
            elif isinstance(item, float) and item.is_integer():
                normalized.append({"id": int(item), "rank": idx})
            elif isinstance(item, str):
                normalized.append({"name": item, "rank": idx})
            else:
                normalized.append({"value": item, "rank": idx})

    return normalized[:3]


def append_simple_log(input_dict: dict, result_value=None) -> None:
    """
    1回の診断につき1行だけD1ログAPIへ送信する．
    input_json の中に user_id も含めて保存する．
    Secrets未設定ならスキップする．
    直近の重複送信は抑止する．
    """
    url = st.secrets.get("log_api_url")
    token = st.secrets.get("log_api_token")
    if not url or not token:
        return

    normalized_result = normalize_result_for_log(result_value)

    input_with_user = dict(input_dict or {})
    input_with_user["user_id"] = st.session_state.get("user_id")

    payload = {
        "user_id": st.session_state.get("user_id"),
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": st.session_state.setdefault("sid", str(uuid.uuid4())),
        "input_json": input_with_user,
        "result": normalized_result,
    }

    dedup_src = json.dumps(
        {
            "input_json": payload["input_json"],
            "result": payload["result"],
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    dedup_key = hashlib.sha256(dedup_src.encode("utf-8")).hexdigest()

    if st.session_state.get("last_log_key") == dedup_key:
        return

    try:
        r = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if r.status_code >= 400:
            st.error(f"ログAPIエラー: {r.status_code}\n{r.text}")
            return

        st.session_state["last_log_key"] = dedup_key

    except Exception as e:
        st.info(f"ログ送信をスキップした（理由：{e}）")

def build_click_log_url(slot: str, destination_url: str) -> str:
    """
    クリックログ更新用の Cloudflare Worker 中継URLを作る．

    - append_simple_log() で INSERT 済みの session_id を手掛かりにする
    - Worker 側で slot 列（例: 1_a, 2_r）を 0 -> 1 に UPDATE してから
      destination_url へ redirect する
    - log_redirect_base_url が未設定なら destination_url をそのまま返す
    """
    base = st.secrets.get("log_redirect_base_url", "").strip()
    if not base:
        return destination_url

    session_id = st.session_state.get("sid", "")
    user_id = st.session_state.get("user_id", "")

    return (
        f"{base}"
        f"?session_id={quote(str(session_id))}"
        f"&user_id={quote(str(user_id))}"
        f"&slot={quote(str(slot))}"
        f"&to={quote(destination_url, safe='')}"
    )