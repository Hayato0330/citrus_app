import streamlit as st
import streamlit.components.v1 as components
import textwrap
import base64
from pathlib import Path
from google.oauth2 import id_token
from google.auth.transport import requests

# ===== ページ設定 =====
st.set_page_config(page_title="ログイン - 柑橘推薦システム", page_icon="🍊", layout="centered")

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

# ===== タイトル部分 =====
st.markdown("## ログイン - 柑橘類の推薦システム")

# ===== 黒背景の案内ボックス =====
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
※ 本サービスは 電気通信大学 の Google アカウント（@gl.cc.uec.ac.jp）のみ利用可能です。
</div>
""", unsafe_allow_html=True)


# ===== Google クライアントID =====
GOOGLE_CLIENT_ID = "50427079333-hvl90ll0nud8nns6cfdvqbuh1r2qmdrq.apps.googleusercontent.com"  # ← GCPで取得したIDに置き換え

# ===== 許可するメールドメイン =====
ALLOW_ONLY_GLC = True                    # ← gl のみで OK なら True のまま
ALLOWED_DOMAIN = "gl.cc.uec.ac.jp"       # 許可ドメイン

# ===== Google Sign-In ボタンを埋め込み =====
components.html(
    f"""
    <style>
      .g_id_signin {{
          margin-top: 40px;  /* ← この行で下に下げる（pxを増やすとさらに下がる） */
      }}
    </style>

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
    height=600,  # ← 高さも少し増やすと自然
)

# ===== JS→Pythonの通信（トークン取得） =====
from streamlit_javascript import st_javascript  # pip install streamlit-javascript
token = st_javascript("await new Promise(resolve => { window.addEventListener('message', e => resolve(e.data.id_token)); });")

# ===== トークンが取得された場合の処理 =====
if token is None:
    st.warning("Google の認証ウィンドウが閉じられたか、トークンが取得できませんでした。もう一度お試しください。")
else:
    try:
        # --- IDトークンの検証 ---
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=30  # ← 時差吸収（Edge Case）
        )

        # --- 発行元の確認（Google 以外拒否）---
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            st.error("Google 以外から発行された認証トークンです。ログインを中断しました。")
            st.stop()

        # --- クライアントIDの一致を確認 ---
        if idinfo["aud"] != GOOGLE_CLIENT_ID:
            st.error("トークンのクライアントIDが一致しません。GCP の設定を確認してください。")
            st.stop()

        # --- ユーザ情報 ---
        user_email = idinfo.get("email", "")
        user_name = idinfo.get("name", "")
        user_picture = idinfo.get("picture", "")

        # --- ドメイン制限 ---
        if ALLOW_ONLY_GLC and not user_email.endswith("@" + ALLOWED_DOMAIN):
            st.error(f"このアカウント（{user_email}）ではログインできません。")
            st.stop()

        # --- 成功時 ---
        st.session_state.update({
            "user_logged_in": True,
            "user_name": user_name,
            "user_email": user_email,
            "user_picture": user_picture,
        })
        st.success(f"🎉 ようこそ {user_name} さん！ ({user_email})")
        st.image(user_picture, width=80)
        st.rerun()

    except ValueError as ve:
        # トークンが不正
        st.error(f"トークンが無効です（ValueError）: {ve}")

    except Exception as e:
        # その他の認証エラー
        st.error(f"Google 認証で予期しないエラーが発生しました: {e}")

