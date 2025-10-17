# output_login.py
import streamlit as st
import numpy as np
import pandas as pd
from urllib.parse import quote


# ===== データ処理関数 =====
def load_data(csv_path: str) -> pd.DataFrame | None:
    """特徴量CSVを読み込む。失敗したら None を返す。"""
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        return None


def score_items(df: pd.DataFrame, user_vec: np.ndarray,
                season_pref: str = "", season_boost: float = 0.03) -> pd.DataFrame:
    """ユーザー入力ベクトルと特徴量からスコアを計算（コサイン類似度）"""
    feature_cols = ["brix", "acid", "bitter", "smell", "moisture", "elastic"]

    if not all(col in df.columns for col in feature_cols):
        st.error("CSVに必要な特徴量カラムが不足しています。")
        st.stop()

    X = df[feature_cols].astype(float).values

    def normalize(v):
        return v / (np.linalg.norm(v) + 1e-8)

    user_vec = normalize(user_vec)
    X_norm = np.array([normalize(x) for x in X])

    scores = X_norm @ user_vec

    # 季節一致に加点
    if season_pref and "season" in df.columns:
        mask = df["season"].astype(str).str.contains(season_pref)
        scores = scores + mask.astype(float) * season_boost

    df = df.copy()
    df["score"] = scores
    return df.sort_values("score", ascending=False).reset_index(drop=True)


# ===== ユーティリティ関数 =====
def build_amazon_url(name: str) -> str:
    query = quote(f"{name} 生果 フルーツ -苗 -苗木 -のぼり -ジュース -ゼリー -缶 -本")
    return f"https://www.amazon.co.jp/s?k={query}&i=grocery"

def build_rakuten_url(name: str) -> str:
    return f"https://search.rakuten.co.jp/search/mall/{quote(name)}/"

def build_satofuru_url(name: str) -> str:
    return f"https://www.satofull.jp/search/?q={quote(name)}"

def build_twitter_share(names: list[str]) -> str:
    # 順位付き + 改行
    ranked_text = "\n".join([f"{i+1}位 {name}" for i, name in enumerate(names)])
    text = quote(f"おすすめの柑橘 🍊\n{ranked_text}\n#柑橘おすすめ")

    share_url = st.secrets.get("public_app_url", "")
    url_query = f"&url={quote(share_url)}" if share_url else ""

    return f"https://twitter.com/intent/tweet?text={text}{url_query}"



# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果", page_icon="🍊", layout="wide")

# 背景色（薄いオレンジ）
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF8F0;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ===== データ取得 =====
ranked = st.session_state.get("ranked_results", None)
topk = 3

if ranked is None:
    df = load_data("citrus_features.csv")

    if df is None:
        # --- ダミーデータを用意 ---
        df = pd.DataFrame({
            "Item_name": ["温州みかん", "ポンカン", "はっさく"],
            "brix": [5, 4, 3],
            "acid": [2, 3, 4],
            "bitter": [1, 2, 3],
            "smell": [3, 4, 2],
            "moisture": [5, 4, 3],
            "elastic": [2, 3, 4],
            "season": ["冬", "冬〜春", "春"],
            "description": ["甘くて食べやすい定番みかん", "香り豊かで人気の柑橘", "さっぱりとした味わい"],
            "image_path": [
                "https://via.placeholder.com/200x150?text=Mikan",
                "https://via.placeholder.com/200x150?text=Ponkan",
                "https://via.placeholder.com/200x150?text=Hassaku",
            ]
        })

    # ダミー入力ベクトル
    user_vec = np.array([2, 3, 2, 3, 4, 5], dtype=float)
    season_pref = ""

    ranked = score_items(df, user_vec, season_pref=season_pref, season_boost=0.03)
    st.session_state.ranked_results = ranked


# ===== UI =====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果")

top_items = ranked.head(topk)

# 四象限レイアウト
cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]

for idx, row in enumerate(top_items.itertuples(), start=1):
    with quadrants[idx - 1]:
        st.markdown(f"#### {idx}. {row.name}")

        image_url = getattr(row, "image_path", None) or "https://via.placeholder.com/200x150?text=No+Image"
        st.image(image_url, use_container_width=True)

        match_percent = f"{row.score*100:.1f}%"
        st.markdown(
            f"**マッチ度:** <span style='color:#f59e0b;'>{match_percent}</span>",
            unsafe_allow_html=True
        )

        # st.caption(f"季節: {getattr(row, 'season', '-')}")
        st.caption(getattr(row, "description", ""))

        # 外部リンク
        st.markdown(f"[Amazonで見る]({build_amazon_url(row.name)})", unsafe_allow_html=True)
        st.markdown(f"[楽天で見る]({build_rakuten_url(row.name)})", unsafe_allow_html=True)
        st.markdown(f"[さとふるで見る]({build_satofuru_url(row.name)})", unsafe_allow_html=True)


# === 右下「まとめ」ブロック ===
with quadrants[3]:
    st.markdown("#### まとめ")
    citrus_names = [r.name for r in top_items.itertuples()]
    twitter_url = build_twitter_share(citrus_names)
    st.markdown(f"[Xでシェアする]({twitter_url})", unsafe_allow_html=True)

st.caption("※ マッチ度は嗜好との近さを % 表記。季節一致がある場合は加点されます。")
