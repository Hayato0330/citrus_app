# app.py
import streamlit as st

st.set_page_config(page_title="柑橘類の推薦システム", page_icon="🍊", layout="wide")

# ================= CSS =================
st.markdown("""
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">

<style>
:root{
  --primary:#f98006;
}

html, body, [data-testid="stAppViewContainer"]{
  height:100%;
  font-family: "Plus Jakarta Sans", sans-serif;
}

/* 背景 */
.bg-wrap{
  position:fixed; inset:0; z-index:-2;
}
.bg-wrap img{
  width:100%; height:100%; object-fit:cover;
}
.bg-overlay{
  position:fixed; inset:0; z-index:-1;
  background: rgba(255,250,240,.85);
}
@media (prefers-color-scheme: dark){
  .bg-overlay{ background: rgba(35,25,15,.85); }
}

/* 中央のヒーローセクション */
.hero{
  min-height: 90vh;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  text-align:center;
  color:#1f1f1f;
}
.hero h1{ font-weight:800; font-size:3rem; margin-bottom:.5rem; }
.hero p{ font-size:1.2rem; opacity:.85; }

/* ボタン */
.btn{
  font-weight:800; padding:1rem 2rem; font-size:1.2rem;
  border-radius:1rem; text-decoration:none;
  transition: all .2s ease;
  display:inline-block;
}
.btn-ghost{
  background:rgba(249,128,6,.15); color:var(--primary);
}
.btn-ghost:hover{ background:rgba(249,128,6,.25); }
.btn-primary{
  background:var(--primary); color:white; box-shadow:0 6px 16px rgba(249,128,6,.25);
}
.btn-primary:hover{ filter:brightness(1.1); }
.btn-outline{
  border:2px solid rgba(249,128,6,.6); background:white; color:var(--primary);
}
.btn-outline:hover{ background:rgba(249,128,6,.1); }
</style>
""", unsafe_allow_html=True)

# ================= 背景レイヤ =================
st.markdown("""
<div class="bg-wrap">
  <img src="top_background.png" alt="柑橘の背景">
</div>
<div class="bg-overlay"></div>
""", unsafe_allow_html=True)

# ================= ヒーローセクション =================
st.markdown("""
<div class="hero">
  <h1>柑橘類の推薦システム</h1>
  <p>あなたにぴったりの品種を紹介します</p>

  <div style="margin-top:2rem; display:flex; flex-wrap:wrap; gap:1.5rem; justify-content:center;">
    <a href="#try" class="btn btn-ghost">お試しで推薦してもらう</a>
    <div style="display:flex; flex-direction:column; gap:1rem; min-width:12rem;">
      <a href="#signup" class="btn btn-primary">新規登録</a>
      <a href="#login" class="btn btn-outline">ログイン</a>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ================= ボタンクリック処理（デモ用） =================
if "page" not in st.session_state:
    st.session_state["page"] = None

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("お試しで推薦してもらう"):
        st.session_state["page"] = "try"
with col2:
    if st.button("新規登録"):
        st.session_state["page"] = "signup"
with col3:
    if st.button("ログイン"):
        st.session_state["page"] = "login"