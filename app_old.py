# app.py
# appappapp

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

# 推薦に使う標準カラム
FEATURES = ["brix", "acid", "bitterness", "aroma", "moisture", "texture"]

# 入力CSVの別名 → 標準名 マッピング
ALIASES = {
    "brix": ["brix", "sweet", "sweetness", "sugar"],
    "acid": ["acid", "acidity", "sour", "sourness"],
    "bitterness": ["bitterness", "bitter"],
    "aroma": ["aroma", "smell", "fragrance", "flavor", "flavour"],
    "moisture": ["moisture", "juicy", "juiciness"],
    "texture": ["texture", "elastic", "firmness", "pulpiness"],
}

# ===== カラム整形 =====
def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # 小文字化＆trim
    df = df.rename(columns={c: c.strip().lower() for c in df.columns})

    # season / image_url を推定
    if "season" not in df.columns:
        for cand in ["seasons", "season_pref", "in_season"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "season"})
                break
    if "image_url" not in df.columns:
        for cand in ["image", "img", "img_url", "photo_url", "picture"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "image_url"})
                break

    # 特徴量の別名を標準名へ
    for std, cands in ALIASES.items():
        if std in df.columns:
            continue
        for cand in cands:
            if cand in df.columns:
                df = df.rename(columns={cand: std})
                break

    # name / id を補完
    if "name" not in df.columns:
        for cand in ["品種名", "citrus_name", "item_name", "title"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "name"})
                break
        if "name" not in df.columns:
            df["name"] = [f"item_{i}" for i in range(len(df))]
    if "id" not in df.columns:
        df["id"] = np.arange(1, len(df) + 1)

    return df

@st.cache_data(ttl=3600)
def load_citrus_df(key: str | None = None):
    required = ("r2_account_id", "r2_access_key_id", "r2_secret_access_key", "r2_bucket")
    missing = [k for k in required if k not in st.secrets]
    if missing:
        raise RuntimeError(f"R2の接続情報が見つからない．.streamlit/secrets.toml に {missing} を設定すること．")
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{st.secrets['r2_account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=st.secrets["r2_access_key_id"],
        aws_secret_access_key=st.secrets["r2_secret_access_key"],
    )
    obj_key = key or st.secrets.get("r2_key")
    if not obj_key:
        raise RuntimeError("R2のオブジェクトキーが未指定である．入力欄にキーを入れるか，secrets['r2_key'] を設定すること．")
    obj = s3.get_object(Bucket=st.secrets["r2_bucket"], Key=obj_key)
    return pd.read_csv(BytesIO(obj["Body"].read()), encoding="utf-8-sig")

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    """常にR2から取得する．ローカルCSVは読まない（要求どおり）．"""
    df = load_citrus_df(path or None)  # UIの入力値をそのままR2キーとして使用
    df = _standardize_columns(df)

    # 必須カラム確認
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise KeyError(f"必要カラムが見つかりません: {missing} / 取得カラム: {list(df.columns)}")

    # 数値化して1〜6にクリップ
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").clip(1, 6)

    # 付帯情報整備
    if "season" not in df.columns:
        df["season"] = ""
    df["season"] = df["season"].fillna("").astype(str)

    if "image_url" not in df.columns:
        df["image_url"] = ""
    else:
        df["image_url"] = df["image_url"].fillna("").astype(str)

    return df.dropna(subset=FEATURES)

def parse_seasons(cell: str) -> List[str]:
    if not cell:
        return []
    return [s.strip().lower() for s in str(cell).split(",") if s.strip()]

def _append_log(input_dict: dict, top_rows: list[dict]) -> None:
    """
    D1へログPOSTする．同一内容の連投を避けるため，直近ペイロードをセッションに記録する．
    Secretsに log_api_url と log_api_token が無ければ何もしない．
    """
    url = st.secrets.get("log_api_url")
    token = st.secrets.get("log_api_token")
    if not url or not token:
        return  # ログAPI未設定なら静かにスキップ

    # 重複送信ガード
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": st.session_state.setdefault("sid", str(uuid.uuid4())),
        "input_json": input_dict,
        # 解析や可視化を想定し，上位のname/score/distanceのみを薄く送る
        "result": {"top": top_rows},
    }
    key = str(hash(str(payload["input_json"]) + str(payload["result"])))
    if st.session_state.get("last_log_key") == key:
        return

    try:
        r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=5)
        r.raise_for_status()
        st.session_state["last_log_key"] = key
    except Exception as e:
        # 失敗してもアプリ本体は止めない
        st.info(f"ログ送信をスキップした（理由：{e}）")

# ===== 推薦計算 =====
def score_items(
    df: pd.DataFrame,
    user_vec: np.ndarray,
    season_pref: str = "",
    weights: Dict[str, float] | None = None,
    season_boost: float = 0.03,
) -> pd.DataFrame:
    if weights is None:
        weights = {k: 1.0 for k in FEATURES}

    w = np.array([weights[k] for k in FEATURES], dtype=float)

    # 各特徴の最大差は5（1〜6スケール）を想定
    max_dist = math.sqrt(np.sum((w * 5) ** 2))

    X = df[FEATURES].to_numpy(dtype=float)
    diffs = X - user_vec[None, :]
    dists = np.sqrt(np.sum((diffs * w[None, :]) ** 2, axis=1))
    scores = 1.0 - (dists / max_dist)

    season_pref_norm = season_pref.strip().lower()
    add = np.zeros_like(scores)
    if season_pref_norm:
        match = df["season"].fillna("").map(
            lambda s: season_pref_norm in parse_seasons(s)
        ).to_numpy(dtype=bool)
        add = np.where(match, season_boost, 0.0)

    final = np.clip(scores + add, 0.0, 1.0)

    out = df.copy()
    out["distance"] = dists
    out["score"] = final
    return out.sort_values(["score", "name"], ascending=[False, True]).reset_index(drop=True)

def label_map(k: str) -> str:
    return {
        "brix": "甘さ",
        "acid": "酸味",
        "bitterness": "苦味",
        "aroma": "香り",
        "moisture": "ジューシーさ",
        "texture": "食感（しっかり）",
    }.get(k, k)

def explain_match(row: pd.Series, user_vec: np.ndarray) -> str:
    # 近さ（=差の小ささ）上位2特徴を説明
    closeness = []
    for i, f in enumerate(FEATURES):
        closeness.append((f, 1 - abs(row[f] - user_vec[i]) / 5))
    closeness.sort(key=lambda x: x[1], reverse=True)
    top2 = [f"{label_map(k)}が近い" for k, _ in closeness[:2]]
    return "・" + " / ".join(top2)

# ===== UI =====
st.title("🍊 柑橘レコメンダ（Streamlit版）")
st.write("6段階評価の嗜好から、特徴が近い柑橘をおすすめします。")

with st.sidebar:
    st.header("1) 好みを入力")
    brix     = st.slider("甘さ（brix）", 1, 6, 4)
    acid     = st.slider("酸味（acid）", 1, 6, 3)
    bitter   = st.slider("苦味（bitterness）", 1, 6, 2)
    aroma    = st.slider("香り（aroma）", 1, 6, 3)
    moisture = st.slider("ジューシーさ（moisture）", 1, 6, 4)
    texture  = st.slider("食感（しっかり）（texture）", 1, 6, 3)

    season_pref = st.selectbox("季節の希望（任意）", ["", "winter", "spring", "summer", "autumn"])

    with st.expander("重み（任意・上級者向け）"):
        w_brix     = st.number_input("甘さの重み",       0.0, 3.0, 1.0, 0.1)
        w_acid     = st.number_input("酸味の重み",       0.0, 3.0, 1.0, 0.1)
        w_bitter   = st.number_input("苦味の重み",       0.0, 3.0, 1.0, 0.1)
        w_aroma    = st.number_input("香りの重み",       0.0, 3.0, 1.0, 0.1)
        w_moisture = st.number_input("ジューシーさの重み",0.0, 3.0, 1.0, 0.1)
        w_texture  = st.number_input("食感の重み",       0.0, 3.0, 1.0, 0.1)

    topk = st.number_input("表示件数", 1, 20, 5)

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.subheader("2) データの読み込み")
    default_key = st.secrets.get("r2_key", "citrus_features.csv")
    data_file = st.text_input(
        "R2オブジェクトキー",
        value=default_key,
        help="例: citrus_features.csv または datasets/2025/citrus_features.csv．ローカルCSVは読み込まない．"
    )
    try:
        df = load_data(data_file)
        st.success(f"読み込み成功: {len(df)} 品種")
        st.dataframe(df[["name", "season"] + FEATURES], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"読み込みに失敗しました: {e}")
        st.stop()

with col_right:
    st.subheader("3) 結果")
    user_vec = np.array([brix, acid, bitter, aroma, moisture, texture], dtype=float)
    weights = {
        "brix": w_brix if "w_brix" in locals() else 1.0,
        "acid": w_acid if "w_acid" in locals() else 1.0,
        "bitterness": w_bitter if "w_bitter" in locals() else 1.0,
        "aroma": w_aroma if "w_aroma" in locals() else 1.0,
        "moisture": w_moisture if "w_moisture" in locals() else 1.0,
        "texture": w_texture if "w_texture" in locals() else 1.0,
    }

    ranked = score_items(df, user_vec, season_pref=season_pref, weights=weights)

    # ← 上位結果をD1へ一度だけ送る（同一内容の連投は抑止）
    try:
        _append_log(
            input_dict={
                "brix": int(brix), "acid": int(acid), "bitterness": int(bitter),
                "aroma": int(aroma), "moisture": int(moisture), "texture": int(texture),
                "season_pref": season_pref, "weights": weights, "topk": int(topk),
            },
            top_rows=ranked.head(int(topk))[["name", "score", "distance"]]
                .round({"score": 3, "distance": 3})
                .to_dict(orient="records"),
        )
    except Exception as _:
        pass  # 万が一の例外でもUIは継続

    for i, row in ranked.head(int(topk)).iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([1, 3])
            with c1:
                if isinstance(row.get("image_url", ""), str) and row["image_url"].strip():
                    st.image(row["image_url"], use_container_width=True)
                st.metric(label="スコア", value=f"{row['score']:.3f}")
                st.caption(f"距離: {row['distance']:.3f}")
            with c2:
                st.markdown(f"### {i+1}. {row['name']}")
                st.write(explain_match(row, user_vec))
                feat_cols = [label_map(f) for f in FEATURES]
                values = [int(row[f]) for f in FEATURES]
                show_df = pd.DataFrame([values], columns=feat_cols)
                st.dataframe(show_df, hide_index=True, use_container_width=True)
                st.caption(f"季節: {row['season'] or '-'}")

    st.divider()
    st.caption("※ スコアは 0〜1。嗜好との近さ（距離の小ささ）＋季節一致の加点で算出。")