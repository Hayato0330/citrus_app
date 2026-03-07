import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

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
    入力値と推薦結果をD1ログAPIへ送信する．
    Secrets未設定ならスキップする．
    直近の重複送信は抑止する．
    """
    url = st.secrets.get("log_api_url")
    token = st.secrets.get("log_api_token")
    if not url or not token:
        return

    normalized_result = normalize_result_for_log(result_value)

    payload = {
        "user_id": st.session_state.get("user_id"),
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": st.session_state.setdefault("sid", str(uuid.uuid4())),
        "input_json": input_dict,
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

def append_event_log(event_name: str, event_data: dict | None = None) -> None:
    """
    汎用イベントログをD1ログAPIへ送信する．
    例：
    - route_change
    - result_login_view
    """
    url = st.secrets.get("log_api_url")
    token = st.secrets.get("log_api_token")
    if not url or not token:
        return

    payload = {
        "user_id": st.session_state.get("user_id"),
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": st.session_state.setdefault("sid", str(uuid.uuid4())),
        "input_json": {
            "event": event_name,
            **(event_data or {}),
        },
        "result": [],
    }

    dedup_src = json.dumps(
        payload["input_json"],
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    dedup_key = hashlib.sha256(dedup_src.encode("utf-8")).hexdigest()

    # event専用の重複キー
    last_event_key = st.session_state.get("last_event_log_key")
    if last_event_key == dedup_key:
        return

    try:
        r = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if r.status_code >= 400:
            st.error(f"イベントログAPIエラー: {r.status_code}\n{r.text}")
            return
        st.session_state["last_event_log_key"] = dedup_key
    except Exception as e:
        st.info(f"イベントログ送信をスキップした（理由：{e}）")
