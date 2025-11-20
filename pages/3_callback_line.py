# 3_callback_line.py

import streamlit as st
import requests
import json
import base64

st.set_page_config(page_title="LINEログイン処理", page_icon="🔑", layout="centered")

st.markdown("## LINEログイン処理中...")

query_params = st.query_params

if "code" not in query_params:
    st.error("LINEから認証コードが返ってきていません。")
    st.stop()

code = query_params["code"]
state = query_params.get("state", "")

LINE_CLIENT_ID = "（あなたのLINEチャネルID）"
LINE_CLIENT_SECRET = "（あなたのLINEチャネルシークレット）"
CALLBACK_URL = "https://citrusapp-xxxxxxx.streamlit.app/callback_line"

# アクセストークン交換
token_url = "https://api.line.me/oauth2/v2.1/token"
data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": CALLBACK_URL,
    "client_id": LINE_CLIENT_ID,
    "client_secret": LINE_CLIENT_SECRET,
}

token_res = requests.post(token_url, data=data)
token_json = token_res.json()

if "id_token" not in token_json:
    st.error("LINEからIDトークンを取得できませんでした。")
    st.write(token_json)
    st.stop()

id_token_jwt = token_json["id_token"]

# ---- ID Token をデコード ----
payload = id_token_jwt.split(".")[1] + "=="
payload_json = json.loads(base64.urlsafe_b64decode(payload))

user_name = payload_json.get("name", "")
user_id = payload_json.get("sub", "")
picture = payload_json.get("picture", "")

st.session_state.update({
    "user_logged_in": True,
    "user_name": user_name,
    "user_email": "",          # LINEはemailが無い場合もある
    "user_picture": picture,
})

st.success(f"LINEログイン成功！ ようこそ {user_name} さん！")

st.rerun()
