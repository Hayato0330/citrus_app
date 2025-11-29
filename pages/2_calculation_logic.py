# calculation_logic.py
# app.pyをメインの関数として，ページ遷移を行っています．現在は1_top.pyから，2_input.pyへの遷移が可能になっています．ここから2_input.pyから，3_output_nologin.pyへの遷移をapp.pyのなかで行いたいです．そのために，2_input.pyで行える入力(甘さ，酸味，苦味，香り，ジューシーさ，食感のユーザーの好みの1~6の整数値と，希望の季節を表す(winter, spring, summer, autumnのいずれか)の文字列)を2_calculation_logic.pyの入力として与えます．2_calculation_logic.pyで得られるIDの出力を3_output_nologin.pyの入力として与え，csvファイルを読み込む

import math
from typing import List, Dict
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st
import boto3

# 柑橘の特徴量として使うカラム名
FEATURES = ["brix", "acid", "bitterness", "aroma", "moisture", "texture"]

# 入力CSVの別名 → 標準名マッピング
ALIASES = {
    "brix": ["brix", "sweet", "sweetness", "sugar"],
    "acid": ["acid", "acidity", "sour", "sourness"],
    "bitterness": ["bitterness", "bitter"],
    "aroma": ["aroma", "smell", "fragrance", "flavor", "flavour"],
    "moisture": ["moisture", "juicy", "juiciness"],
    "texture": ["texture", "elastic", "firmness", "pulpiness"],
}


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """CSVのカラム名を標準化し，idカラムを補完する．"""
    # 小文字化＆前後の空白除去
    df = df.rename(columns={c: c.strip().lower() for c in df.columns})

    # season を推定
    if "season" not in df.columns:
        for cand in ["seasons", "season_pref", "in_season"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "season"})
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


def parse_seasons(cell: str) -> List[str]:
    """seasonセルをカンマ区切りで分割し，小文字リストにする．"""
    if not cell:
        return []
    return [s.strip().lower() for s in str(cell).split(",") if s.strip()]


# ===== R2 からの読み込み部分（app_old.py と同じ思想） =====

@st.cache_data(ttl=3600)
def _load_citrus_raw_from_r2(key: str | None = None) -> pd.DataFrame:
    """
    Cloudflare R2 から生のCSVを読み込む．
    secrets.toml の設定は app_old.py と同じものを前提とする．
    """
    required = ("r2_account_id", "r2_access_key_id", "r2_secret_access_key", "r2_bucket")
    missing = [k for k in required if k not in st.secrets]
    if missing:
        raise RuntimeError(
            f"R2の接続情報が見つからない．.streamlit/secrets.toml に {missing} を設定すること．"
        )

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{st.secrets['r2_account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=st.secrets["r2_access_key_id"],
        aws_secret_access_key=st.secrets["r2_secret_access_key"],
    )

    obj_key = key or st.secrets.get("r2_key")
    if not obj_key:
        raise RuntimeError(
            "R2のオブジェクトキーが未指定である．r2_key を secrets.toml に設定すること．"
        )

    obj = s3.get_object(Bucket=st.secrets["r2_bucket"], Key=obj_key)
    return pd.read_csv(BytesIO(obj["Body"].read()), encoding="utf-8-sig")


@st.cache_data
def _prepare_dataframe(r2_key: str | None = None) -> pd.DataFrame:
    """
    R2 からCSVを読み込み，特徴量と season 等を整えた DataFrame を返す．
    """
    df = _load_citrus_raw_from_r2(r2_key)
    df = _standardize_columns(df)

    # 必須カラム確認
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise KeyError(f"必要カラムが見つからない: {missing} / 取得カラム: {list(df.columns)}")

    # 数値化して1〜6にクリップ
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").clip(1, 6)

    # season を文字列で用意
    if "season" not in df.columns:
        df["season"] = ""
    df["season"] = df["season"].fillna("").astype(str)

    # 特徴量に欠損がある行は落とす
    df = df.dropna(subset=FEATURES)

    return df


# ===== 類似度計算 =====

def score_items(
    df: pd.DataFrame,
    user_vec: np.ndarray,
    season_pref: str = "",
    weights: Dict[str, float] | None = None,
    season_boost: float = 0.03,
) -> pd.DataFrame:
    """
    類似度（スコア）を計算して降順ソートしたDataFrameを返す．

    - user_vec: [brix, acid, bitterness, aroma, moisture, texture] の6次元ベクトル
    - season_pref: "winter" などの希望季節（小文字・大文字は無視される）
    """
    if weights is None:
        weights = {k: 1.0 for k in FEATURES}

    # 特徴ごとの重みベクトル
    w = np.array([weights[k] for k in FEATURES], dtype=float)

    # 各特徴が1〜6スケールで最大差5を取ると仮定したときの最大距離
    max_dist = math.sqrt(np.sum((w * 5) ** 2))

    # 特徴行列
    X = df[FEATURES].to_numpy(dtype=float)

    # ユーザベクトルとの差
    diffs = X - user_vec[None, :]

    # 重み付きユークリッド距離
    dists = np.sqrt(np.sum((diffs * w[None, :]) ** 2, axis=1))

    # 距離から類似度スコアへ変換（0〜1）
    scores = 1.0 - (dists / max_dist)

    # 季節希望が一致する行には season_boost を加点
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

    # スコア降順，名前昇順でソート
    return out.sort_values(["score", "name"], ascending=[False, True]).reset_index(drop=True)


# ===== 外部公開用：上位3品種IDを返す関数 =====

def calculate_top3_ids(
    sweetness: int,
    sourness: int,
    bitterness: int,
    aroma: int,
    juiciness: int,
    texture: int,
    season_pref: str,
    *,
    r2_key: str | None = None,
) -> List[int]:
    """
    ユーザー嗜好と季節希望から，上位3品種のIDリストを返すメイン関数．

    引数：
        sweetness  : 甘さ（1〜6）
        sourness   : 酸味（1〜6）
        bitterness : 苦味（1〜6）
        aroma      : 香り（1〜6）
        juiciness  : ジューシーさ（1〜6）
        texture    : 食感（1〜6）
        season_pref: "winter", "spring", "summer", "autumn" のいずれか
        r2_key     : R2 のオブジェクトキー（省略時は secrets["r2_key"] を使用）

    戻り値：
        上位3件（行数が3未満ならその分だけ）の品種IDを格納したリスト
    """
    # R2 から特徴量を取得
    df = _prepare_dataframe(r2_key)

    # ユーザー嗜好ベクトル（app_old.py と同じ並び）
    user_vec = np.array(
        [sweetness, sourness, bitterness, aroma, juiciness, texture],
        dtype=float,
    )

    # 重みはとりあえず全て1．必要になったら引数に出してもよい
    weights = {k: 1.0 for k in FEATURES}

    ranked = score_items(
        df,
        user_vec,
        season_pref=season_pref,
        weights=weights,
    )

    # 上位3件のidをリストで返す（行数が足りない場合はその分だけ）
    top_ids = ranked["id"].head(3).tolist()
    return top_ids
