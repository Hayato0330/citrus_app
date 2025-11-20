# 3_callback_line.py

import streamlit as st
import requests
import json
import jwt   # ← PyJWT
from jwt.algorithms import RSAAlgorithm

st.set_page_config(page_title="LINEログイン処理", page_icon="🔑", layout="centered")

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
# Secrets / 設定値
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
# LINE の公開鍵(JWKS)を取得
# ==============================================================
jwks_url = "https://api.line.me/oauth2/v2.1/certs"
jwks = requests.get(jwks_url).json()

# header から kid を取得
header = jwt.get_unverified_header(id_token_jwt)
kid = header["kid"]

# kid に対応する公開鍵を取得
public_key = None
for key in jwks["keys"]:
    if key["kid"] == kid:
        public_key = RSAAlgorithm.from_jwk(json.dumps(key))
        break

if public_key is None:
    st.error("公開鍵が見つかりませんでした（kid不一致）。")
    st.stop()

# ==============================================================
# ID Token をデコード・検証（正しい方法）
# ==============================================================
try:
    payload = jwt.decode(
        id_token_jwt,
        public_key,
        algorithms=["RS256"],
        audience=LINE_CLIENT_ID,
        issuer="https://access.line.me",
    )
except Exception as e:
    st.error(f"ID Token の検証に失敗しました: {e}")
    st.stop()

# ==============================================================
# ユーザ情報
# ==============================================================
user_name = payload.get("name", "LINEユーザー")
email = payload.get("email", "")
picture = payload.get("picture", "")

# ==============================================================
# セッションへ保存
# ==============================================================
st.session_state.update({
    "user_logged_in": True,
    "user_name": user_name,
    "user_email": email,
    "user_picture": picture,
})

st.success(f"LINEログイン成功！ ようこそ {user_name} さん！")

st.rerun()
