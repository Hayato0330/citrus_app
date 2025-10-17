# output_login.py
import streamlit as st
import numpy as np
import pandas as pd
from urllib.parse import quote
import textwrap

# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果", page_icon="🍊", layout="wide")

# ===== CSS =====
st.markdown(textwrap.dedent("""
<style>
body {
    background-color: #FFF8F0; /* 薄オレンジ背景 */
}
.card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,.12);
    border: 1px solid #eee;
}
.card h2, .card h3 {
    color: #000;  /* 品種名や見出しは黒 */
    margin-top: 0;
}
.match-score {
    color: #f59e0b; /* マッチ度はオレンジ */
    font-weight: bold;
}
.link-btn {
    display: inline-block;
    padding: 8px 14px;
    margin: 6px 0;
    border-radius: 6px;
    background: #22c55e;
    color: #fff !important;
    text-decoration: none;
    font-weight: 600;
    font-size: 14px;
    transition: opacity .15s;
}
.link-btn:hover {
    opacity: .9;
}
</style>
"""), unsafe_allow_html=True)

# ===== データ処理関数 =====
def load_data(csv_path: str) -> pd.DataFrame | None:
    try:
        return pd.read_csv(csv_path)
    except Exception:
        return None

def score_items(df: pd.DataFrame, user_vec: np.ndarray,
                season_pref: str = "", season_boost: float = 0.03) -> pd.DataFrame:
    feature_cols = ["brix", "acid", "bitter", "smell", "moisture", "elastic"]
    X = df[feature_cols].astype(float).values

    def normalize(v):
        return v / (np.linalg.norm(v) + 1e-8)

    user_vec = normalize(user_vec)
    Xn = np.array([normalize(x) for x in X])
    scores = Xn @ user_vec

    if season_pref and "season" in df.columns:
        mask = df["season"].astype(str).str.contains(season_pref)
        scores = scores + mask.astype(float) * season_boost

    out = df.copy()
    out["score"] = scores
    return out.sort_values("score", ascending=False).reset_index(drop=True)

# ===== 外部リンク =====
def build_amazon_url(name: str) -> str:
    q = quote(f"{name} 生果 フルーツ -苗 -苗木 -のぼり -ジュース -ゼリー -缶 -本")
    return f"https://www.amazon.co.jp/s?k={q}&i=grocery"

def build_rakuten_url(name: str) -> str:
    return f"https://search.rakuten.co.jp/search/mall/{quote(name)}/"

def build_satofuru_url(name: str) -> str:
    return f"https://www.satofull.jp/search/?q={quote(name)}"

def build_twitter_share(names: list[str]) -> str:
    lines = [f"{i+1}位 {nm}" for i, nm in enumerate(names)]
    text = f"おすすめの柑橘 🍊\n" + "\n".join(lines) + "\n#柑橘おすすめ"
    app_url = st.secrets.get("public_app_url", "")
    url_q = f"&url={quote(app_url)}" if app_url else ""
    return f"https://twitter.com/intent/tweet?text={quote(text)}{url_q}"

# ===== データ取得 =====
ranked = st.session_state.get("ranked_results", None)
TOPK = 3

if ranked is None:
    df = load_data("citrus_features.csv")
    if df is None:
        # ダミーデータ
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
    user_vec = np.array([2, 3, 2, 3, 4, 5], dtype=float)
    ranked = score_items(df, user_vec, season_pref="", season_boost=0.03)
    st.session_state.ranked_results = ranked

# ===== UI =====
st.title("🍊 柑橘おすすめ診断 - 結果")

top_items = ranked.head(TOPK)

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]

for idx, row in enumerate(top_items.itertuples(), start=1):
    with quadrants[idx - 1]:
        name = getattr(row, "Item_name", "不明")
        desc = getattr(row, "description", "")
        image_url = getattr(row, "image_path", None) or "https://via.placeholder.com/200x150?text=No+Image"
        score_pct = float(getattr(row, "score", 0.0)) * 100.0

        html = f"""
        <div class="card">
          <h2>{idx}. {name}</h2>
          <div style="display:flex;gap:20px;align-items:flex-start;">
            <!-- 左列：説明とマッチ度 -->
            <div style="flex:1;">
              <img src="{image_url}" style="width:100%;max-width:200px;border-radius:8px;margin-bottom:10px;">
              <p style="color:#333;margin:4px 0;">{desc}</p>
              <p style="margin:4px 0;">マッチ度: <span class="match-score">{score_pct:.1f}%</span></p>
            </div>
            <!-- 右列：ボタン -->
            <div style="flex:1;text-align:center;">
              <a class="link-btn" href="{build_amazon_url(name)}" target="_blank">Amazon</a><br>
              <a class="link-btn" href="{build_rakuten_url(name)}" target="_blank">楽天</a><br>
              <a class="link-btn" href="{build_satofuru_url(name)}" target="_blank">さとふる</a>
            </div>
          </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

# まとめ（右下）
with quadrants[3]:
    names_for_share = [getattr(r, "Item_name", "不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(names_for_share)
    html = f"""
    <div class="card" style="text-align:center;">
      <h3>まとめ</h3>
      <a class="link-btn" href="{twitter_url}" target="_blank">Xでシェアする</a>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

st.caption("※ マッチ度は嗜好との近さを % 表記。季節一致がある場合は加点されます。")
