# pages/3_line_oauth.py
import requests
import jwt
import streamlit as st

def handle_line_oauth():
    params = st.query_params

    # code がなければ通常アクセス
    if "code" not in params:
        return

    code = params.get("code")

    # 二重実行ガード
    if st.session_state.get("line_last_code") == code:
        st.query_params.clear()
        return
    st.session_state["line_last_code"] = code

    # トークン交換
    res = requests.post(
        "https://api.line.me/oauth2/v2.1/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": st.secrets["LINE_REDIRECT_URI"],
            "client_id": st.secrets["LINE_CHANNEL_ID"],
            "client_secret": st.secrets["LINE_CHANNEL_SECRET"],
        },
    )

    if res.status_code != 200:
        st.query_params.clear()
        st.error("LINEログインに失敗しました")
        st.stop()

    token = res.json()

    payload = jwt.decode(
        token["id_token"],
        st.secrets["LINE_CHANNEL_SECRET"],
        algorithms=["HS256"],
        audience=st.secrets["LINE_CHANNEL_ID"],
        issuer="https://access.line.me",
    )

    # セッション保存（emailは使わない方針）
    st.session_state.update({
        "user_logged_in": True,
        "auth_provider": "line",
        "user_id": payload.get("sub"),
        "user_name": payload.get("name"),
        "user_picture": payload.get("picture"),
        "route": "top_login",
    })

    # URLクリーン → app.py 再実行
    st.query_params.clear()
    st.rerun()
