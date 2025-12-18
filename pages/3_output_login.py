# pages/3_output_login.py
import streamlit as st
import numpy as np
import pandas as pd
from urllib.parse import quote
import textwrap
import base64
from pathlib import Path
import runpy

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
body { background-color: #FFF8F0; }

.card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,.12);
  border: 1px solid #eee;
}
.card h2, .card h3 { color:#000; margin-top:0; }

.match-score { color:#f59e0b; font-weight:bold; }

.link-btn {
  display:inline-block;
  padding:8px 14px;
  margin:6px 0;
  border-radius:6px;
  color:#fff !important;
  text-decoration:none;
  font-weight:600;
  font-size:14px;
  transition:opacity .15s;
  cursor:pointer;
}
.link-btn img { height:16px; vertical-align:middle; margin-right:6px; }
.link-btn:hover { opacity:.9; }

.amazon-btn { background-color:#00BFFF; }
.rakuten-btn { background-color:#BF0000; }
.satofuru-btn { background-color:#D2691E; }
.x-btn {
  background-color:#ffffff;
  color:#000 !important;
  border:1px solid #ddd;
}

.amazon-btn:hover { background-color:#87CEEB; }
.rakuten-btn:hover { background-color:#990000; }
.satofuru-btn:hover { background-color:#b85c19; }
.x-btn:hover { background-color:#f5f5f5; color:#000 !important; }
</style>
"""), unsafe_allow_html=True)

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

# ===== 外部リンク生成 =====
def build_amazon_url(name: str) -> str:
    q = quote(f"{name} 生果 フルーツ -苗 -苗木 -のぼり -ジュース -ゼリー -缶 -本")
    return f"https://www.amazon.co.jp/s?k={q}&i=grocery"

def build_rakuten_url(name: str) -> str:
    return f"https://search.rakuten.co.jp/search/mall/{quote(name)}/"

def build_satofuru_url(name: str) -> str:
    return f"https://www.satofull.jp/search/?q={quote(name)}"

# ===== SNSシェア =====
def build_twitter_share(names: list[str]) -> str:
    ranked_text = "\n".join([f"{i+1}位 {n}" for i, n in enumerate(names)])
    app_url = "https://citrusapp-ukx8zpjspw4svc7dmd5jnj.streamlit.app/"
    text = quote(f"おすすめの柑橘 🍊\n{ranked_text}\n#柑橘おすすめ\n{app_url}")
    return f"https://twitter.com/intent/tweet?text={text}"

# ===== データ取得（nologin と同じ思想）=====
TOPK = 3

top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.error("診断結果が見つからないため，トップページからやり直してほしい．")
    with st.sidebar:
        if st.button("← トップへ戻る", use_container_width=True):
            st.session_state["route"] = "top_login" if st.session_state.get("user_logged_in") else "top"
            st.rerun()
    st.stop()

# 入力値（app.py が session_state に入れてる前提）
try:
    user_vec = np.array(
        [
            int(st.session_state["val_brix"]),
            int(st.session_state["val_acid"]),
            int(st.session_state["val_bitterness"]),
            int(st.session_state["val_aroma"]),
            int(st.session_state["val_moisture"]),
            int(st.session_state["val_texture"]),
        ],
        dtype=float,
    )
except Exception as e:
    st.error(f"入力値が見つからない／取得できませんでした（詳細: {e}）")
    st.stop()

# 2_calculation_logic から DF 作成＆スコアリングを取得
ns = runpy.run_path("pages/2_calculation_logic.py")

prepare_df = ns.get("_prepare_dataframe")
score_items = ns.get("score_items")

if prepare_df is None:
    st.error("2_calculation_logic.py に _prepare_dataframe が見つかりません。")
    st.stop()

df_all = prepare_df()

# score_items が無い場合は最低限のコサイン類似で計算（落ちない保険）
if score_items is None:
    feature_cols = ["brix", "acid", "bitter", "smell", "moisture", "elastic"]
    if not all(c in df_all.columns for c in feature_cols):
        st.error("特徴量カラムが不足しています（brix/acid/bitter/smell/moisture/elastic）。")
        st.stop()
    X = df_all[feature_cols].astype(float).values

    def normalize(v): return v / (np.linalg.norm(v) + 1e-8)
    u = normalize(user_vec)
    Xn = np.array([normalize(x) for x in X])
    scores = Xn @ u
    ranked_all = df_all.copy()
    ranked_all["score"] = scores
else:
    # 2_calculation_logic 側の定義に合わせて呼ぶ（weights は無ければ渡さない）
    try:
        ranked_all = score_items(df_all, user_vec, season_pref="", weights=None)
    except TypeError:
        ranked_all = score_items(df_all, user_vec, season_pref="")

# top_ids の順序を保持して抽出（表示順位は top_ids を優先）
df_sel = ranked_all[ranked_all["id"].isin(top_ids)].copy()
df_sel["__order"] = pd.Categorical(df_sel["id"], categories=top_ids, ordered=True)
df_sel = df_sel.sort_values("__order")

top_items = df_sel.head(TOPK)

# ===== UI =====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果（ログイン）")

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]

def pick(row, *keys, default=None):
    for k in keys:
        v = getattr(row, k, None)
        if v is not None and v != "":
            return v
    return default

def render_card(i, row):
    # 列名が name / Item_name どちらでも動くように
    name = pick(row, "name", "Item_name", default="不明")
    desc = pick(row, "description", default="")
    image_url = pick(row, "image_path", default="https://via.placeholder.com/200x150?text=No+Image")
    score_pct = float(pick(row, "score", default=0.0)) * 100

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
          <a class="link-btn amazon-btn" href="{build_amazon_url(name)}" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg" alt="Amazon">
            Amazonで見る
          </a><br>
          <a class="link-btn rakuten-btn" href="{build_rakuten_url(name)}" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/6/6a/Rakuten_Global_Brand_Logo.svg" alt="Rakuten">
            楽天で見る
          </a><br>
          <a class="link-btn satofuru-btn" href="{build_satofuru_url(name)}" target="_blank">
            <img src="https://www.satofull.jp/favicon.ico" alt="さとふる">
            さとふるで見る
          </a>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

for i, row in enumerate(top_items.itertuples(), start=1):
    with quadrants[i - 1]:
        render_card(i, row)

with quadrants[3]:
    names = [pick(r, "name", "Item_name", default="不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(names)
    st.markdown(f"""
    <div class="card" style="text-align:center;">
      <h3>まとめ</h3>
      <a class="link-btn x-btn" href="{twitter_url}" target="_blank">
        <img src="https://cdn.cms-twdigitalassets.com/content/dam/about-twitter/x/brand-toolkit/logo-black.png.twimg.2560.png" alt="X">
        Xでシェア
      </a>
    </div>
    """, unsafe_allow_html=True)

st.caption("※ マッチ度は嗜好との近さを % 表記です。")

with st.sidebar:
    if st.button("← トップへ戻る", use_container_width=True):
        st.session_state["route"] = "top_login" if st.session_state.get("user_logged_in") else "top"
        st.rerun()
