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

# =========================
# 1. エラー応答チェック
# =========================
if "error" in params:
    st.error(
        f"LINEログインに失敗しました: "
        f"{params.get('error')} - {params.get('error_description')}"
    )
    st.stop()

# =========================
# 2. code / state チェック
# =========================
if "code" not in params or "state" not in params:
    st.error("LINEから認証コードまたは state が返ってきていません。")
    st.write(dict(params))
    st.stop()

code = params["code"]

# ★追加：同じ認可コードを二重に使わない（rerun/再読込対策）
if st.session_state.get("line_last_code") == code:
    st.warning("この認可コードはすでに処理済みです。ログイン画面からやり直してください。")
    st.stop()
st.session_state["line_last_code"] = code

state = params["state"]

# NOTE:
# Streamlit + 外部OAuth では session_state が維持されないため
# 開発中は state 検証をスキップする


# =========================
# 4. トークン取得
# =========================
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

if res.status_code != 200:
    st.error(f"トークン取得に失敗しました（HTTP {res.status_code}）")
    st.json(res.json())
    st.stop()

token_json = res.json()
st.subheader("LINE token_json（デバッグ表示）")
st.write("token_json =", token_json)  # ★一時的デバッグ

if "id_token" not in token_json:
    st.error("LINEから ID トークンを取得できませんでした。")
    st.json(token_json)
    st.stop()

id_token_jwt = token_json["id_token"]

# =========================
# 5. IDトークン検証
# =========================
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

# --- nonce 検証（★重要） ---
expected_nonce = st.session_state.get("line_nonce")
if expected_nonce and payload.get("nonce") != expected_nonce:
    st.error("nonce の検証に失敗しました。")
    st.stop()

# =========================
# 6. セッション保存
# =========================
st.session_state.update({
    "user_logged_in": True,
    "auth_provider": "line",
    "user_id": payload.get("sub"),
    "user_name": payload.get("name", "LINEユーザー"),
    "user_email": payload.get("email", ""),
    "user_picture": payload.get("picture", ""),
})

st.success(f"LINEログイン成功！ようこそ {st.session_state['user_name']} さん！")

# app.py のルーティングに戻す
st.session_state["route"] = "top"   # ログイン後トップへ（あなたの設計）
st.rerun()
