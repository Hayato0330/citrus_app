# top.py
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
# 3️⃣ CSSデザイン（透け感＋フェードアップ）
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

/* ------------------ アニメーション定義 ------------------ */

/* タイトルや説明文のフェードアップ（完全に表示） */
@keyframes fadeUpFull {
  0% { opacity: 0; transform: translateY(30px); }
  100% { opacity: 1; transform: translateY(0); }
}

/* ボタン用のフェードアップ（透け感を保つ） */
@keyframes fadeUpSoft {
  0% { opacity: 0; transform: translateY(30px); }
  100% { opacity: 0.95; transform: translateY(0); }
}

/* ------------------ ヒーローセクション ------------------ */
.hero{
  min-height: 90vh;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  text-align:center;
  color:#1f1f1f;
}
.hero h1{
  font-weight:800;
  font-size:3.5rem;
  margin-bottom:.8rem;
  opacity:0;
  animation: fadeUpFull 1s ease forwards;
  animation-delay:0.1s;
}
.hero p{
  font-size:1.4rem;
  opacity:0;
  animation: fadeUpFull 1s ease forwards;
  animation-delay:0.4s;
}

/* ------------------ ボタン全般 ------------------ */
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
  opacity:0.95; /* ← 常に透け感あり */
  animation: fadeUpSoft 1s ease forwards;
  animation-delay:0.7s;
}

/* 🍊 お試しボタン */
.btn-ghost{
  background: linear-gradient(135deg, var(--primary-light), var(--primary));
  color:white;
}
.btn-ghost:hover{
  filter: brightness(1.1);
  box-shadow:0 8px 18px rgba(249,128,6,0.3);
}

/* 🟧 新規登録ボタン */
.btn-primary{
  background: linear-gradient(135deg, var(--primary-lighter), var(--primary-light));
  color:white;
}
.btn-primary:hover{
  filter:brightness(1.1);
  box-shadow:0 8px 18px rgba(249,128,6,0.3);
}

/* 🟧 ログインボタン（同じ色調） */
.btn-outline{
  background: linear-gradient(135deg, var(--primary-lighter), var(--primary-light));
  color:white;
}
.btn-outline:hover{
  filter:brightness(1.1);
  box-shadow:0 8px 18px rgba(249,128,6,0.3);
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# 4️⃣ 背景設定（静止）
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
# 5️⃣ メインヒーローセクション
# ----------------------------------------------------------
st.markdown("""
<div class="hero">
  <h1>柑橘類の推薦システム</h1>
  <p>あなたにぴったりの品種を紹介します</p>

  <div style="margin-top:3rem; display:flex; flex-wrap:wrap; gap:2rem; justify-content:center;">
    <a href="https://citrusapp-stahmzy7w8xxfvwgdg6hbq.streamlit.app/" target="_self" class="btn btn-ghost">🍊 お試しで推薦してもらう</a>
    <div style="display:flex; flex-direction:column; gap:1.5rem; min-width:14rem;">
      <a href="#signup" class="btn btn-primary">新規登録</a>
      <a href="#login" class="btn btn-outline">ログイン</a>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)