# 3_callback_line.py

import streamlit as st
import requests
import json
import base64
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

st.set_page_config(page_title="LINEログイン処理", page_icon="🔑", layout="centered")

st.markdown("## LINEログイン処理中...")

# ==============================================================
# クエリパラメータ取得
# ==============================================================
query_params = st.query_params

if "code" not in query_params:
    st.error("LINEから認証コードが返ってきていません。")
    st.stop()

code = query_params["code"]
state = query_params.get("state", "")

# ==============================================================
# Secrets から設定を取得
# ==============================================================
LINE_CLIENT_ID = st.secrets["LINE_CHANNEL_ID"]
LINE_CLIENT_SECRET = st.secrets["LINE_CHANNEL_SECRET"]
CALLBACK_URL = st.secrets["LINE_REDIRECT_URI"]

# ==============================================================
# 認可コード → アクセストークン交換
# ==============================================================
token_url = "https://api.line.me/oauth2/v2.1/token"

headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}

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
# ID Token を Google ライブラリで検証（安全な方法）
# ==============================================================
try:
    # LINEのissuerはこれ
    ID_TOKEN_ISS = "https://access.line.me"

    idinfo = id_token.verify_oauth2_token(
        id_token_jwt,
        grequests.Request(),
        audience=LINE_CLIENT_ID,
        issuer=ID_TOKEN_ISS
    )

except Exception as e:
    st.error(f"ID Token の検証に失敗しました: {e}")
    st.stop()

# ==============================================================
# ユーザ情報の取得
# ==============================================================
user_name = idinfo.get("name", "")
user_id = idinfo.get("sub", "")
picture = idinfo.get("picture", "")
email = idinfo.get("email", "")

# ==============================================================
# セッションへ保存
# ==============================================================
st.session_state.update({
    "user_logged_in": True,
    "user_name": user_name or "LINEユーザー",
    "user_email": email,
    "user_picture": picture,
})

st.success(f"LINEログイン成功！ ようこそ {user_name} さん！")

st.rerun()
