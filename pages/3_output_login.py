import streamlit as st
import numpy as np
import pandas as pd
from urllib.parse import quote
import textwrap

# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果（ログイン）", page_icon="🍊", layout="wide")

# ===== CSS =====
st.markdown(textwrap.dedent("""
<style>
/* 全体背景 */
body {
    background-color: #FFF8F0; /* 薄オレンジ背景 */
}

/* カードデザイン */
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

/* マッチ度 */
.match-score {
    color: #f59e0b;
    font-weight: bold;
}

/* 共通ボタン */
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

/* ブランドごとのカラー */
.amazon-btn { background-color: #000000; }  /* 黒背景 + 白ロゴ */
.amazon-btn:hover { background-color: #222222; }

.rakuten-btn { background-color: #BF0000; }
.rakuten-btn:hover { background-color: #990000; }

.satofuru-btn { background-color: #D2691E; }
.satofuru-btn:hover { background-color: #b85c19; }

.x-btn { background-color: #000000; }
.x-btn:hover { background-color: #222222; }
</style>
"""), unsafe_allow_html=True)


# ===== データ処理関数 =====
def load_data(csv_path: str) -> pd.DataFrame | None:
    """CSV読み込み（失敗時はNone）"""
    try:
        return pd.read_csv(csv_path)
    except Exception:
        return None

def score_items(df: pd.DataFrame, user_vec: np.ndarray,
                season_pref: str = "", season_boost: float = 0.03) -> pd.DataFrame:
    """コサイン類似度でマッチ度を計算"""
    feature_cols = ["brix", "acid", "bitter", "smell", "moisture", "elastic"]
    if not all(col in df.columns for col in feature_cols):
        st.error("CSVに必要な特徴量カラムが不足しています。")
        st.stop()

    X = df[feature_cols].astype(float).values

    def normalize(v): return v / (np.linalg.norm(v) + 1e-8)
    user_vec = normalize(user_vec)
    X_norm = np.array([normalize(x) for x in X])
    scores = X_norm @ user_vec

    # 季節一致補正
    if season_pref and "season" in df.columns:
        mask = df["season"].astype(str).str.contains(season_pref)
        scores += mask.astype(float) * season_boost

    out = df.copy()
    out["score"] = scores
    return out.sort_values("score", ascending=False).reset_index(drop=True)


# ===== SNSシェア =====
def build_twitter_share(names: list[str]) -> str:
    """順位付きでツイート内容を構成"""
    ranked_text = "\n".join([f"{i+1}位 {n}" for i, n in enumerate(names)])
    text = quote(f"おすすめの柑橘 🍊\n{ranked_text}\n#柑橘おすすめ")
    share_url = st.secrets.get("public_app_url", "")
    url_query = f"&url={quote(share_url)}" if share_url else ""
    return f"https://twitter.com/intent/tweet?text={text}{url_query}"


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
st.markdown("### 🍊 柑橘おすすめ診断 - 結果")

top_items = ranked.head(TOPK)

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]


def render_card(i, row):
    """品種カードのレンダリング"""
    name = getattr(row, "Item_name", "不明")
    desc = getattr(row, "description", "")
    image_url = getattr(row, "image_path", None) or "https://via.placeholder.com/200x150?text=No+Image"
    score_pct = float(getattr(row, "score", 0.0)) * 100

    html = f"""
    <div class="card">
      <h2>{i}. {name}</h2>
      <div style="display:flex;gap:20px;align-items:flex-start;">
        <!-- 左列 -->
        <div style="flex:1;">
          <img src="{image_url}" style="max-width:100%;border-radius:8px;margin-bottom:10px;">
          <p>マッチ度: <span class="match-score">{score_pct:.1f}%</span></p>
          <p style="font-size:14px;color:#333;">{desc}</p>
        </div>
        <!-- 右列（有効なリンク） -->
        <div style="flex:1;text-align:center;">
          <a class="link-btn amazon-btn" href="https://www.amazon.co.jp" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo_white.svg" alt="Amazon">Amazonで見る
          </a><br>
          <a class="link-btn rakuten-btn" href="https://www.rakuten.co.jp" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/6/6a/Rakuten_Global_Brand_Logo.svg" alt="Rakuten">楽天で見る
          </a><br>
          <a class="link-btn satofuru-btn" href="https://www.satofull.jp" target="_blank">
            <img src="https://www.satofull.jp/favicon.ico" alt="さとふる">さとふるで見る
          </a>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# 品種カードを配置
for i, row in enumerate(top_items.itertuples(), start=1):
    with quadrants[i - 1]:
        render_card(i, row)

# === 右下「まとめ」 ===
with quadrants[3]:
    names = [getattr(r, "Item_name", "不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(names)
    st.markdown(f"""
    <div class="card" style="text-align:center;">
      <h3>まとめ</h3>
      <a class="link-btn x-btn" href="{twitter_url}" target="_blank">
        <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/X_logo_2023.svg"
             alt="X" style="height:16px;vertical-align:middle;margin-right:6px;">
        Xでシェア
      </a>
    </div>
    """, unsafe_allow_html=True)

st.caption("※ マッチ度は嗜好との近さを % 表記。季節一致がある場合は加点されます。")
