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

# ===== 背景画像 =====
@st.cache_data
def local_image_to_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
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
  background:#fff;
  border-radius:12px;
  padding:20px;
  margin-bottom:20px;
  box-shadow:0 4px 12px rgba(0,0,0,.12);
  border:1px solid #eee;
}
.card h2, .card h3 { margin-top:0; }

.link-btn {
  display:inline-block;
  padding:8px 14px;
  margin:6px 0;
  border-radius:6px;
  color:#fff !important;
  text-decoration:none;
  font-weight:600;
  font-size:14px;
}
.disabled-btn {
  opacity:.6;
  pointer-events:none;
}

.amazon-btn { background:#00BFFF; }
.rakuten-btn { background:#BF0000; }
.satofuru-btn { background:#D2691E; }
.x-btn {
  background:#fff;
  color:#000 !important;
  border:1px solid #ddd;
}
</style>
"""), unsafe_allow_html=True)

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
  background:url("{bg_url}") center/cover fixed no-repeat;
}}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"] {{
  background:transparent !important;
}}
</style>
""", unsafe_allow_html=True)

# ===== 何派ロジック =====
def _safe_int(v, d=0):
    try: return int(v)
    except: return d

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
        "sweet":"甘党","sour":"さっぱり","bitter":"大人味",
        "aroma":"香り","juicy":"ジューシー","texture":"ぷりぷり"
    }
    priority = ["aroma","sour","sweet","juicy","texture","bitter"]
    ranked = sorted(vals.keys(), key=lambda k:(-vals[k], priority.index(k)))
    a,b = labels[ranked[0]], labels[ranked[1]]
    return f"{a}{b}派" if a!=b else f"{a}派"

def build_twitter_share(names):
    taste = compute_taste_type()
    n1 = names[0] if len(names)>0 else "—"
    n2 = names[1] if len(names)>1 else "—"
    n3 = names[2] if len(names)>2 else "—"
    text = (
        "🍊柑橘おすすめ診断の結果！\n\n"
        f"【私は “{taste}” でした🍋】\n\n"
        f"🏆 1位：{n1}\n🥈 2位：{n2}\n🥉 3位：{n3}\n\n"
        "あなたのタイプも出るよ👇\n"
        "#柑橘おすすめ\n"
        "https://citrusapp-ukx8zpjspw4svc7dmd5jnj.streamlit.app/"
    )
    return f"https://twitter.com/intent/tweet?text={quote(text)}"

# ===== データ =====
top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.session_state["route"]="top"
    st.rerun()

ns = runpy.run_path("pages/2_calculation_logic.py")
df = ns["_prepare_dataframe"]()
df_sel = df[df["id"].isin(top_ids)]
df_sel["__o"] = pd.Categorical(df_sel["id"], categories=top_ids, ordered=True)
df_sel = df_sel.sort_values("__o")
top_items = df_sel.head(3)

# ===== UI =====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果")

taste = compute_taste_type()
st.markdown(
    f"""<div style="display:inline-block;
    padding:.5rem 1rem;border-radius:999px;
    background:rgba(249,128,6,.15);font-weight:800">
    あなたは <span style="color:#f59e0b">{taste}</span> です 🍊
    </div>""",
    unsafe_allow_html=True
)

cols = st.columns(2)
for i,row in enumerate(top_items.itertuples(),1):
    with cols[(i-1)%2]:
        st.markdown(f"""
        <div class="card">
          <h2>{i}. {row.name}</h2>
          <div class="link-btn amazon-btn disabled-btn">Amazonで生果を探す（ログイン後）</div><br>
          <div class="link-btn rakuten-btn disabled-btn">楽天で贈答/家庭用を探す（ログイン後）</div><br>
          <div class="link-btn satofuru-btn disabled-btn">ふるさと納税で探す（ログイン後）</div>
          <p style="font-size:13px;color:#666;margin-top:8px">
            ※ ログインすると購入リンクや履歴保存が使えます
          </p>
        </div>
        """, unsafe_allow_html=True)

# ===== まとめ =====
names = [r.name for r in top_items.itertuples()]
twitter_url = build_twitter_share(names)

st.markdown(f"""
<div class="card" style="text-align:center">
  <h3>まとめ</h3>
  <a class="link-btn x-btn" href="{twitter_url}" target="_blank">
    Xでシェア
  </a>
  <p style="margin-top:14px">
    👉 <b>ログインすると保存・購入ができます</b>
  </p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    if st.button("← トップへ戻る", use_container_width=True):
        st.session_state["route"]="top"
        st.rerun()
