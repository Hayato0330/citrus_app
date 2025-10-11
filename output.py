import streamlit as st
import numpy as np
import pandas as pd
from urllib.parse import quote


# ===== データ処理用関数 =====
def load_data(csv_path: str) -> pd.DataFrame | None:
    """特徴量CSVを読み込む。失敗したら None を返す。"""
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        return None


def score_items(
    df: pd.DataFrame,
    user_vec: np.ndarray,
    season_pref: str = "",
    season_boost: float = 0.03,
) -> pd.DataFrame:
    """ユーザーの入力ベクトルと特徴量からスコアを計算する（簡易版：コサイン類似度）"""
    feature_cols = ["brix", "acid", "bitter", "smell", "moisture", "elastic"]

    # 特徴量が足りない場合は処理中止
    for col in feature_cols:
        if col not in df.columns:
            st.error(f"CSVに必要なカラムがありません: {col}")
            st.stop()

    X = df[feature_cols].astype(float).values

    def normalize(v):
        return v / (np.linalg.norm(v) + 1e-8)

    user_vec = normalize(user_vec)
    X_norm = np.array([normalize(x) for x in X])

    scores = X_norm @ user_vec

    if season_pref and "season" in df.columns:
        mask = df["season"].astype(str).str.contains(season_pref)
        scores = scores + mask.astype(float) * season_boost

    df = df.copy()
    df["score"] = scores
    return df.sort_values("score", ascending=False).reset_index(drop=True)


# ===== ユーティリティ =====
def build_amazon_url(name: str) -> str:
    query = quote(f"{name} 生果 フルーツ -苗 -苗木 -のぼり -ジュース -ゼリー -缶 -本")
    return f"https://www.amazon.co.jp/s?k={query}&i=grocery"


def build_rakuten_url(name: str) -> str:
    return f"https://search.rakuten.co.jp/search/mall/{quote(name)}/"


def build_satofuru_url(name: str) -> str:
    return f"https://www.satofull.jp/search/?q={quote(name)}"


def build_twitter_share(names: list[str]) -> str:
    text = quote(f"おすすめの柑橘: {', '.join(names)} #柑橘おすすめ")
    return f"https://twitter.com/intent/tweet?text={text}"


# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果", page_icon="🍊", layout="wide")


# ===== データ取得 =====
ranked = st.session_state.get("ranked_results", None)
topk = 3

if ranked is None:
    df = load_data("citrus_features.csv")
    if df is None:
        st.stop()  # CSVがないなら終了

    # 固定のダミーユーザーベクトル
    user_vec = np.array([2, 3, 2, 3, 4, 5], dtype=float)
    season_pref = ""

    ranked = score_items(df, user_vec, season_pref=season_pref, season_boost=0.03)
    st.session_state.ranked_results = ranked


# ===== 認証状態チェック =====
is_logged_in = True  # 単体テスト用なので常にログイン済み


# ===== UI =====
st.title("🍊 あなたにおすすめの柑橘")

top_items = ranked.head(topk)
cols = st.columns(2)  # 2×2 グリッド用

for idx, row in enumerate(top_items.itertuples(), start=1):
    with cols[(idx - 1) % 2]:
        st.markdown(f"## {idx}. {getattr(row, 'Item_name', '不明')}")

        left, right = st.columns([1, 1])

        with left:
            # 画像URLが無ければダミーを利用
            image_url = getattr(row, "image_url", None) or "https://via.placeholder.com/200x150?text=No+Image"
            st.image(image_url, use_container_width=True)

            match_percent = f"{row.score*100:.1f}%"
            st.markdown(
                f"**マッチ度:** <span style='color:#f59e0b;'>{match_percent}</span>",
                unsafe_allow_html=True,
            )
            st.caption(f"季節: {getattr(row, 'season', '-')}")

        with right:
            if is_logged_in:
                st.markdown(f"[Amazonで見る]({build_amazon_url(getattr(row, 'Item_name', '不明'))})")
                st.markdown(f"[楽天で見る]({build_rakuten_url(getattr(row, 'Item_name', '不明'))})")
                st.markdown(f"[さとふるで見る]({build_satofuru_url(getattr(row, 'Item_name', '不明'))})")
            else:
                st.warning("🔒 外部リンクはログインが必要です")


# === 右下「まとめ」ブロック ===
with cols[1]:
    st.markdown("## まとめ")
    citrus_names = [getattr(r, "Item_name", "不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(citrus_names)
    st.markdown(f"[Xでシェア]({twitter_url})", unsafe_allow_html=True)

st.caption("※ マッチ度は嗜好との近さを % 表記。季節一致がある場合は加点されます。")
