# pages/3_output_nologin.py
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

# ===== CSS（login版と完全一致）=====
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

/* ★ nologin専用：見た目そのまま無効化 */
.disabled-btn {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}
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

# ===== データ取得（login版と同一）=====
TOPK = 3

top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.session_state["route"] = "top"
    st.rerun()

ns = runpy.run_path("pages/2_calculation_logic.py")
df_all = ns["_prepare_dataframe"]()

df_sel = df_all[df_all["id"].isin(top_ids)].copy()
df_sel["__order"] = pd.Categorical(df_sel["id"], categories=top_ids, ordered=True)
df_sel = df_sel.sort_values("__order")
top_items = df_sel.head(TOPK)

# ===== 何派 + SNSシェア用ロジック =====
def _safe_int(v, d=0):
    try:
        return int(v)
    except Exception:
        return d

def compute_taste_type() -> str:
    vals = {
        "sweet": _safe_int(st.session_state.get("val_brix")),
        "sour": _safe_int(st.session_state.get("val_acid")),
        "bitter": _safe_int(st.session_state.get("val_bitterness")),
        "aroma": _safe_int(st.session_state.get("val_aroma")),
        "juicy": _safe_int(st.session_state.get("val_moisture")),
        "texture": _safe_int(st.session_state.get("val_texture")),
    }
    labels = {
        "sweet": "甘党",
        "sour": "さっぱり",
        "bitter": "大人味",
        "aroma": "香り",
        "juicy": "ジューシー",
        "texture": "ぷりぷり",
    }
    priority = ["aroma", "sour", "sweet", "juicy", "texture", "bitter"]
    ranked = sorted(vals.keys(), key=lambda k: (-vals[k], priority.index(k)))
    a, b = labels[ranked[0]], labels[ranked[1]]
    return f"{a}{b}派" if a != b else f"{a}派"

def build_twitter_share(names):
    taste = compute_taste_type()
    n1 = names[0] if len(names) > 0 else "—"
    n2 = names[1] if len(names) > 1 else "—"
    n3 = names[2] if len(names) > 2 else "—"

    text = (
        "🍊柑橘おすすめ診断の結果！\n\n"
        f"【私は “{taste}” でした🍋】\n\n"
        f"🏆 1位：{n1}\n"
        f"🥈 2位：{n2}\n"
        f"🥉 3位：{n3}\n\n"
        "あなたのタイプも出るよ👇\n"
        "#柑橘おすすめ\n"
        "https://citrusapp-ukx8zpjspw4svc7dmd5jnj.streamlit.app/"
    )
    return f"https://twitter.com/intent/tweet?text={quote(text)}"

# ===== データ =====
top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.session_state["route"] = "top"
    st.rerun()

ns = runpy.run_path("pages/2_calculation_logic.py")
df = ns["_prepare_dataframe"]()

df_sel = df[df["id"].isin(top_ids)].copy()
df_sel["__o"] = pd.Categorical(df_sel["id"], categories=top_ids, ordered=True)
df_sel = df_sel.sort_values("__o")

top_items = df_sel.head(3)


# ===== UI（login版と完全一致）=====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果")

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]

def render_card(i, row):
    name = getattr(row, "name", "不明")
    desc = getattr(row, "description", "")
    image_url = getattr(row, "image_path", "https://via.placeholder.com/200x150?text=No+Image")
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
            <!-- ★ 見た目そのまま・クリック不可 -->
            <div class="link-btn amazon-btn disabled-btn">
                <img src="https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg">
                Amazonで生果を探す
            </div><br>
            <div class="link-btn rakuten-btn disabled-btn">
                <img src="https://upload.wikimedia.org/wikipedia/commons/6/6a/Rakuten_Global_Brand_Logo.svg">
                楽天で贈答/家庭用を探す
            </div><br>
            <div class="link-btn satofuru-btn disabled-btn">
                <img src="https://www.satofull.jp/favicon.ico">
                ふるさと納税で探す
            </div>
            <p style="font-size:13px;color:#666;margin-top:10px;">
              ※ <b>ログイン</b>すると購入リンクや履歴保存が使えます
            </p>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

for i, row in enumerate(top_items.itertuples(), start=1):
    with quadrants[i - 1]:
        render_card(i, row)

# ===== まとめカード（login版と同一配置）=====
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

    # ★ 「ログイン」導線（UIは崩さず、挙動だけ）
    if st.button("🔐 ログインして購入リンクを見る", use_container_width=True):
        st.session_state["route"] = "login"
        st.rerun()

with st.sidebar:
    if st.button("← トップへ戻る", use_container_width=True):
        st.session_state["route"] = "top"
        st.rerun()
