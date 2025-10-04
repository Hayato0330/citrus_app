# app.py
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
bg_url = local_image_to_data_url("top_background.png")

# ----------------------------------------------------------
# 3️⃣ CSSデザイン
# ----------------------------------------------------------
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

# ----------------------------------------------------------
# 4️⃣ 背景レイヤ
# ----------------------------------------------------------
if bg_url:
    st.markdown(f"""
    <div class="bg-wrap">
      <img src="{bg_url}" alt="柑橘の背景">
    </div>
    <div class="bg-overlay"></div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="bg-wrap"></div>
    <div class="bg-overlay"></div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------------
# 5️⃣ メインヒーローセクション
# ----------------------------------------------------------
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