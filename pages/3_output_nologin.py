# pages/3_output_nologin.py
import streamlit as st
import pandas as pd
from urllib.parse import quote
import boto3
import textwrap
import base64
from pathlib import Path
from io import BytesIO

# ★追加：Plotly + components（カードを1枚=1 iframeで完結させる）
import plotly.graph_objects as go
import plotly.io as pio
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
    # app直下/citrus_images/citrus_{ID}.JPG を探す
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

# ===== no-image（デフォルト画像）=====
NO_IMAGE_PATH = Path(__file__).resolve().parent.parent / "other_images/no_image.png"
NO_IMAGE_URL = image_file_to_data_url(str(NO_IMAGE_PATH)) or "https://via.placeholder.com/200x150?text=No+Image"

# ===== CSS（Streamlit側：サイドバー等を消して背景を適用）=====
st.markdown(
    textwrap.dedent(
        """
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; height: 0 !important; }
        [data-testid="stDecoration"] { display: none !important; }
        section[data-testid="stSidebar"], div[data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        button[kind="header"], button[title="Toggle sidebar"], button[aria-label="Toggle sidebar"] { display: none !important; }

        html, body, #root, [data-testid="stAppViewContainer"] {
          background-color: transparent !important;
        }
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

# ===== R2共通：S3クライアント =====
@st.cache_data(ttl=3600)
def _get_s3():
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
    return s3

# ===== R2：details（説明）=====
@st.cache_data(ttl=3600)
def load_details_df() -> pd.DataFrame:
    s3 = _get_s3()
    key = st.secrets.get("r2_details_key") or "citrus_details_list.xlsx"
    obj = s3.get_object(Bucket=st.secrets["r2_bucket"], Key=key)
    df = pd.read_excel(BytesIO(obj["Body"].read()), sheet_name="description_image")
    if "Item_ID" in df.columns:
        df["Item_ID"] = pd.to_numeric(df["Item_ID"], errors="coerce")
    return df

# ===== R2：features（指標）=====
@st.cache_data(ttl=3600)
def load_features_df() -> pd.DataFrame:
    s3 = _get_s3()
    key = st.secrets.get("r2_key") or "citrus_features.csv"
    obj = s3.get_object(Bucket=st.secrets["r2_bucket"], Key=key)
    df = pd.read_csv(BytesIO(obj["Body"].read()))
    if "Item_ID" in df.columns:
        df["Item_ID"] = pd.to_numeric(df["Item_ID"], errors="coerce")
    return df

details_df = load_details_df()
features_df = load_features_df()

# ===== データ取得 =====
TOPK = 3
top_ids = st.session_state.get("top_ids")

if not top_ids:
    st.error("診断結果が見つからないため，トップページからやり直してほしい．")
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

# ==============================================================
# ★カード内に全部入れるため：カード1枚=1 iframe(components.html)で完結
# ==============================================================
def build_radar_div(item_id: int) -> str:
    frow = features_df.loc[features_df["Item_ID"] == item_id].iloc[0]

    labels = ["甘さ", "酸味", "苦味", "香り", "ジューシーさ", "食感"]
    values = [
        int(frow["brix"]),
        int(frow["acid"]),
        int(frow["bitter"]),
        int(frow["smell"]),
        int(frow["moisture"]),
        int(frow["elastic"]),
    ]

    r = values + [values[0]]
    theta = labels + [labels[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r, theta=theta, fill="toself"))
    fig.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False,
        title=dict(text="この品種の特徴", x=0.5, font=dict(size=12)),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[1, 6],
                tickvals=[1, 2, 3, 4, 5, 6],
            )
        ),
    )

    # ★重要：components.htmlはカードごとにiframeなので毎回PlotlyJSが必要
    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs="cdn",
        config={"displayModeBar": False, "responsive": True},
    )

def build_card_html(rank: int, name: str, desc: str, image_url: str, radar_div: str) -> str:
    # descに改行がある場合を念のためHTML化
    desc_html = (desc or "").replace("\n", "<br/>")

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body {{
    margin: 0;
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
                 Arial, "Noto Sans JP", "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
  }}
  .card {{
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,.12);
    border: 1px solid #eee;
  }}
  h2 {{
    margin: 0 0 12px 0;
    font-size: 34px;
    font-weight: 900;
    color: #000;
  }}
  .row {{ display:flex; gap:20px; align-items:flex-start; }}
  .left {{ flex:1; }}
  .right {{ flex:1; text-align:center; }}

  .img {{
    width:100%;
    border-radius:8px;
    margin-bottom:10px;
    display:block;
    background:#f5f5f5;
  }}

  .desc {{
    font-size:14px;
    color:#333;
    line-height:1.6;
  }}

  .link-btn {{
    display:inline-block;
    padding:8px 14px;
    margin:6px 0;
    border-radius:6px;
    color:#fff;
    text-decoration:none;
    font-weight:600;
    font-size:14px;
    opacity:0.6;
    cursor:not-allowed;
    pointer-events:none;
  }}

  .amazon-btn {{ background:#00BFFF; }}
  .rakuten-btn {{ background:#BF0000; }}
  .satofuru-btn {{ background:#D2691E; }}

  .note {{
    font-size:13px;
    color:#666;
    margin-top:10px;
    line-height:1.5;
  }}

  .radar-wrap {{
    margin-top:10px;
  }}
</style>
</head>
<body>
  <div class="card">
    <h2>{rank}. {name}</h2>

    <div class="row">
      <div class="left">
        <img class="img" src="{image_url}" />
        <div class="desc">{desc_html}</div>
      </div>

      <div class="right">
        <a class="link-btn amazon-btn" href="javascript:void(0)">Amazonで生果を探す</a><br/>
        <a class="link-btn rakuten-btn" href="javascript:void(0)">楽天で贈答/家庭用を探す</a><br/>
        <a class="link-btn satofuru-btn" href="javascript:void(0)">ふるさと納税で探す</a>

        <div class="note">
          <b>ログインするとできること</b><br/>
          ・気になった柑橘を <b>購入ページまで進める</b><br/>
          ・入力を変えて <b>何度でも試せる</b>
        </div>

        <div class="radar-wrap">
          {radar_div}
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

# ===== 1〜3位のカード出力（白カード内に全部）=====
for rank, r in enumerate(top_items.itertuples(), start=1):
    with quadrants[rank - 1]:
        item_id = int(pick(r, "Item_ID", default=0) or 0)
        name = pick(r, "Item_name", "name", default="不明")
        desc = pick(r, "Description", "description", default="")
        image_url = build_citrus_image_url_from_id(item_id) or NO_IMAGE_URL

        try:
            radar_div = build_radar_div(item_id)
        except Exception:
            radar_div = "<div style='color:#999;font-size:12px;'>レーダーを生成できませんでした</div>"

        html = build_card_html(rank, name, desc, image_url, radar_div)

        # 説明文が長いと切れるので少し余裕を持たせる
        components.html(html, height=720, scrolling=False)

# ===== まとめ枠（Streamlit側カード）=====
with quadrants[3]:
    names = [pick(r, "Item_name", "name", default="不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(names)

    st.markdown(
        """
        <style>
        .card2 {
          background-color: #ffffff;
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 20px;
          box-shadow: 0 4px 12px rgba(0,0,0,.12);
          border: 1px solid #eee;
          text-align:center;
        }
        .x-btn {
          display:inline-block;
          padding:8px 14px;
          margin:6px 0;
          border-radius:6px;
          background-color:#ffffff;
          color:#000 !important;
          border:1px solid #ddd;
          text-decoration:none;
          font-weight:600;
          font-size:14px;
        }
        .x-btn:hover { background-color:#f5f5f5; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="card2">
          <h3>まとめ</h3>
          <a class="x-btn" href="{twitter_url}" target="_blank">Xでシェア</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("ログインして購入リンクを見る", use_container_width=True):
        st.session_state["route"] = "login"
        st.session_state.pop("navigate_to", None)
        st.rerun()