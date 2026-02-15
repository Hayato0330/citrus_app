# pages/3_output_nologin.py
import streamlit as st
import pandas as pd
from urllib.parse import quote
import textwrap
import base64
from pathlib import Path
import json
import runpy
import plotly.graph_objects as go
import streamlit.components.v1 as components
# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果", page_icon="🍊", layout="wide")

# ===== ユーティリティ =====
def pick(row, *keys, default=None):
    for k in keys:
        v = getattr(row, k, None)
        if v not in (None, ""):
            return v
    return default

def _safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default

# ===== 背景画像 =====
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

@st.cache_data
def image_file_to_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    ext = p.suffix.lower()
    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def build_citrus_image_url_from_id(item_id) -> str:
    root = Path(__file__).resolve().parent.parent
    try:
        iid = int(item_id)
    except Exception:
        return ""
    candidates = [
        root / "citrus_images" / f"citrus_{iid}.JPG",
        root / "citrus_images" / f"citrus_{iid}.jpg",
        root / "citrus_images" / f"citrus_{iid}.JPEG",
        root / "citrus_images" / f"citrus_{iid}.jpeg",
        root / "citrus_images" / f"citrus_{iid}.png",
    ]
    for p in candidates:
        if p.exists():
            return image_file_to_data_url(str(p))
    return ""

# ===== no-image=====
NO_IMAGE_PATH = Path(__file__).resolve().parent.parent / "other_images/no_image.png"
NO_IMAGE_URL = image_file_to_data_url(str(NO_IMAGE_PATH)) or "https://via.placeholder.com/200x150?text=No+Image"

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
    [data-testid="stHeader"], 
    [data-testid="stToolbar"], 
    [data-testid="stSidebar"] {{
        background: transparent !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ===== top_ids =====
top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.session_state["route"] = "top"
    st.rerun()

TOPK = 3


# ===== Excel（説明と画像）=====
@st.cache_data
def load_details():
    path = Path(__file__).resolve().parent.parent / "citrus_details_list.xlsx"
    return pd.read_excel(path, sheet_name="description_image")

details_df = load_details()

FEATURES = ["brix", "acid", "bitterness", "aroma", "moisture", "texture"]

@st.cache_data(ttl=3600)
def load_feature_db_from_r2():
    ns = runpy.run_path("pages/2_calculation_logic.py")
    df = ns["_prepare_dataframe"]()

    if df is None or df.empty:
        return pd.DataFrame()

    if "id" not in df.columns:
        st.error("特徴量DFに 'id' 列がありません。")
        return pd.DataFrame()

    df = df.copy()
    try:
        df["id"] = df["id"].astype(int)
    except Exception:
        pass

    df = df.set_index("id", drop=False)
    return df


feature_df = load_feature_db_from_r2()

# ===== top_ids から表示用 top_items を作る（計算なし）=====
top_ids_int = []
for x in top_ids:
    try:
        top_ids_int.append(int(x))
    except Exception:
        pass

df_sel = details_df[details_df["Item_ID"].isin(top_ids_int)].copy()
df_sel["__order"] = pd.Categorical(df_sel["Item_ID"], categories=top_ids_int, ordered=True)
df_sel = df_sel.sort_values("__order").reset_index(drop=True)

top_items = df_sel.head(TOPK)

# ===== レーダーチャート =====
RADAR_LABELS = ["甘さ","酸味","苦味","香り","ジューシー","食感"]

def get_item_vals_from_feature_db(item_id: int):
    if item_id in feature_df.index:
        row = feature_df.loc[item_id]
        # FEATURES順で取り出す（= レーダーの軸順と一致）
        return [float(row[c]) for c in FEATURES]
    # 見つからない場合のフォールバック（落とさない）
    return [1, 1, 1, 1, 1, 1]

def make_radar_fig_with_frames(item_vals, min_r=1, max_r=6, steps=18, frame_ms=30):
    theta = RADAR_LABELS + [RADAR_LABELS[0]]
    it = list(item_vals) + [item_vals[0]]

    it0 = [min_r] * len(theta)

    frames = []
    for k in range(steps):
        t = k / (steps - 1)
        cur = [min_r + (v - min_r) * t for v in it]
        frames.append(go.Frame(name=str(k), data=[go.Scatterpolar(r=cur, theta=theta, fill="toself")]))

    fig = go.Figure(
        data=[go.Scatterpolar(r=it0, theta=theta, fill="toself")],
        layout=go.Layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[min_r, max_r],
                    tickmode="array",
                    tickvals=[1, 2, 3, 4, 5, 6],
                ),
                # ★ここを最小構成にする（ValueError回避）
                angularaxis=dict(
                    tickfont=dict(size=12),
                ),
            ),
            showlegend=False,
            # ★見切れ対策は margin と height でやる（互換性が高い）
            margin=dict(l=90, r=90, t=25, b=90),
        ),
        frames=frames,
    )
    return fig, frame_ms

def plotly_autoplay_html(fig, height=340, frame_ms=30, div_id="plotlyRadar"):
    fig_json = fig.to_plotly_json()
    fig_str = json.dumps(fig_json, ensure_ascii=False)

    html = f"""
<div id="{div_id}" style="width:100%;height:{height}px;"></div>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<script>
const fig = {fig_str};
const gd = document.getElementById("{div_id}");

Plotly.newPlot(gd, fig.data, fig.layout, {{displayModeBar: false, responsive: true}})
  .then(() => {{
    setTimeout(() => {{
      Plotly.animate(gd, null, {{
        frame: {{duration: {frame_ms}, redraw: true}},
        transition: {{duration: 0}},
        mode: "immediate"
      }});
    }}, 120);
  }});
</script>
"""
    components.html(html, height=height + 10, scrolling=False)

# ===== 何派 + Xシェア =====
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
    ranked = sorted(vals.keys(), key=lambda k: (-vals[k], priority.index(k)))
    a, b = labels[ranked[0]], labels[ranked[1]]
    return f"{a}{b}派" if a != b else f"{a}派"

def build_twitter_share(names):
    taste = compute_taste_type()
    n = names + ["—","—","—"]
    text = (
        "🍊柑橘おすすめ診断の結果！\n\n"
        f"【私は “{taste}” でした🍋】\n\n"
        f"🏆 1位：{n[0]}\n"
        f"🥈 2位：{n[1]}\n"
        f"🥉 3位：{n[2]}\n\n"
        "あなたのタイプも出るよ👇\n"
        "#柑橘おすすめ\n"
        "https://citrusapp-ukx8zpjspw4svc7dmd5jnj.streamlit.app/"
    )
    return f"https://twitter.com/intent/tweet?text={quote(text)}"

# ===== UI =====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果")

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]

def render_card(i, row):
    name = pick(row, "Item_name", "name", default="不明")
    desc = pick(row, "Description", "description", default="")
    item_id = pick(row, "Item_ID", default=None)

    image_url = NO_IMAGE_URL  # デフォルトは必ず no-image
    real_url = build_citrus_image_url_from_id(item_id)
    if real_url:
        image_url = real_url

    html = f"""
    <div class="card">
      <h2>{i}. {name}</h2>

      <div style="display:flex;gap:20px;align-items:flex-start;">
        <div style="flex:1;">
          <img src="{image_url}" style="max-width:100%;border-radius:8px;margin-bottom:10px;">
          <p style="font-size:14px;color:#333; margin:0;">{desc}</p>
        </div>

        <div style="flex:1;text-align:center;">
          <div class="link-btn amazon-btn disabled-btn">Amazonで生果を探す</div><br>
          <div class="link-btn rakuten-btn disabled-btn">楽天で贈答/家庭用を探す</div><br>
          <div class="link-btn satofuru-btn disabled-btn">ふるさと納税で探す</div>

          <p style="font-size:13px;color:#666;margin-top:10px;line-height:1.5;">
            <b>ログインするとできること</b><br>
            ・気になった柑橘を <b>購入ページまで進める</b><br>
            ・入力を変えて <b>何度でも試せる</b>
          </p>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

for i,r in enumerate(top_items.itertuples(),1):
    with quadrants[i-1]:
        render_card(i,r)

with quadrants[3]:
    names = [pick(r, "Item_name", "name", default="不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(names)

    st.markdown(f"""
    <div class="card" style="text-align:center;">
      <h3>まとめ</h3>
      <a class="link-btn x-btn" href="{twitter_url}" target="_blank">
        Xでシェア
      </a>
      <div style="margin-top:14px;"></div>
    </div>
    """, unsafe_allow_html=True)

    col_a = st.columns(1, gap="small")

    with col_a[0]:
        if st.button("ログインして購入リンクを見る", use_container_width=True):
            st.session_state["route"] = "login"
            st.session_state.pop("navigate_to", None)
            st.rerun()

