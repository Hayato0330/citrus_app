import streamlit as st
import streamlit.components.v1 as components
import textwrap
import base64
import urllib.parse
from pathlib import Path
from google.oauth2 import id_token
from google.auth.transport import requests
from streamlit_javascript import st_javascript

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

IMG_PATH = Path(__file__).resolve().parent.parent / "top_background.png"
bg_url = local_image_to_data_url(str(IMG_PATH))

# 背景CSS
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
    unsafe_allow_html=True
)

# ==============================================================
# タイトル
# ==============================================================
st.markdown("## ログイン - 柑橘類の推薦システム")

st.markdown("""
<div style="
    background-color: rgba(0, 0, 0, 0.85);
    color: white;
    text-align: center;
    padding: 0.8rem 1rem;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.2);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    font-weight: 500;
    font-size: 0.95rem;
    margin-top: 0.5rem;
">
※ Googleログインの場合、 電通大UECクラウドアカウント（@gl.cc.uec.ac.jp）のみ利用可能です。
</div>
""", unsafe_allow_html=True)

# ==============================================================
# ログイン選択
# ==============================================================
st.markdown("### ログイン方法を選択してください")

col1, col2 = st.columns(2)

GOOGLE_CLIENT_ID = "317782524858-5q1rgg3e4dgr0ej3lqi2ri048ag9q4lh.apps.googleusercontent.com"
ALLOWED_DOMAIN = "gl.cc.uec.ac.jp"

# ==============================================================
# Google ログイン
# ==============================================================
with col1:
    st.markdown("#### Google でログイン")

    components.html(
        f"""
        <div id="g_id_onload"
            data-client_id="{GOOGLE_CLIENT_ID}"
            data-context="signin"
            data-ux_mode="popup"
            data-callback="handleCredentialResponse"
            data-auto_select="false">
        </div>

        <div class="g_id_signin"
            data-type="standard"
            data-shape="rectangular"
            data-theme="outline"
            data-text="signin_with"
            data-size="large"
            data-logo_alignment="left">
        </div>

        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <script>
        function handleCredentialResponse(response) {{
            const id_token = response.credential;
            window.parent.postMessage({{ 'id_token': id_token }}, "*");
        }}
        </script>
        """,
        height=200
    )

# JS → Python（Google id_token）
token = st_javascript(
    "await new Promise(resolve => { window.addEventListener('message', e => resolve(e.data.id_token)); });"
)

# Google token 処理
if token:
    try:
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), GOOGLE_CLIENT_ID, clock_skew_in_seconds=30
        )

        # 発行元確認
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            st.error("Google 以外から発行されたトークンです。")
            st.stop()

        # aud 確認
        if idinfo["aud"] != GOOGLE_CLIENT_ID:
            st.error("クライアントIDが一致しません。GCP 設定を確認してください。")
            st.stop()

        user_email = idinfo.get("email", "")
        user_name = idinfo.get("name", "")
        user_picture = idinfo.get("picture", "")

        if not user_email.endswith("@" + ALLOWED_DOMAIN):
            st.error(f"このアカウント（{user_email}）ではログインできません。")
            st.stop()

        st.session_state.update({
            "user_logged_in": True,
            "user_name": user_name,
            "user_email": user_email,
            "user_picture": user_picture,
        })
        st.rerun()

    except Exception as e:
        st.error(f"Google 認証エラー: {e}")

# ==============================================================
# LINE ログイン
# ==============================================================
with col2:
    st.markdown("#### LINE でログイン")

    def create_line_authorize_url():
        base_url = "https://access.line.me/oauth2/v2.1/authorize"
        params = {
            "response_type": "code",
            "client_id": st.secrets["LINE_CHANNEL_ID"],
            "redirect_uri": st.secrets["LINE_REDIRECT_URI"],
            "state": "random_state_12345",
            "scope": "profile openid email",
            "nonce": "random_nonce_abc"
        }
        return base_url + "?" + urllib.parse.urlencode(params)

    login_url = create_line_authorize_url()

    st.markdown(
        f"""
        <a href="{login_url}">
            <img src="https://developers.line.biz/media/login_button_guideline/line_login_button.png"
                style="width:200px; margin-top:20px;">
        </a>
        """,
        unsafe_allow_html=True
    )

# ==============================================================
# END
# ==============================================================
