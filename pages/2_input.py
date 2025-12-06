# UI刷新版（修正版：背景#FFF9ED／完了ボタン全幅／ボタン影＆押下動作／即時色反映）
# 右ボタン高さ統一／左2列の縦ライン常時表示を追加

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

# ===== 背景色・余白・タイポグラフィ・ボタン演出 =====
st.markdown(
    """
    <style>
    /* 背景色を #FFE4B5 に統一 */
    body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        background-color: #FFE4B5;
    }

    /* 全体の縦余白を詰める */
    .block-container { padding-top: 0.4rem; padding-bottom: 0.6rem; }

    /* タイトル：小さめ＋「今の文字の半分の幅」だけ下げる（= 0.8rem） */
    .block-container h1 {
        font-size: 1.6rem;
        line-height: 1.2;
        margin-top: 0.8rem;    /* 指定どおり半分だけ下げる */
        margin-bottom: 0.2rem;
    }

    /* 右カラムの小見出しの余白を控えめに */
    .block-container h3 { margin-top: 0.3rem; margin-bottom: 0.2rem; }

    /* 季節セクションの下余白を極小に（完了ボタンとの隙間を詰める） */
    .season-section { margin-bottom: 0.1rem; }

    /* ボタンのサイズ・影・押下アニメーション（全ボタン共通） */
    button[kind="secondary"], button[kind="primary"] {
        padding-top: 0.34rem !important;
        padding-bottom: 0.34rem !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.18);
        transition: transform 0.02s ease, box-shadow 0.02s ease, filter 0.02s ease;
    }
    /* へこむ動き（押下時） */
    button[kind="secondary"]:active, button[kind="primary"]:active {
        transform: translateY(1px);
        box-shadow: 0 1px 3px rgba(0,0,0,0.25);
        filter: saturate(1.05);
    }

    /* 左入力2列の間に縦ライン（中央細カラム） */
    .vline { width: 100%; height: 100%; border-left: 2px solid rgba(0,0,0,0.25); 
             min-height: 18rem; }  /* ← 追加：常時見える最小高さを確保 */
    .vline-wrap { display: flex; align-items: stretch; height: 100%; }

    /* 全幅の完了ボタン行（上詰め） */
    .submit-row { margin-top: 0.1rem; }  /* 季節ボタン直下に寄せる */

    /* === 右側ヒント用ボタン：高さと見た目の統一 === */
    .right-btns button[kind="secondary"], 
    .right-btns button[kind="primary"] {
        min-height: 3.2rem;          /* ← 追加：高さを統一 */
        display: flex;               /* 中央寄せ */
        align-items: center;
        justify-content: center;
        text-align: center;
        font-size: 0.9rem;           /* 長文でも収まりやすく */
        line-height: 1.2;
        white-space: normal;         /* 折り返し許可 */
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
def _append_simple_log(input_dict: dict) -> None:
    """
    入力値だけをログPOSTする．Secrets未設定ならスキップする．
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
        # result フィールドは送信しない（DB の result カラムには何も保存しない）
    }
    # result を含めず，入力のみで重複判定を行う
    key = str(hash(str(payload["input_json"])))
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
st.title("🍊 柑橘類の推薦システム")
# 説明キャプションは削除（上に詰める）

# セッション状態の初期化（季節 val_season を削除）
for key in [
    "val_brix", "val_acid", "val_bitterness", "val_aroma", "val_moisture", "val_texture",
    "right_output",
]:
    st.session_state.setdefault(key, None)

# ---- 即時反映ヘルパ ----
def _immediate_select(state_key: str, value):
    """選択状態を更新して即時再描画するヘルパ．（色切替の一段遅れを解消）"""
    st.session_state[state_key] = value
    st.rerun()

# ---- 入力ボタン群 ----
def scale_buttons(label: str, state_key: str):
    """
    1〜6の横並びボタンで値を選択する．
    ・選択中ボタンは常時 primary 色
    ・クリック直後に rerun して即時に色を反映する
    """
    st.write(label)
    cols = st.columns(6)
    current = st.session_state[state_key]
    for i, c in enumerate(cols, start=1):
        with c:
            if st.button(
                str(i),
                key=f"btn_{state_key}_{i}",
                type=("primary" if (current == i) else "secondary"),
                use_container_width=True,
            ):
                _immediate_select(state_key, i)

# 季節ボタンは不要になったため削除済み

# レイアウト：左＝入力（見出しなしで上詰め），右＝操作表示
left, right = st.columns(2, gap="large")

with left:
    # 2列＋中央細カラム（縦ライン）で配置
    colL, colMid, colR = st.columns([1, 0.05, 1])

    with colL:
        scale_buttons("甘さ", "val_brix")
        scale_buttons("酸味", "val_acid")
        scale_buttons("苦味", "val_bitterness")

    with colMid:
        # 常時見える縦ライン
        st.markdown('<div class="vline-wrap"><div class="vline"></div></div>', unsafe_allow_html=True)

    with colR:
        scale_buttons("香り", "val_aroma")
        scale_buttons("ジューシーさ", "val_moisture")
        scale_buttons("食感", "val_texture")

with right:
    st.subheader("柑橘ソムリエのヒント")

    # 右側ボタンをラップして高さ統一を適用
    st.markdown('<div class="right-btns">', unsafe_allow_html=True)

    bc = st.columns(5)
    btn_labels = [
        "際立つ甘さが好きな人へ",
        "ビターな大人へ",
        "香りを楽しむ人へ",
        "溢れる果汁が好きな人へ",
        "食感重視の人へ",
    ]
    out_map = {
        "際立つ甘さが好きな人へ": "甘さが際立つのは、酸味とのバランスが取れている時です。ここでは、希望の甘味の数値に対して、酸味を-2程度にしておくと自然な甘さになります！",
        "ビターな大人へ": "苦味は柑橘の白い繊維や薄皮から感じられます。この苦味を味わえると柑橘の幅が大きく広がります！大人な苦味が好きな人は、苦味を4以上にするのがおすすめです！",
        "香りを楽しむ人へ": "ここでの香りは、口に入れた時の鼻に抜ける香りを指します！味の濃さは香りの強さと大きく影響するので数字が大きいほど風味は豊かですが、味のバランスが雑になりやすいので注意が必要です。",
        "溢れる果汁が好きな人へ": "ジューシーな果実が好きな人は果汁量はもちろん大きめに入力するのがおすすめです。しかし、甘味や酸味などが小さいと水っぽい味わいになりやすいので注意が必要です！",
        "食感重視の人へ": "弾力は口にしてからの印象に大きく影響します。プチッと食感が好きな人は弾力を大きく、口に入れた瞬間にとろけるような味わいが好きな人は小さく入力するのがおすすめです。",
    }
    cur_out = st.session_state.right_output
    for lab, col in zip(btn_labels, bc):
        with col:
            if st.button(
                lab.upper(),  # 日本語はそのままだが統一のため既存仕様を維持
                key=f"btn_right_{lab}",
                type=("primary" if (cur_out == out_map[lab]) else "secondary"),
                use_container_width=True,
            ):
                _immediate_select("right_output", out_map[lab])

    st.markdown("</div>", unsafe_allow_html=True)  # /.right-btns

    st.divider()
    if st.session_state.right_output:
        st.markdown(f"### {st.session_state.right_output}")
    else:
        st.info("上のボタンを押してね")

# ===== 全幅の完了ボタン（左右カラムの外でページ全体に伸ばす） =====
st.markdown('<div class="submit-row">', unsafe_allow_html=True)
if st.button("完了", type="primary", use_container_width=True, key="btn_submit_full"):
    # 入力検証（季節 val_season と right_output はチェック対象から除外）
    missing = [
        k for k in [
            "val_brix", "val_acid", "val_bitterness", "val_aroma",
            "val_moisture", "val_texture",
        ] if st.session_state.get(k) in (None, "")
    ]
    if missing:
        st.error("未入力の項目があるため送信できない．全項目を選択してから再度実行すること．")
    else:
        # D1ログ：季節・ヒント文の項目は送信しない
        input_dict = {
            "brix": int(st.session_state.val_brix),
            "acid": int(st.session_state.val_acid),
            "bitterness": int(st.session_state.val_bitterness),
            "aroma": int(st.session_state.val_aroma),
            "moisture": int(st.session_state.val_moisture),
            "texture": int(st.session_state.val_texture),
        }
        _append_simple_log(input_dict=input_dict)

        # ★ ここから追加：app.py に渡すための情報をセッションにセット
        st.session_state["user_preferences"] = input_dict
        st.session_state["input_submitted"] = True

        st.success("入力値をログとして送信した．")

st.markdown('</div>', unsafe_allow_html=True)

# ===== 注意事項 =====
# ・本UIではデータの読み込みおよび推薦結果の表示は行わない（要件）．
# ・ログは「完了」押下時のみ送信し，未入力がある場合は送信しない（要件）．
# ・重み・表示件数の項目は削除している（要件）．
