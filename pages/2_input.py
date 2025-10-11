# input.py
# UI刷新版（要件対応）

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

# 推薦に使う標準カラム（将来の互換のために残すが、本UIでは結果表示を行わない）
FEATURES = ["brix", "acid", "bitterness", "aroma", "moisture", "texture"]

# 入力CSVの別名 → 標準名 マッピング（ログの互換用。実際の読込や結果表示はしない）
ALIASES = {
    "brix": ["brix", "sweet", "sweetness", "sugar"],
    "acid": ["acid", "acidity", "sour", "sourness"],
    "bitterness": ["bitterness", "bitter"],
    "aroma": ["aroma", "smell", "fragrance", "flavor", "flavour"],
    "moisture": ["moisture", "juicy", "juiciness"],
    "texture": ["texture", "elastic", "firmness", "pulpiness"],
}

# ===== ユーティリティ =====
def _append_simple_log(input_dict: dict, output_value: str | None) -> None:
    """
    入力値と出力値だけをログPOSTする．
    Secretsに log_api_url と log_api_token が無ければ何もしない．
    直近の重複送信は抑止する．
    """
    url = st.secrets.get("log_api_url")
    token = st.secrets.get("log_api_token")
    if not url or not token:
        return  # ログAPI未設定なら静かにスキップ

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


# ===== UI（要件） =====
st.title("🍊 柑橘レコメンダ（UI刷新版）")
st.caption("※ この版ではデータの読み込みと結果の表示は行わない．入力完了時のみログを送信する．")

# セッション状態の初期化
for key in [
    "val_brix", "val_acid", "val_bitterness", "val_aroma", "val_moisture", "val_texture",
    "val_season", "right_output",
]:
    st.session_state.setdefault(key, None)


def scale_buttons(label: str, state_key: str):
    """1〜6の横並びボタンで値を選択する．選択値は session_state[state_key] へ格納．"""
    st.write(label)
    cols = st.columns(6)
    for i, c in enumerate(cols, start=1):
        with c:
            if st.button(str(i), key=f"btn_{state_key}_{i}"):
                st.session_state[state_key] = i
    # 現在の選択を表示
    sel = st.session_state[state_key]
    st.caption("選択: " + (str(sel) if sel is not None else "未選択"))


def season_buttons(state_key: str = "val_season"):
    """季節の4ボタン．"""
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


# レイアウト：左＝入力，右＝操作表示
left, right = st.columns(2, gap="large")

with left:
    st.subheader("入力（左側）")
    scale_buttons("甘さ（brix）", "val_brix")
    scale_buttons("酸味（acid）", "val_acid")
    scale_buttons("苦味（bitterness）", "val_bitterness")
    scale_buttons("香り（aroma）", "val_aroma")
    scale_buttons("ジューシーさ（moisture）", "val_moisture")
    scale_buttons("食感（しっかり）（texture）", "val_texture")
    season_buttons("val_season")

    st.divider()
    # 左下：完了ボタン（押下時のみログ記録）
    if st.button("完了", type="primary", use_container_width=True):
        # 入力検証（未入力があればエラー）
        missing = [
            k for k in [
                "val_brix", "val_acid", "val_bitterness", "val_aroma", "val_moisture", "val_texture", "val_season",
                "right_output",
            ] if st.session_state.get(k) in (None, "")
        ]
        if missing:
            st.error("未入力の項目があるため送信できない．右側のボタン出力を含め，全項目を選択・出力してから再度実行すること．")
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
    st.caption("上部の a〜f ボタンを押すと，下に対応テキスト（A〜F）を出力する．")

    # 右上：a〜f ボタン
    bc = st.columns(6)
    btn_labels = ["a", "b", "c", "d", "e", "f"]
    out_map = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F"}
    for lab, col in zip(btn_labels, bc):
        with col:
            if st.button(lab.upper(), key=f"btn_right_{lab}"):
                st.session_state.right_output = out_map[lab]

    st.divider()
    # 押されたボタンに応じてテキストを表示
    if st.session_state.right_output:
        st.markdown(f"### 出力: {st.session_state.right_output}")
    else:
        st.info("まだ出力はない．a〜f のいずれかを押すこと．")

# ===== 注意事項 =====
# ・本UIではデータの読み込みおよび推薦結果の表示は行わない（要件）。
# ・ログは「完了」押下時のみ送信し，未入力がある場合は送信しない（要件）。
# ・重み・表示件数の項目は削除している（要件）
