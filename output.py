# output.py
import streamlit as st
import numpy as np
from urllib.parse import quote

# 本間のローカルにapp.pyがあるため
from app import load_data, score_items


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
    share_url = st.secrets.get("public_app_url", "")
    url_query = f"&url={quote(share_url)}" if share_url else ""
    return f"https://twitter.com/intent/tweet?text={text}{url_query}"


# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果", page_icon="🍊", layout="wide")

# ===== データ取得（input.py または ダミー） =====
ranked = st.session_state.get("ranked_results", None)
topk = 3

if ranked is None:
    try:
        df = load_data("citrus_features.csv")
        user_vec = np.array([2, 3, 2, 3, 4, 5], dtype=float)
        ranked = score_items(df, user_vec, season_pref="", season_boost=0.03)
        st.session_state.ranked_results = ranked
    except Exception as e:
        st.error(f"診断結果が見つかりません（テスト用生成にも失敗）: {e}")
        st.stop()

# ===== 認証状態チェック =====
is_logged_in = st.session_state.get("user_authenticated", True)

# ===== UI =====
st.title("🍊 あなたにおすすめの柑橘")

top_items = ranked.head(topk)
cols = st.columns(2)  # 2×2 グリッド用

for idx, row in enumerate(top_items.itertuples(), start=1):
    with cols[(idx-1) % 2]:
        st.markdown(f"## {idx}. {row.name}")

        left, right = st.columns([1, 1])

        with left:
            st.image(row.image_url or "https://via.placeholder.com/200x150?text=No+Image",
                     use_container_width=True)
            match_percent = f"{row.score*100:.1f}%"
            st.markdown(
                f"**マッチ度:** <span style='color:#f59e0b;'>{match_percent}</span>",
                unsafe_allow_html=True
            )
            st.caption(f"季節: {row.season or '-'}")

        with right:
            if is_logged_in:
                st.markdown(f"[Amazonで見る]({build_amazon_url(row.name)})")
                st.markdown(f"[楽天で見る]({build_rakuten_url(row.name)})")
                st.markdown(f"[さとふるで見る]({build_satofuru_url(row.name)})")
            else:
                st.warning("🔒 外部リンクはログインが必要です")

# === 右下「まとめ」ブロック ===
with cols[1]:
    st.markdown("## まとめ")
    if not is_logged_in:
        if st.button("アカウント登録はこちら"):
            st.switch_page("pages/2_Register.py")

    citrus_names = [r.name for r in top_items.itertuples()]
    twitter_url = build_twitter_share(citrus_names)
    st.markdown(f"[Xでシェア]({twitter_url})", unsafe_allow_html=True)

st.caption("※ マッチ度は嗜好との近さを % 表記。季節一致がある場合は加点されます。")
