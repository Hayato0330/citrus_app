# pages/3_callback_line.py
import requests
import jwt
import streamlit as st

st.set_page_config(page_title="LINEログイン処理中", page_icon="🔑")

LINE_CLIENT_ID = st.secrets["LINE_CHANNEL_ID"]
LINE_CLIENT_SECRET = st.secrets["LINE_CHANNEL_SECRET"]
LINE_REDIRECT_URI = st.secrets["LINE_REDIRECT_URI"]

st.title("LINEログイン処理中...")

params = st.query_params

# 1. エラーが返ってきたとき
if "error" in params:
    st.error(f"LINEログインに失敗しました: {params.get('error')} - {params.get('error_description')}")
    st.stop()

# 2. code / state が無い場合
if "code" not in params or "state" not in params:
    st.error("LINEから認証コードまたはstateが返ってきていません。")
    st.write(dict(params))
    st.stop()

code = params["code"]
state = params["state"]

# 3. state チェック（CSRF対策）
if state != st.session_state.get("line_state"):
    st.error("state の検証に失敗しました。（セッション切れの可能性あり）")
    st.stop()

# 4. 認可コード → トークン交換
token_url = "https://api.line.me/oauth2/v2.1/token"
headers = {"Content-Type": "application/x-www-form-urlencoded"}
data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": LINE_REDIRECT_URI,
    "client_id": LINE_CLIENT_ID,
    "client_secret": LINE_CLIENT_SECRET,
}

res = requests.post(token_url, headers=headers, data=data)
token_json = res.json()

if "id_token" not in token_json:
    st.error("LINEからIDトークンを取得できませんでした。")
    st.write(token_json)   # ← デバッグ時は中身を必ず確認する
    st.stop()

id_token_jwt = token_json["id_token"]

# 5. IDトークン検証
try:
    payload = jwt.decode(
        id_token_jwt,
        LINE_CLIENT_SECRET,
        algorithms=["HS256"],
        audience=LINE_CLIENT_ID,
        issuer="https://access.line.me",
    )
except Exception as e:
    st.error(f"IDトークンの検証に失敗しました: {e}")
    st.stop()

# 6. セッションにユーザー情報を保存
st.session_state.update({
    "user_logged_in": True,
    "auth_provider": "line",
    "user_id": payload.get("sub"),
    "user_name": payload.get("name", "LINEユーザー"),
    "user_email": payload.get("email", ""),
    "user_picture": payload.get("picture", ""),
})

st.success(f"LINEログイン成功！ようこそ {st.session_state['user_name']} さん！")

# 7. ここがポイント：**st.rerun() ではなく 2_input に飛ばす**
from streamlit import switch_page
switch_page("pages/2_input.py")
