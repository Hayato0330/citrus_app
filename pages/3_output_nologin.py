# pages/3_output_nologin.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from urllib.parse import quote
import boto3
import textwrap
import base64
from pathlib import Path
from io import BytesIO
from matplotlib import font_manager

# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果", page_icon="🍊", layout="wide")


# ===== 日本語フォント =====
@st.cache_resource
def get_jp_fontprop():
    root = Path(__file__).resolve().parent.parent
    font_path = root / "fonts" / "NotoSansJP-Regular.ttf"
    if not font_path.exists():
        return None
    font_manager.fontManager.addfont(str(font_path))
    return font_manager.FontProperties(fname=str(font_path))


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


# ===== no-image =====
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
          width:100%;
          padding:8px 10px;
          margin:6px 0;
          border-radius:6px;
          color:#fff !important;
          text-decoration:none;
          font-weight:600;
          font-size:14px;
          transition:opacity .15s;
          cursor:pointer;
          box-sizing:border-box;
          white-space:normal;
          line-height:1.35;
        }
        .link-btn:hover { opacity:.9; }

        .amazon-btn { background-color:#00BFFF; }
        .rakuten-btn { background-color:#BF0000; }
        .satofuru-btn { background-color:#D2691E; }
        .x-btn {
          background-color:#ffffff;
          color:#000 !important;
          border:1px solid #ddd;
          display:inline-block;
          width:auto;
          padding:8px 14px;
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
        section[data-testid="stSidebar"],
        div[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        button[kind="header"],
        button[title="Toggle sidebar"],
        button[aria-label="Toggle sidebar"] {
          display: none !important;
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


# ===== R2: features.csv =====
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


# ===== レーダーチャート =====
@st.cache_data(show_spinner=False)
def radar_png_data_url(
    brix: int, acid: int, bitter: int, smell: int, moisture: int, elastic: int,
    title: str = ""
) -> str:
    fp = get_jp_fontprop()

    labels = ["甘さ", "酸味", "苦味", "香り", "ジューシーさ", "食感"]
    values = [brix, acid, bitter, smell, moisture, elastic]
    values = values + [values[0]]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles = angles + [angles[0]]

    fig = plt.figure(figsize=(2.45, 2.2), dpi=170)
    ax = plt.subplot(111, polar=True)

    line_color = "#F59E0B"
    fill_color = "#FDBA74"
    grid_color = "#E7D7C5"
    text_color = "#4B3B2B"

    ax.set_facecolor("#FFF7ED")
    ax.grid(color=grid_color, linewidth=1.0, alpha=0.9)
    ax.spines["polar"].set_color("#E8B26A")
    ax.spines["polar"].set_linewidth(1.4)

    ax.plot(angles, values, linewidth=2.4, color=line_color)
    ax.fill(angles, values, color=fill_color, alpha=0.35)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8.5, color=text_color, fontproperties=fp)

    ax.set_ylim(1, 6)
    ax.set_yticks([1, 2, 3, 4, 5, 6])
    ax.set_yticklabels(["1", "2", "3", "4", "5", "6"], fontsize=7.5, color=text_color)
    ax.set_rlabel_position(22)

    if title:
        ax.set_title(title, fontsize=9.5, pad=8, color=text_color, fontproperties=fp)

    fig.tight_layout(pad=0.5)
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# ===== R2: details.xlsx =====
@st.cache_data(ttl=3600)
def load_details_df() -> pd.DataFrame:
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

    key = st.secrets.get("r2_details_key") or "citrus_details_list.xlsx"
    obj = s3.get_object(Bucket=st.secrets["r2_bucket"], Key=key)

    df = pd.read_excel(BytesIO(obj["Body"].read()), sheet_name="description_image")
    if "Item_ID" in df.columns:
        df["Item_ID"] = pd.to_numeric(df["Item_ID"], errors="coerce")

    return df


# ===== データ取得 =====
features_df = load_features_df()
details_df = load_details_df()

TOPK = 3
top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.error("診断結果が見つからないため，トップページからやり直してほしい．")
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


def render_card(i, row):
    name = pick(row, "Item_name", "name", default="不明")
    desc = pick(row, "Description", "description", default="") or ""
    item_id = pick(row, "Item_ID", default=None)

    image_url = NO_IMAGE_URL
    real_url = build_citrus_image_url_from_id(item_id)
    if real_url:
        image_url = real_url

    radar_html = ""
    try:
        iid = int(item_id)
        frow = features_df.loc[features_df["Item_ID"] == iid].iloc[0]
        radar_url = radar_png_data_url(
            brix=int(frow["brix"]),
            acid=int(frow["acid"]),
            bitter=int(frow["bitter"]),
            smell=int(frow["smell"]),
            moisture=int(frow["moisture"]),
            elastic=int(frow["elastic"]),
            title="この品種の特徴",
        )
        radar_html = f"""
        <div style="width:100%; display:flex; justify-content:center;">
          <img src="{radar_url}" style="
              width:100%;
              max-width:230px;
              border-radius:12px;
              padding:6px;
              background:#FFF7ED;
              border:1px solid #F1D3A7;
              box-sizing:border-box;
              display:block;
            ">
        </div>
        """
    except Exception:
        radar_html = ""

    html_raw = f"""
<div class="card">
  <h2>{i}. {name}</h2>

  <div style="
      display:flex;
      gap:14px;
      align-items:flex-start;
      width:100%;
      box-sizing:border-box;
      flex-wrap:nowrap;
      overflow:hidden;
    ">

    <!-- 1) 画像 -->
    <div style="flex:0 0 25%; min-width:0; box-sizing:border-box;">
      <img src="{image_url}" style="width:100%; border-radius:12px; display:block;">
    </div>

    <!-- 2) 説明文 -->
    <div style="flex:0 0 24%; min-width:0; box-sizing:border-box;">
      <p style="
          font-size:14px;
          color:#333;
          margin:0;
          line-height:1.7;
          word-break:break-word;
          overflow-wrap:anywhere;
        ">
        {desc}
      </p>
    </div>

    <!-- 3) レーダー -->
    <div style="flex:0 0 21%; min-width:0; box-sizing:border-box;">
      {radar_html}
    </div>

    <!-- 4) ボタン＋メリット -->
    <div style="flex:0 0 18%; min-width:0; text-align:center; box-sizing:border-box;">
      <a class="link-btn amazon-btn disabled-btn" href="javascript:void(0)">Amazonで生果を探す</a><br>
      <a class="link-btn rakuten-btn disabled-btn" href="javascript:void(0)">楽天で贈答/家庭用を探す</a><br>
      <a class="link-btn satofuru-btn disabled-btn" href="javascript:void(0)">ふるさと納税で探す</a>

      <p style="
          font-size:13px;
          color:#666;
          margin-top:10px;
          line-height:1.5;
          word-break:break-word;
          overflow-wrap:anywhere;
        ">
        <b>ログインするとできること</b><br>
        ・気になった柑橘を <b>購入ページまで進める</b><br>
        ・入力を変えて <b>何度でも試せる</b>
      </p>
    </div>

  </div>
</div>
"""
    html = "\n".join(line.lstrip() for line in html_raw.splitlines()).strip()
    st.markdown(html, unsafe_allow_html=True)


for i, r in enumerate(top_items.itertuples(), start=1):
    render_card(i, r)

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