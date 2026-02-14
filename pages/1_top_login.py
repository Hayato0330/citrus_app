# 1_top_login.py
import streamlit as st
import base64
from pathlib import Path

# ----------------------------------------------------------
# ページ設定
# ----------------------------------------------------------
st.set_page_config(page_title="柑橘類の推薦システム", page_icon="🍊", layout="wide")

# ----------------------------------------------------------
# ログイン確認（未ログインなら top に戻す）
# ----------------------------------------------------------
if not st.session_state.get("user_logged_in"):
    # app.py ルーティング運用に合わせて戻す
    st.session_state["route"] = "top"
    st.rerun()

# ----------------------------------------------------------
# ローカル画像をBase64で埋め込む関数
# ----------------------------------------------------------
@st.cache_data
def local_image_to_data_url(path: str) -> str:
    """ローカル画像をBase64データURLに変換"""
    p = Path(path)
    if not p.exists():
        st.warning(f"画像ファイルが見つかりません: {p}")
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

# 背景画像を読み込む
bg_url = local_image_to_data_url("other_images/top_background.png")

# ----------------------------------------------------------
# CSSデザイン
# ----------------------------------------------------------
st.markdown("""
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">

<style>
:root{
  --primary:#f98006;
  --primary-light:#ffa94d;
  --primary-lighter:#fbbf6b;
}
html, body, [data-testid="stAppViewContainer"]{
  height:100%;
  font-family: "Plus Jakarta Sans", sans-serif;
}
.hero{
  min-height: auto;                 /* 高さ固定を解除 */
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:flex-start;       /* 上寄せ */
  text-align:center;
  color:#1f1f1f;
  padding-top: 6vh;                 /* 上に少し余白だけ入れる */
  padding-bottom: 4vh;
}
.hero h1 {
  margin-bottom: 1.6rem;   /* ★変更：ログイン情報を見せるために詰める */
}

.btn{
  font-weight:800;
  padding:1.3rem 2.8rem;
  font-size:1.5rem;
  border-radius:1.2rem;
  text-decoration:none;
  transition: all .2s ease;
  display:flex;
  align-items:center;
  justify-content:center;
  box-shadow:0 6px 14px rgba(0,0,0,0.1);
  border:3px solid rgba(249,128,6,.5);
  min-width: 14rem;
  background: linear-gradient(135deg, var(--primary-light), var(--primary));
  color:white;
}
.btn:hover{
  filter: brightness(1.1);
  box-shadow:0 8px 18px rgba(249,128,6,0.3);
}

/* ===== Streamlit ヘッダー完全削除 ===== */
header[data-testid="stHeader"] {
    display: none !important;
}
[data-testid="stToolbar"] {
    display: none !important;
    height: 0 !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}

/* 念のため最上部の背景を固定 */
html, body, #root, [data-testid="stAppViewContainer"] {
    background-color: transparent !important;
}

/* ★追加：ログインユーザー情報カード */
.user-card {
  width: min(680px, 92vw);
  margin: 0.8rem auto 1.2rem auto;
  padding: 1.0rem 1.1rem;
  border-radius: 14px;
  background: rgba(255,255,255,0.75);
  border: 1px solid rgba(0,0,0,0.06);
  box-shadow: 0 6px 18px rgba(0,0,0,0.08);
  display: flex;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(4px);
}
.user-left {
  display: flex;
  gap: 12px;
  align-items: center;
}
.user-avatar {
  width: 54px;
  height: 54px;
  border-radius: 999px;
  overflow: hidden;
  border: 2px solid rgba(249,128,6,0.25);
  background: rgba(255,255,255,0.8);
  flex: 0 0 auto;
}
.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.user-meta {
  line-height: 1.15;
}
.user-meta .name {
  font-weight: 800;
  font-size: 1.05rem;
}
.user-meta .sub {
  font-weight: 600;
  font-size: 0.86rem;
  opacity: 0.75;
  margin-top: 0.15rem;
}
.badge {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: rgba(249,128,6,0.14);
  border: 1px solid rgba(249,128,6,0.22);
  font-weight: 800;
  font-size: 0.9rem;
}
.badge-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: rgba(34,197,94,0.95); /* 緑 */
  box-shadow: 0 0 0 3px rgba(34,197,94,0.15);
}
.small-note {
  width: min(680px, 92vw);
  margin: 0 auto 1.0rem auto;
  padding: 0.55rem 0.85rem;
  border-radius: 12px;
  background: rgba(0,0,0,0.72);
  color: white;
  font-weight: 600;
  font-size: 0.92rem;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# 背景設定
# ----------------------------------------------------------
if bg_url:
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: url("{bg_url}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] {{
            background: transparent;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# ----------------------------------------------------------
# ヒーローセクション
# ----------------------------------------------------------
st.markdown("""
<div class="hero">
  <h1>柑橘類の推薦システム</h1>
  <p>あなたにぴったりの品種を紹介します</p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# ログインユーザー情報の表示（LINE想定）
# ----------------------------------------------------------
user_name = st.session_state.get("user_name") or "LINEユーザー"
user_picture = st.session_state.get("user_picture") or ""
auth_provider = st.session_state.get("auth_provider") or "line"
user_id = st.session_state.get("user_name") or ""



avatar_html = ""
if user_picture:
    avatar_html = f'<div class="user-avatar"><img src="{user_picture}" alt="avatar"></div>'
else:
    # 画像が無い場合は空の丸枠だけ出す
    avatar_html = '<div class="user-avatar"></div>'

st.markdown(
    f"""
    <div class="user-card">
      <div class="user-left">
        {avatar_html}
        <div class="user-meta">
          <div class="name">ようこそ、{user_name} さん</div>
          <div class="sub">ログイン方法：{auth_provider.upper()}</div>
          <div class="id">ID:{user_id} </div>
        </div>
      </div>
      <div class="badge"><span class="badge-dot"></span>ログイン中</div>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------------
# Streamlitボタンでページ遷移
# ----------------------------------------------------------
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    # ★変更：ログイン済みは「診断を始める」をメイン導線にする
    if st.button("🍊 診断を始める", use_container_width=True):
        st.session_state["navigate_to"] = "input"

with col2:
    # ★ログアウトのみ（診断履歴ボタンは削除）
    if st.button("ログアウト", use_container_width=True):
        # ログイン情報を落とす
        st.session_state["user_logged_in"] = False
        st.session_state["auth_provider"] = None
        st.session_state["user_id"] = None
        st.session_state["user_name"] = None
        st.session_state["user_email"] = None
        st.session_state["user_picture"] = None

        # 画面遷移は app.py に戻す
        st.session_state["route"] = "top"
        st.rerun()
