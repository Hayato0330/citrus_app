# UI刷新版（修正版：スクロール不要＋背景色統一＋タイトル縮小＋選択ボタン常時強調＋選択数表示削除）

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

# ===== 背景色と余白・タイポグラフィ調整 =====
st.markdown(
    """
    <style>
    /* 背景色を #ffd700 で統一 */
    body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        background-color: #ffd700;
    }
    /* 余白をやや詰めて縦方向の高さを節約 */
    .block-container { padding-top: 0.8rem; padding-bottom: 0.8rem; }
    /* タイトルを小さくする（st.title -> h1） */
    .block-container h1 {
        font-size: 1.6rem;
        line-height: 1.2;
        margin-bottom: 0.4rem;
    }
    /* 小見出しのマージン微調整 */
    .block-container h3 {
        margin-top: 0.6rem;
        margin-bottom: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 推薦に使う標準カラム（互換用）
FEATURES = ["brix", "acid", "bitterness", "aroma", "moisture", "texture"]

# 入力CSVの別名 → 標準名 マッピング（互換用）
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
    入力値と出力値だけをログPOSTする．Secrets未設定ならスキップする．
    直近の重複送信は抑止する．
    """
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
    """
    1〜6の横並びボタンで値を選択する．選択中の値は常時強調表示（primary色）にする．
    選択値は session_state[state_key] に格納する．
    """
    st.write(label)
    cols = st.columns(6)
    current = st.session_state[state_key]
    for i, c in enumerate(cols, start=1):
        with c:
            # 選択中のボタンだけ type="primary" で常時強調
            btn_pressed = st.button(
                str(i),
                key=f"btn_{state_key}_{i}",
                type=("primary" if current == i else "secondary"),
                use_container_width=True,
            )
            if btn_pressed:
                st.session_state[state_key] = i

def season_buttons(state_key: str = "val_season"):
    """
    季節の4ボタン．選択中のみ常時強調（primary）．
    """
    st.write("季節の希望")
    cols = st.columns(4)
    seasons = [("winter", "冬"), ("spring", "春"), ("summer", "夏"), ("autumn", "秋")]
    cur = st.session_state[state_key]
    for (code, label), c in zip(seasons, cols):
        with c:
            pressed = st.button(
                label,
                key=f"btn_season_{code}",
                type=("primary" if cur == code else "secondary"),
                use_container_width=True,
            )
            if pressed:
                st.session_state[state_key] = code

# レイアウト：左＝入力（2列グリッド），右＝操作表示
left, right = st.columns(2, gap="large")

with left:
    st.subheader("入力（左側）")

    # ===== スクロール不要化：2列グリッドに再配置 =====
    colL, colR = st.columns(2)
    with colL:
        scale_buttons("甘さ（brix）", "val_brix")
        scale_buttons("酸味（acid）", "val_acid")
        scale_buttons("苦味（bitterness）", "val_bitterness")
    with colR:
        scale_buttons("香り（aroma）", "val_aroma")
        scale_buttons("ジューシーさ（moisture）", "val_moisture")
        scale_buttons("食感（しっかり）（texture）", "val_texture")

    # 季節ボタンは2列の下にまとめる
    season_buttons("val_season")

    st.divider()
    # 左下：完了ボタン（押下時のみログ記録）
    if st.button("完了", type="primary", use_container_width=True):
        # 入力検証（未入力があればエラー）
        missing = [
            k for k in [
                "val_brix", "val_acid", "val_bitterness", "val_aroma",
                "val_moisture", "val_texture", "val_season", "right_output",
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

    # 右上：a〜f ボタン（選択中は常時強調）
    bc = st.columns(6)
    btn_labels = ["a", "b", "c", "d", "e", "f"]
    out_map = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F"}
    cur_out = st.session_state.right_output
    for lab, col in zip(btn_labels, bc):
        with col:
            pressed = st.button(
                lab.upper(),
                key=f"btn_right_{lab}",
                type=("primary" if cur_out == out_map[lab] else "secondary"),
                use_container_width=True,
            )
            if pressed:
                st.session_state.right_output = out_map[lab]
                cur_out = st.session_state.right_output  # 直後の描画に反映

    st.divider()
    # 押されたボタンに応じてテキストを表示
    if st.session_state.right_output:
        st.markdown(f"### 出力: {st.session_state.right_output}")
    else:
        st.info("まだ出力はない．a〜f のいずれかを押すこと．")

# ===== 注意事項 =====
# ・本UIではデータの読み込みおよび推薦結果の表示は行わない（要件）．
# ・ログは「完了」押下時のみ送信し，未入力がある場合は送信しない（要件）．
# ・重み・表示件数の項目は削除している（要件）．

