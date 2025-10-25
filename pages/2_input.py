# UI刷新版（修正版：縦ライン追加／隙間詰め／即時色反映）

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

# ===== 背景色・余白・タイポグラフィ調整 =====
st.markdown(
    """
    <style>
    /* 背景色を #ffd700 で統一 */
    body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        background-color: #ffd700;
    }
    /* 全体の縦余白を詰める */
    .block-container { padding-top: 0.4rem; padding-bottom: 0.6rem; }

    /* タイトル：小さめ＋フォントサイズの半分だけ下げる（= 0.8rem） */
    .block-container h1 {
        font-size: 1.6rem;
        line-height: 1.2;
        margin-top: 0.8rem;   /* 指定どおり下げる */
        margin-bottom: 0.2rem;
    }

    /* 右カラム見出しの余白を控えめに */
    .block-container h3 { margin-top: 0.3rem; margin-bottom: 0.2rem; }

    /* 季節セクションと完了ボタン間の隙間を詰める */
    .season-section { margin-bottom: 0.2rem; }
    hr { margin: 0.2rem 0 !important; }

    /* ボタンの高さ抑制（縦詰め） */
    button[kind="secondary"], button[kind="primary"] {
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
    }

    /* 左入力2列の間に縦ライン（中央細カラムを線にする） */
    .vline { width: 100%; height: 100%; border-left: 2px solid rgba(0,0,0,0.35); }
    .vline-wrap { display: flex; align-items: stretch; height: 100%; }
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
# 説明キャプションは削除（詰め）

# セッション状態の初期化
for key in [
    "val_brix", "val_acid", "val_bitterness", "val_aroma", "val_moisture", "val_texture",
    "val_season", "right_output",
]:
    st.session_state.setdefault(key, None)

def _immediate_select(state_key: str, value):
    """選択状態を更新して即時再描画するヘルパ．"""
    st.session_state[state_key] = value
    # クリック直後に色を反映させるために即時再実行
    st.rerun()

def scale_buttons(label: str, state_key: str):
    """
    1〜6の横並びボタンで値を選択する．
    ・選択中ボタンは常時 primary 色
    ・クリック時に即 rerun してその場で色が反映される
    """
    st.write(label)
    cols = st.columns(6)
    current = st.session_state[state_key]
    for i, c in enumerate(cols, start=1):
        with c:
            # type は現状態に基づく．押されたら即時 rerun して再描画で色反映．
            if st.button(
                str(i),
                key=f"btn_{state_key}_{i}",
                type=("primary" if (current == i) else "secondary"),
                use_container_width=True,
            ):
                _immediate_select(state_key, i)

def season_buttons(state_key: str = "val_season"):
    """
    季節の4ボタン．選択中のみ primary．
    クリック時に即 rerun し，色が一段遅れにならないようにする．
    """
    st.markdown('<div class="season-section">', unsafe_allow_html=True)
    st.write("季節の希望")
    cols = st.columns(4)
    cur = st.session_state[state_key]
    seasons = [("winter", "冬"), ("spring", "春"), ("summer", "夏"), ("autumn", "秋")]
    for (code, label), c in zip(seasons, cols):
        with c:
            if st.button(
                label,
                key=f"btn_season_{code}",
                type=("primary" if (cur == code) else "secondary"),
                use_container_width=True,
            ):
                _immediate_select(state_key, code)
    st.markdown("</div>", unsafe_allow_html=True)

# レイアウト：左＝入力（見出しなしで上詰め），右＝操作表示
left, right = st.columns(2, gap="large")

with left:
    # 2列＋中央細カラム（縦ライン）で配置
    colL, colMid, colR = st.columns([1, 0.05, 1])

    with colL:
        scale_buttons("甘さ（brix）", "val_brix")
        scale_buttons("酸味（acid）", "val_acid")
        scale_buttons("苦味（bitterness）", "val_bitterness")

    with colMid:
        # 高さを自然に伸ばすため，ラッパーを使って縦ラインを描画
        st.markdown('<div class="vline-wrap"><div class="vline"></div></div>', unsafe_allow_html=True)

    with colR:
        scale_buttons("香り（aroma）", "val_aroma")
        scale_buttons("ジューシーさ（moisture）", "val_moisture")
        scale_buttons("食感（しっかり）（texture）", "val_texture")

    # 季節ボタン（セクション下の余白は極小）
    season_buttons("val_season")

    # 区切り線は挿入しない（隙間発生を避ける）
    # 完了ボタンを直下に配置し，さらに上方向に寄せるため余白を置かない
    if st.button("完了", type="primary", use_container_width=True):
        # 入力検証
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

    # a〜f ボタン（クリックで即 rerun → 色即時反映）
    bc = st.columns(6)
    btn_labels = ["a", "b", "c", "d", "e", "f"]
    out_map = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F"}
    cur_out = st.session_state.right_output
    for lab, col in zip(btn_labels, bc):
        with col:
            if st.button(
                lab.upper(),
                key=f"btn_right_{lab}",
                type=("primary" if (cur_out == out_map[lab]) else "secondary"),
                use_container_width=True,
            ):
                _immediate_select("right_output", out_map[lab])

    st.divider()
    if st.session_state.right_output:
        st.markdown(f"### 出力: {st.session_state.right_output}")
    else:
        st.info("まだ出力はない．a〜f のいずれかを押すこと．")

# ===== 注意事項 =====
# ・本UIではデータの読み込みおよび推薦結果の表示は行わない（要件）．
# ・ログは「完了」押下時のみ送信し，未入力がある場合は送信しない（要件）．
# ・重み・表示件数の項目は削除している（要件）．
