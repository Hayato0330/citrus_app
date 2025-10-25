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
/* ===== 背景設定 ===== */
body {
    background-color: #FFF8F0; /* 薄オレンジ背景 */
}

/* ===== カード ===== */
.card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,.12);
    border: 1px solid #eee;
}
.card h2, .card h3 {
    color: #000;
    margin-top: 0;
}

/* ===== マッチ度 ===== */
.match-score {
    color: #f59e0b;
    font-weight: bold;
}

/* ===== 共通ボタン ===== */
.link-btn {
    display: inline-block;
    padding: 8px 14px;
    margin: 6px 0;
    border-radius: 6px;
    color: #fff !important;
    text-decoration: none;
    font-weight: 600;
    font-size: 14px;
    transition: opacity .15s;
    cursor: pointer;
}
.link-btn img {
    height: 16px;
    vertical-align: middle;
    margin-right: 6px;
}
.link-btn:hover {
    opacity: .9;
}

/* ===== 無効化ボタン ===== */
.disabled-btn {
    opacity: 0.6 !important;
    cursor: not-allowed !important;
    pointer-events: none !important;
}

/* ===== ブランドカラー ===== */
.amazon-btn { background-color: #00BFFF; }
.rakuten-btn { background-color: #BF0000; }
.satofuru-btn { background-color: #D2691E; }
.x-btn {
    background-color: #ffffff; /* 白背景 */
    color: #000 !important;    /* テキストを黒に固定 */
    border: 1px solid #ddd;    /* 輪郭を出して白背景でも目立たせる */
}

/* ===== ブランドカラー hover ===== */
.amazon-btn:hover { background-color: #87CEEB; }
.rakuten-btn:hover { background-color: #990000; }
.satofuru-btn:hover { background-color: #b85c19; }
.x-btn:hover {
    background-color: #f5f5f5; /* hover時にややグレーで反応 */
    color: #000 !important;    /* hover時も黒を維持 */
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
        scores += mask.astype(float) * season_boost
    out = df.copy()
    out["score"] = scores
    return out.sort_values("score", ascending=False).reset_index(drop=True)


# ===== SNSシェア =====
def build_twitter_share(names: list[str]) -> str:
    ranked_text = "\n".join([f"{i+1}位 {n}" for i, n in enumerate(names)])
    app_url = "https://citrusapp-ukx8zpjspw4svc7dmd5jnj.streamlit.app/"
    # ツイート本文に直接リンクを改行付きで埋め込む
    text = quote(f"おすすめの柑橘 🍊\n{ranked_text}\n#柑橘おすすめ\n{app_url}")
    return f"https://twitter.com/intent/tweet?text={text}"




# ===== データ取得 =====
ranked = st.session_state.get("ranked_results")
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
            "description": ["甘くて食べやすい定番みかん", "香り豊かで人気の柑橘", "さっぱりとした味わい"],
            "image_path": [
                "https://via.placeholder.com/200x150?text=Mikan",
                "https://via.placeholder.com/200x150?text=Ponkan",
                "https://via.placeholder.com/200x150?text=Hassaku"
            ]
        })
    user_vec = np.array([2, 3, 2, 3, 4, 5], dtype=float)
    ranked = score_items(df, user_vec)
    st.session_state.ranked_results = ranked


# ===== UI =====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果（ゲスト表示）")

top_items = ranked.head(TOPK)

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]


def render_card(i, row):
    name = getattr(row, "Item_name", "不明")
    desc = getattr(row, "description", "")
    image_url = getattr(row, "image_path", None) or "https://via.placeholder.com/200x150?text=No+Image"
    score_pct = float(getattr(row, "score", 0.0)) * 100
    html = f"""
    <div class="card">
      <h2>{i}. {name}</h2>
      <div style="display:flex;gap:20px;align-items:flex-start;">
        <div style="flex:1;">
          <img src="{image_url}" style="max-width:100%;border-radius:8px;margin-bottom:10px;">
          <p>マッチ度: <span class="match-score">{score_pct:.1f}%</span></p>
          <p style="font-size:14px;color:#333;">{desc}</p>
        </div>
        <div style="flex:1;text-align:center;">
          <!-- 無効化ボタン -->
          <div class="link-btn amazon-btn disabled-btn">
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg" alt="Amazon" style="height:16px;vertical-align:middle;margin-right:6px;">
            Amazonで見る
          </div><br>
          <div class="link-btn rakuten-btn disabled-btn">
            <img src="https://upload.wikimedia.org/wikipedia/commons/6/6a/Rakuten_Global_Brand_Logo.svg"
                 alt="Rakuten" style="height:16px;vertical-align:middle;margin-right:6px;">
            楽天で見る
          </div><br>
          <div class="link-btn satofuru-btn disabled-btn">
            <img src="https://www.satofull.jp/favicon.ico"
                 alt="さとふる" style="height:16px;vertical-align:middle;margin-right:6px;">
            さとふるで見る
          </div>
          <p style="font-size:13px;color:#666;margin-top:10px;">
            Amazon・楽天・さとふるの利用にはアカウント登録が必要です
          </p>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# カード配置
for i, row in enumerate(top_items.itertuples(), start=1):
    with quadrants[i - 1]:
        render_card(i, row)

# === 右下（Xシェア + 新規登録導線） ===
with quadrants[3]:
    names = [getattr(r, "Item_name", "不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(names)
    st.markdown(f"""
    <div class="card" style="text-align:center;">
      <h3>まとめ</h3>
      <a class="link-btn x-btn" href="{twitter_url}" target="_blank">
        <img src="https://cdn.cms-twdigitalassets.com/content/dam/about-twitter/x/brand-toolkit/logo-black.png.twimg.2560.png"
             alt="X" style="height:16px;vertical-align:middle;margin-right:6px;">
        Xでシェア
      </a>
      <p style="margin-top:15px;font-size:14px;">
        <a href="/signup" style="color:#f59e0b;font-weight:bold;text-decoration:underline;">
          👉 新規登録はこちら
        </a>
      </p>
    </div>
    """, unsafe_allow_html=True)

st.caption("※ マッチ度は嗜好との近さを % 表記。季節一致がある場合は加点されます。")
