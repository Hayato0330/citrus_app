# UI刷新版（修正版：詰め調整＋タイトル位置調整＋即時色反映）

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
    /* 全体の縦余白を詰める */
    .block-container { padding-top: 0.4rem; padding-bottom: 0.6rem; }
    /* タイトル: 文字を小さくし，フォントサイズの半分だけ下げる（= 0.8rem） */
    .block-container h1 {
        font-size: 1.6rem;
        line-height: 1.2;
        margin-top: 0.8rem;   /* ← 指定：今の文字の半分の幅だけ下に下げる */
        margin-bottom: 0.4rem;
    }
    /* 小見出しの上下マージン微調整（右カラム用） */
    .block-container h3 {
        margin-top: 0.4rem;
        margin-bottom: 0.4rem;
    }
    /* ボタンの横詰め＆高さ調整 */
    button[kind="secondary"], button[kind="primary"] {
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
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

# ===== UI =====
st.title("🍊 柑橘レコメンダ（UI刷新版）")
# 指定により説明キャプションは非表示（その分詰める）

# セッション状態の初期化
for key in [
    "val_brix", "val_acid", "val_bitterness", "val_aroma", "val_moisture", "val_texture",
    "val_season", "right_output",
]:
    st.session_state.setdefault(key, None)

def scale_buttons(label: str, state_key: str):
    """
    1〜6の横並びボタンで値を選択する．
    ・選択中ボタンは常時強調（primary）
    ・クリックした瞬間にも色が反映されるよう，pressed を優先して描画する
    """
    st.write(label)
    cols = st.columns(6)
    current = st.session_state[state_key]
    for i, c in enumerate(cols, start=1):
        with c:
            pressed = st.button(
                str(i),
                key=f"btn_{state_key}_{i}",
                type=("primary" if (current == i) else "secondary"),
                use_container_width=True,
            )
            if pressed:
                st.session_state[state_key] = i
                current = i  # 直後のループ以降で即時反映

def season_buttons(state_key: str = "val_season"):
    """
    季節の4ボタン．選択中のみ常時強調（primary）．
    クリック時点で即時色反映するため，pressed 後に current を更新する．
    """
    st.write("季節の希望")
    cols = st.columns(4)
    cur = st.session_state[state_key]
    seasons = [("winter", "冬"), ("spring", "春"), ("summer", "夏"), ("autumn", "秋")]
    for (code, label), c in zip(seasons, cols):
        with c:
            pressed = st.button(
                label,
                key=f"btn_season_{code}",
                type=("primary" if (cur == code) else "secondary"),
                use_container_width=True,
            )
            if pressed:
                st.session_state[state_key] = code
                cur = code  # 即時反映

# レイアウト：左＝入力（見出しは非表示で上詰め），右＝操作表示
left, right = st.columns(2, gap="large")

with left:
    # 指定により「入力（左側）」は非表示（その分上に詰める）

    # 2列グリッドに配置（スクロール不要）
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
    st.caption("a〜f ボタンを押すと，下に対応テキスト（A〜F）を出力する．")

    # a〜f ボタン（クリック時点で即時色反映）
    bc = st.columns(6)
    btn_labels = ["a", "b", "c", "d", "e", "f"]
    out_map = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F"}
    cur_out = st.session_state.right_output
    for lab, col in zip(btn_labels, bc):
        with col:
            pressed = st.button(
                lab.upper(),
                key=f"btn_right_{lab}",
                type=("primary" if (cur_out == out_map[lab]) else "secondary"),
                use_container_width=True,
            )
            if pressed:
                st.session_state.right_output = out_map[lab]
                cur_out = out_map[lab]  # 即時反映

    st.divider()
    if st.session_state.right_output:
        st.markdown(f"### 出力: {st.session_state.right_output}")
    else:
        st.info("まだ出力はない．a〜f のいずれかを押すこと．")

# ===== 注意事項 =====
# ・本UIではデータの読み込みおよび推薦結果の表示は行わない（要件）．
# ・ログは「完了」押下時のみ送信し，未入力がある場合は送信しない（要件）．
# ・重み・表示件数の項目は削除している（要件）．
