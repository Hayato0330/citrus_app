# 1_top.py
import streamlit as st
import base64
from pathlib import Path

# ----------------------------------------------------------
# 1️⃣ ページ設定
# ----------------------------------------------------------
st.set_page_config(page_title="柑橘類の推薦システム", page_icon="🍊", layout="wide")

# ----------------------------------------------------------
# 2️⃣ ローカル画像をBase64で埋め込む関数
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
# 3️⃣ CSSデザイン
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
  margin-bottom: 2.2rem;   /* ← タイトルとボタンの間隔を広げる */
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
            
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# 4️⃣ 背景設定
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
# 5️⃣ ヒーローセクション
# ----------------------------------------------------------
st.markdown("""
<div class="hero">
  <h1>柑橘類の推薦システム</h1>
  <p>あなたにぴったりの品種を紹介します</p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# 6️⃣ Streamlitボタンでページ遷移
# ----------------------------------------------------------
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    if st.button("🍊 お試しで推薦してもらう", use_container_width=True):
        st.session_state["navigate_to"] = "input"

with col2:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("新規登録", use_container_width=True):
            st.switch_page("pages/2_Signup.py")
    with c2:
        if st.button("ログイン", use_container_width=True):
            st.switch_page("pages/3_Login.py")