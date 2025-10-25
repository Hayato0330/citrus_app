# UI刷新版（修正版：スクロール＋背景色対応）

import math
from typing import List, Dict
from io import BytesIO
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st
import boto3
import requests
import uuid

# ===== 基本設定 =====
st.set_page_config(page_title="柑橘レコメンダ 🍊", page_icon="🍊", layout="wide")

# ===== 背景色の変更 =====
st.markdown(
    """
    <style>
    body {
        background-color: #ffd700;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #ffd700;
    }
    [data-testid="stSidebar"] {
        background-color: #ffd700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

FEATURES = ["brix", "acid", "bitterness", "aroma", "moisture", "texture"]

ALIASES = {
    "brix": ["brix", "sweet", "sweetness", "sugar"],
    "acid": ["acid", "acidity", "sour", "sourness"],
    "bitterness": ["bitterness", "bitter"],
    "aroma": ["aroma", "smell", "fragrance", "flavor", "flavour"],
    "moisture": ["moisture", "juicy", "juiciness"],
    "texture": ["texture", "elastic", "firmness", "pulpiness"],
}

def _append_simple_log(input_dict: dict, output_value: str | None) -> None:
    url = st.secrets.get("log_api_url")
    token = st.secrets.get("log_api_token")
    if not url or not token:
        return
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": st.session_state.setdefault("sid", str(uuid.uuid4())),
        "input_json": input_dict,
        "result": {"output": output_value},
    }
    key = str(hash(str(payload["input_json"]) + str(payload["result"])))
    if st.session_state.get("last_log_key") == key:
        return
    try:
        r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=5)
        r.raise_for_status()
        st.session_state["last_log_key"] = key
    except Exception as e:
        st.info(f"ログ送信をスキップした（理由：{e}）")

def label_map(k: str) -> str:
    return {
        "brix": "甘さ",
        "acid": "酸味",
        "bitterness": "苦味",
        "aroma": "香り",
        "moisture": "ジューシーさ",
        "texture": "食感（しっかり）",
    }.get(k, k)

st.title("🍊 柑橘レコメンダ（UI刷新版）")
st.caption("※ 背景色 #ffd700 で統一。左側の入力欄はスクロール可能。")

for key in [
    "val_brix", "val_acid", "val_bitterness", "val_aroma", "val_moisture", "val_texture",
    "val_season", "right_output",
]:
    st.session_state.setdefault(key, None)

def scale_buttons(label: str, state_key: str):
    st.write(label)
    cols = st.columns(6)
    for i, c in enumerate(cols, start=1):
        with c:
            if st.button(str(i), key=f"btn_{state_key}_{i}"):
                st.session_state[state_key] = i
    sel = st.session_state[state_key]
    st.caption("選択: " + (str(sel) if sel is not None else "未選択"))

def season_buttons(state_key: str = "val_season"):
    st.write("季節の希望")
    cols = st.columns(4)
    seasons = [("winter", "冬"), ("spring", "春"), ("summer", "夏"), ("autumn", "秋")]
    for (code, label), c in zip(seasons, cols):
        with c:
            if st.button(label, key=f"btn_season_{code}"):
                st.session_state[state_key] = code
    cur = st.session_state[state_key]
    jp = {"winter": "冬", "spring": "春", "summer": "夏", "autumn": "秋"}
    st.caption("選択: " + (jp.get(cur, "未選択")))

left, right = st.columns(2, gap="large")

with left:
    st.subheader("入力（左側）")

    # ===== スクロール可能な領域 =====
    with st.container():
        st.markdown(
            """
            <style>
            div[data-testid="stVerticalBlock"] > div:first-child {
                max-height: 500px;
                overflow-y: auto;
                padding-right: 10px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        scale_buttons("甘さ（brix）", "val_brix")
        scale_buttons("酸味（acid）", "val_acid")
        scale_buttons("苦味（bitterness）", "val_bitterness")
        scale_buttons("香り（aroma）", "val_aroma")
        scale_buttons("ジューシーさ（moisture）", "val_moisture")
        scale_buttons("食感（しっかり）（texture）", "val_texture")
        season_buttons("val_season")

    st.divider()
    if st.button("完了", type="primary", use_container_width=True):
        missing = [
            k for k in [
                "val_brix", "val_acid", "val_bitterness", "val_aroma", "val_moisture", "val_texture", "val_season",
                "right_output",
            ] if st.session_state.get(k) in (None, "")
        ]
        if missing:
            st.error("未入力の項目があるため送信できない．")
        else:
            input_dict = {
                "brix": int(st.session_state.val_brix),
                "acid": int(st.session_state.val_acid),
                "bitterness": int(st.session_state.val_bitterness),
                "aroma": int(st.session_state.val_aroma),
                "moisture": int(st.session_state.val_moisture),
                "texture": int(st.session_state.val_texture),
                "season_pref": st.session_state.val_season,
            }
            _append_simple_log(input_dict=input_dict, output_value=st.session_state.right_output)
            st.success("入力値と出力値をログとして送信した．")

with right:
    st.subheader("右側：操作と出力")
    st.caption("a〜f ボタンを押すと，下に対応テキスト（A〜F）を出力する．")

    bc = st.columns(6)
    btn_labels = ["a", "b", "c", "d", "e", "f"]
    out_map = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F"}
    for lab, col in zip(btn_labels, bc):
        with col:
            if st.button(lab.upper(), key=f"btn_right_{lab}"):
                st.session_state.right_output = out_map[lab]

    st.divider()
    if st.session_state.right_output:
        st.markdown(f"### 出力: {st.session_state.right_output}")
    else:
        st.info("まだ出力はない．a〜f のいずれかを押すこと．")