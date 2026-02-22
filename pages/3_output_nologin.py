# pages/3_output_nologin.py
import streamlit as st
import pandas as pd
from urllib.parse import quote
import boto3
import textwrap
import base64
from pathlib import Path
from io import BytesIO

# ★追加：Plotly（HTML埋め込み用）
import plotly.graph_objects as go
import plotly.io as pio

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

NO_IMAGE_PATH = Path(__file__).resolve().parent.parent / "other_images/no_image.png"
NO_IMAGE_URL = image_file_to_data_url(str(NO_IMAGE_PATH)) or "https://via.placeholder.com/200x150?text=No+Image"

# ===== CSS =====
st.markdown(
    textwrap.dedent(
        """
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

        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; height: 0 !important; }
        [data-testid="stDecoration"] { display: none !important; }

        html, body, #root, [data-testid="stAppViewContainer"] {
          background-color: transparent !important;
        }

        section[data-testid="stSidebar"], div[data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        button[kind="header"], button[title="Toggle sidebar"], button[aria-label="Toggle sidebar"] { display: none !important; }
        </style>
        """
    ),
    unsafe_allow_html=True,
)

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

# ===== 何派 + SNSシェア =====
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

def build_twitter_share(names: list[str]) -> str:
    app_url = "https://citrusapp-ukx8zpjspw4svc7dmd5jnj.streamlit.app/"
    taste_type = compute_taste_type()
    n = names + ["—", "—", "—"]
    text_raw = (
        "🍊柑橘おすすめ診断の結果！\n\n"
        f"【私は “{taste_type}” でした🍋】\n"
        "あなたは何派？\n\n"
        f"🏆 1位：{n[0]}\n"
        f"🥈 2位：{n[1]}\n"
        f"🥉 3位：{n[2]}\n\n"
        "あなたのタイプも出るよ👇\n"
        "#柑橘おすすめ\n"
        f"{app_url}"
    )
    return f"https://twitter.com/intent/tweet?text={quote(text_raw)}"

# ==============================================================
# ★追加①：R2から citrus_features.csv を読み込む
# ==============================================================
@st.cache_data(ttl=3600)
def load_features_df() -> pd.DataFrame:
    required = ("r2_account_id", "r2_access_key_id", "r2_secret_access_key", "r2_bucket")
    missing = [k for k in required if k not in st.secrets]
    if missing:
        raise RuntimeError(f"R2の接続情報が見つからない。secrets.toml に {missing} を設定してほしい。")

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{st.secrets['r2_account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=st.secrets["r2_access_key_id"],
        aws_secret_access_key=st.secrets["r2_secret_access_key"],
    )

    key = st.secrets.get("r2_key") or "citrus_features.csv"
    obj = s3.get_object(Bucket=st.secrets["r2_bucket"], Key=key)

    df = pd.read_csv(BytesIO(obj["Body"].read()))
    if "Item_ID" in df.columns:
        df["Item_ID"] = pd.to_numeric(df["Item_ID"], errors="coerce")
    return df

# ==============================================================
# ★追加②：PlotlyレーダーをHTML(div)にして返す（st.markdownに埋め込む）
# ==============================================================
def build_radar_div_html(
    brix: int, acid: int, bitter: int, smell: int, moisture: int, elastic: int,
    include_js: bool,
    title: str = "この品種の特徴"
) -> str:
    labels = ["甘さ", "酸味", "苦味", "香り", "ジューシーさ", "食感"]
    values = [brix, acid, bitter, smell, moisture, elastic]

    # 閉じる
    r = values + [values[0]]
    theta = labels + [labels[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r,
            theta=theta,
            fill="toself",
            hovertemplate="%{theta}: %{r}<extra></extra>",
        )
    )

    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False,
        title=dict(text=title, x=0.5, y=0.95, xanchor="center", yanchor="top", font=dict(size=12)),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[1, 6],
                tickmode="array",
                tickvals=[1, 2, 3, 4, 5, 6],
            )
        ),
    )

    div = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=("cdn" if include_js else False),  # ★JSは最初だけ
        config={"displayModeBar": False, "responsive": True},
    )

    # カード右側に収めるラッパ
    return f"""
    <div style="width:100%; max-width:420px; margin:10px auto 0 auto;">
      {div}
    </div>
    """

# ===== Excel（説明と画像）=====
@st.cache_data(ttl=3600)
def load_details_df() -> pd.DataFrame:
    required = ("r2_account_id", "r2_access_key_id", "r2_secret_access_key", "r2_bucket")
    missing = [k for k in required if k not in st.secrets]
    if missing:
        raise RuntimeError(
            f"R2の接続情報が見つからない。secrets.toml に {missing} を設定してほしい。"
        )

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{st.secrets['r2_account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=st.secrets["r2_access_key_id"],
        aws_secret_access_key=st.secrets["r2_secret_access_key"],
    )

    key = st.secrets.get("r2_details_key") or "citrus_details_list.xlsx"
    obj = s3.get_object(Bucket=st.secrets["r2_bucket"], Key=key)

    df = pd.read_excel(BytesIO(obj["Body"].read()), sheet_name="description_image")
    if "Item_ID" in df.columns:
        df["Item_ID"] = pd.to_numeric(df["Item_ID"], errors="coerce")
    return df

# ==============================================================
# ★追加③：features_df をロード
# ==============================================================
features_df = load_features_df()
details_df = load_details_df()

# ===== データ取得 =====
TOPK = 3
top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.error("診断結果が見つからないため，トップページからやり直してほしい．")
    with st.sidebar:
        if st.button("← トップへ戻る", use_container_width=True):
            st.session_state["route"] = "top_login" if st.session_state.get("user_logged_in") else "top"
            st.rerun()
    st.stop()

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

# ===== UI =====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果")

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]

def render_card(i, row):
    name = pick(row, "Item_name", "name", default="不明")
    desc = pick(row, "Description", "description", default="")
    item_id = pick(row, "Item_ID", default=None)

    image_url = NO_IMAGE_URL
    real_url = build_citrus_image_url_from_id(item_id)
    if real_url:
        image_url = real_url

    # ==========================================================
    # ★追加④：品種の指標をfeatures_dfから引いてレーダーHTMLを作る
    #    JS読み込みは1位カードのみ（i==1）でCDNを入れる
    # ==========================================================
    radar_html = ""
    try:
        iid = int(item_id)
        frow = features_df.loc[features_df["Item_ID"] == iid].iloc[0]
        radar_html = build_radar_div_html(
            brix=int(frow["brix"]),
            acid=int(frow["acid"]),
            bitter=int(frow["bitter"]),
            smell=int(frow["smell"]),
            moisture=int(frow["moisture"]),
            elastic=int(frow["elastic"]),
            include_js=(i == 1),
            title="この品種の特徴",
        )
    except Exception:
        radar_html = ""

    html_raw = f"""
<div class="card">
  <h2>{i}. {name}</h2>
  <div style="display:flex;gap:20px;align-items:flex-start;">
    <div style="flex:1;">
      <img src="{image_url}" style="max-width:100%;border-radius:8px;margin-bottom:10px;">
      <p style="font-size:14px;color:#333;">{desc}</p>
    </div>

    <div style="flex:1;text-align:center;">
      <a class="link-btn amazon-btn disabled-btn" href="javascript:void(0)">Amazonで生果を探す</a><br>
      <a class="link-btn rakuten-btn disabled-btn" href="javascript:void(0)">楽天で贈答/家庭用を探す</a><br>
      <a class="link-btn satofuru-btn disabled-btn" href="javascript:void(0)">ふるさと納税で探す</a>

      <p style="font-size:13px;color:#666;margin-top:10px;line-height:1.5;">
        <b>ログインするとできること</b><br>
        ・気になった柑橘を <b>購入ページまで進める</b><br>
        ・入力を変えて <b>何度でも試せる</b>
      </p>

      {radar_html}
    </div>
  </div>
</div>
"""

    html = "\n".join(line.lstrip() for line in html_raw.splitlines()).strip()
    st.markdown(html, unsafe_allow_html=True)

for i, r in enumerate(top_items.itertuples(), start=1):
    with quadrants[i - 1]:
        render_card(i, r)

with quadrants[3]:
    names = [pick(r, "Item_name", "name", default="不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(names)

    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
          <h3>まとめ</h3>
          <a class="link-btn x-btn" href="{twitter_url}" target="_blank">Xでシェア</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("ログインして購入リンクを見る", use_container_width=True):
        st.session_state["route"] = "login"
        st.session_state.pop("navigate_to", None)
        st.rerun()