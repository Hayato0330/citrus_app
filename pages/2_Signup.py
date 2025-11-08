import streamlit as st
import streamlit.components.v1 as components
import textwrap
import base64
from pathlib import Path
from google.oauth2 import id_token
from google.auth.transport import requests

# ===== ページ設定 =====
st.set_page_config(page_title="新規登録 - 柑橘推薦システム", page_icon="🍊", layout="wide")
# ===== 背景画像（Base64埋め込み） =====
@st.cache_data
def local_image_to_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
        st.warning(f"背景画像が見つかりません: {p}")
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

# ✅ 親ディレクトリ（app.py と同じ階層）にある top_background.png を参照
IMG_PATH = Path(__file__).resolve().parent.parent / "top_background.png"
bg_url = local_image_to_data_url(str(IMG_PATH))

# ===== CSS =====
st.markdown(textwrap.dedent(f"""
<style>
/* ===== 背景設定 ===== */
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
"""), unsafe_allow_html=True)

# ===== Google クライアントID =====
GOOGLE_CLIENT_ID = "850365063962-ntge0smf483se8h9ktpjjlvre2cdh4hl.apps.googleusercontent.com"  # ← GCPで取得したIDに置き換え

# ===== 許可するドメイン =====
ALLOWED_DOMAIN = "gl.cc.uec.ac.jp"

st.markdown("## 🎓 UECクラウドアカウントで新規登録")
st.info("※ 本サービスは 電気通信大学 の Google アカウント（@gl.cc.uec.ac.jp）のみ利用可能です。")

# ===== Google Sign-In ボタンを埋め込み =====
components.html(
    f"""
    <div id="g_id_onload"
         data-client_id="{GOOGLE_CLIENT_ID}"
         data-context="signin"
         data-ux_mode="popup"
         data-callback="handleCredentialResponse"
         data-auto_select="false"
         data-itp_support="true">
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
    height=400,
)

# ===== JS→Pythonの通信（トークン取得） =====
from streamlit_javascript import st_javascript  # pip install streamlit-javascript
token = st_javascript("await new Promise(resolve => { window.addEventListener('message', e => resolve(e.data.id_token)); });")

# ===== トークンが取得された場合の処理 =====
if token:
    try:
        # トークンをGoogleで検証
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)

        user_email = idinfo.get("email", "")
        user_name = idinfo.get("name", "")
        user_picture = idinfo.get("picture", "")

        # --- ドメイン制限 ---
        if user_email.endswith("@" + ALLOWED_DOMAIN):
            st.session_state["user_logged_in"] = True
            st.session_state["user_name"] = user_name
            st.session_state["user_email"] = user_email
            st.session_state["user_picture"] = user_picture

            st.success(f"🎉 ようこそ {user_name} さん！ ({user_email})")
            st.image(user_picture, width=80)

            st.session_state["route"] = "top"  # app.py経由でトップへ戻る
            st.rerun()

        else:
            st.error(f"⚠️ このアカウント（{user_email}）は利用できません。")
            st.stop()

    except Exception as e:
        st.error(f"トークン検証に失敗しました: {e}")
