# pages/3_Login.py
import streamlit as st
import base64
from pathlib import Path
import secrets
import urllib.parse

# ==============================================================
# ページ設定
# ==============================================================
st.set_page_config(
    page_title="ログイン - 柑橘推薦システム",
    page_icon="🍊",
    layout="centered"
)

# ==============================================================
# 背景画像を base64 に変換
# ==============================================================
@st.cache_data
def local_image_to_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

# ==============================================================
# 背景画像
# ==============================================================
IMG_PATH = Path(__file__).resolve().parent.parent / "other_images/top_background.png"
bg_url = local_image_to_data_url(str(IMG_PATH))
# ==============================================================
# CSS（サイドバー・ヘッダ・ツールバー完全非表示 + 背景適用）
# ==============================================================
st.markdown(
    f"""
    <style>
    html, body, #root, [data-testid="stAppViewContainer"] {{
        background-color: transparent !important;
    }}
    [data-testid="stAppViewContainer"] {{
        background-image: url("{bg_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    [data-testid="stToolbar"] {{
        display: none !important;
        height: 0 !important;
    }}
    [data-testid="stDecoration"] {{
        display: none !important;
    }}
    section[data-testid="stSidebar"] {{
        display: none !important;
    }}
    div[data-testid="stSidebar"] {{
        display: none !important;
    }}
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}
    button[kind="header"] {{
        display: none !important;
    }}
    button[title="Toggle sidebar"] {{
        display: none !important;
    }}
    button[aria-label="Toggle sidebar"] {{
        display: none !important;
    }}
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] {{
        background: transparent !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================
# タイトル
# ==============================================================
st.markdown("## ログイン - 柑橘類の推薦システム")
st.markdown("### LINEでログインしてください")

# ==============================================================
# state / nonce（1セッションで固定）
# ==============================================================
if "line_state" not in st.session_state:
    st.session_state["line_state"] = secrets.token_urlsafe(16)

if "line_nonce" not in st.session_state:
    st.session_state["line_nonce"] = secrets.token_urlsafe(16)

# ==============================================================
# LINE 認可URL生成（★ 正式実装）
# ==============================================================
def create_line_authorize_url():
    base_url = "https://access.line.me/oauth2/v2.1/authorize"

    params = {
        "response_type": "code",
        "client_id": st.secrets["LINE_CHANNEL_ID"],
        "redirect_uri": st.secrets["LINE_REDIRECT_URI"],
        "state": st.session_state["line_state"],
        "scope": "profile openid",   # emailは使わない
        "nonce": st.session_state["line_nonce"],
    }

    query = urllib.parse.urlencode(params)
    return f"{base_url}?{query}"

login_url = create_line_authorize_url()

# ==============================================================
# LINE公式ログインボタン
# ==============================================================
btn_path = Path(__file__).resolve().parent.parent / "other_images/btn_login_press.png"
line_btn_url = local_image_to_data_url(str(btn_path))

st.markdown(
    f"""
    <div style="margin-top: 24px; text-align:center;">
        <a href="{login_url}">
            <img src="{line_btn_url}"
                 style="width:220px; max-width:100%; display:block; margin:auto;">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
