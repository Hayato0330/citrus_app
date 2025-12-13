import streamlit as st
import numpy as np
import pandas as pd
from urllib.parse import quote
import textwrap
import base64
from pathlib import Path
import runpy  # ← 追加：2_calculation_logic から R2 読み込み関数を使う

# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果", page_icon="🍊", layout="wide")

@st.cache_data
def local_image_to_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
        st.warning(f"背景画像が見つかりません: {p}")
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

IMG_PATH = Path(__file__).resolve().parent.parent / "other_images/top_background.png"
bg_url = local_image_to_data_url(str(IMG_PATH))

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
                            
/* ===== Streamlit ヘッダー完全削除 ===== */
header[data-testid="stHeader"] {
    display: none !important;
}
[data-testid="stToolbar"] {
    display: none !important;
    height: 0 !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}

/* 上部余白の白線対策 */
html, body, #root {
    background: transparent !important;
}

</style>
"""), unsafe_allow_html=True)
# ===== 背景CSS =====
st.markdown(
    f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: url("{bg_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] {{
        background: transparent !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ===== SNSシェア =====
def build_twitter_share(names: list[str]) -> str:
    ranked_text = "\n".join([f"{i+1}位 {n}" for i, n in enumerate(names)])
    app_url = "https://citrusapp-ukx8zpjspw4svc7dmd5jnj.streamlit.app/"
    # ツイート本文に直接リンクを改行付きで埋め込む
    text = quote(f"おすすめの柑橘 🍊\n{ranked_text}\n#柑橘おすすめ\n{app_url}")
    return f"https://twitter.com/intent/tweet?text={text}"

# ===== データ取得 =====
TOPK = 3

top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.error("診断結果が見つからないため，トップページからやり直してほしい．")
    with st.sidebar:
        if st.button("← トップへ戻る", use_container_width=True):
            st.session_state["route"] = "top"
            st.rerun()
    st.stop()

# 2_calculation_logic.py から R2 読み込み関数を取得
ns = runpy.run_path("pages/2_calculation_logic.py")
prepare_df = ns["_prepare_dataframe"]

df_all = prepare_df()
# ID でフィルタして，入力時の順位順に並べる
df_sel = df_all[df_all["id"].isin(top_ids)].copy()
df_sel["__order"] = pd.Categorical(df_sel["id"], categories=top_ids, ordered=True)
df_sel = df_sel.sort_values("__order")

# ===== UI =====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果（ゲスト表示）")

top_items = df_sel.head(TOPK)

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]

def render_card(i, row):
    name = getattr(row, "name", "不明")
    # 説明文は常に「未設定」
    desc = "未設定"
    # 画像パスは空欄のまま
    image_url = ""

    html = f"""
    <div class="card">
      <h2>{i}. {name}</h2>
      <div style="display:flex;gap:20px;align-items:flex-start;">
        <div style="flex:1;">
          <img src="{image_url}" style="max-width:100%;border-radius:8px;margin-bottom:10px;">
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
    names = [getattr(r, "name", "不明") for r in top_items.itertuples()]
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

# マッチ度のキャプションは削除済み

# === サイドバーに戻るボタン ===
with st.sidebar:
    if st.button("← トップへ戻る", use_container_width=True):
        st.session_state["route"] = "top"
        st.rerun()
