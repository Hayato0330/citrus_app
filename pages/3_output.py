# output_nologin.py
import streamlit as st
import numpy as np
import pandas as pd
from urllib.parse import quote
import textwrap

# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果（ログインなし）", page_icon="🍊", layout="wide")

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
    if not all(col in df.columns for col in feature_cols):
        st.error("CSVに必要な特徴量カラムが不足しています。")
        st.stop()

    X = df[feature_cols].astype(float).values
    def normalize(v): return v / (np.linalg.norm(v) + 1e-8)
    user_vec = normalize(user_vec)
    Xn = np.array([normalize(x) for x in X])
    scores = Xn @ user_vec

    if season_pref and "season" in df.columns:
        mask = df["season"].astype(str).str.contains(season_pref)
        scores = scores + mask.astype(float) * season_boost

    out = df.copy()
    out["score"] = scores
    return out.sort_values("score", ascending=False).reset_index(drop=True)


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
st.markdown("### 🍊 柑橘おすすめ診断 - 結果（ログインなし）")

top_items = ranked.head(TOPK)

# 四象限レイアウト
cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]


def render_card(idx: int, row):
    name = getattr(row, "Item_name", "不明")
    desc = getattr(row, "description", "")
    image_url = getattr(row, "image_path", None) or "https://via.placeholder.com/200x150?text=No+Image"
    score_pct = float(getattr(row, "score", 0.0)) * 100.0

    html = f"""
    <div class="card">
      <h2>{idx}. {name}</h2>
      <div style="display:flex;gap:20px;align-items:flex-start;">
        <div style="flex:1;">
          <div style="padding:10px;border:1px solid #ddd;border-radius:8px;background:#fafafa;margin-bottom:10px;">
            <p style="margin:0;color:#333;font-size:14px;">{desc}</p>
          </div>
          <p style="margin:6px 0;">マッチ度: <span class="match-score">{score_pct:.1f}%</span></p>
        </div>
        <div style="flex:1;text-align:center;">
          <a class="link-btn" href="pages/2_Register.py" target="_self">🔒 Amazon</a><br>
          <a class="link-btn" href="pages/2_Register.py" target="_self">🔒 楽天</a><br>
          <a class="link-btn" href="pages/2_Register.py" target="_self">🔒 さとふる</a>
          <p style="font-size:12px;color:#666;margin-top:8px;">※利用には新規登録が必要です</p>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


for idx, row in enumerate(top_items.itertuples(), start=1):
    with quadrants[idx - 1]:
        render_card(idx, row)


# === 右下「まとめ」ブロック ===
with quadrants[3]:
    names = [getattr(r, "Item_name", "不明") for r in top_items.itertuples()]
    text = quote("おすすめの柑橘 🍊\n" + "\n".join([f"{i+1}位 {n}" for i, n in enumerate(names)]) + "\n#柑橘おすすめ")
    twitter_url = f"https://twitter.com/intent/tweet?text={text}"

    st.markdown(f"""
    <div class="card" style="text-align:center;">
      <h3>まとめ</h3>
      <a class="link-btn" href="{twitter_url}" target="_blank">Xでシェアする</a>
    </div>
    """, unsafe_allow_html=True)

st.caption("※ マッチ度は嗜好との近さを % 表記。季節一致がある場合は加点されます。")
