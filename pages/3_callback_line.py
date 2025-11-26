# 3_callback_line.py

import streamlit as st
import requests
import jwt

st.set_page_config(page_title="LINEログイン処理", page_icon="🔑", layout="centered")
st.write("現在アクセスされているURL:", st.request.url)
st.markdown("## LINEログイン処理中...")

# ==============================================================
# クエリ取得
# ==============================================================
query_params = st.query_params

if "code" not in query_params:
    st.error("LINEから認証コードが返ってきていません。")
    st.stop()

code = query_params["code"]

# ==============================================================
# Secrets 読み込み
# ==============================================================
LINE_CLIENT_ID = st.secrets["LINE_CHANNEL_ID"]
LINE_CLIENT_SECRET = st.secrets["LINE_CHANNEL_SECRET"]
CALLBACK_URL = st.secrets["LINE_REDIRECT_URI"]

# ==============================================================
# 認可コード → アクセストークン交換
# ==============================================================
token_url = "https://api.line.me/oauth2/v2.1/token"
headers = {"Content-Type": "application/x-www-form-urlencoded"}

data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": CALLBACK_URL,
    "client_id": LINE_CLIENT_ID,
    "client_secret": LINE_CLIENT_SECRET,
}

token_res = requests.post(token_url, headers=headers, data=data)
token_json = token_res.json()

if "id_token" not in token_json:
    st.error("LINEからIDトークンを取得できませんでした。")
    st.json(token_json)
    st.stop()

id_token_jwt = token_json["id_token"]

# ==============================================================
# HS256 で IDトークンを検証（これが LINE Web Login の正しい方法）
# ==============================================================
try:
    payload = jwt.decode(
        id_token_jwt,
        LINE_CLIENT_SECRET,        # ← HS256 の秘密鍵は channel secret！
        algorithms=["HS256"],
        audience=LINE_CLIENT_ID,
        issuer="https://access.line.me"
    )
except Exception as e:
    st.error(f"ID Token の検証に失敗しました: {e}")
    st.stop()

# ==============================================================
# ユーザー情報
# ==============================================================
user_name = payload.get("name", "LINEユーザー")
email = payload.get("email", "")
picture = payload.get("picture", "")

# ==============================================================
# セッションに保存
# ==============================================================
st.session_state.update({
    "user_logged_in": True,
    "user_name": user_name,
    "user_email": email,
    "user_picture": picture,
})

st.success(f"LINEログイン成功！ようこそ {user_name} さん！")
st.rerun()
