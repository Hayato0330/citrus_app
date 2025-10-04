# app.py
import streamlit as st

st.set_page_config(page_title="柑橘類の推薦システム", page_icon="🍊", layout="wide")

# ================= CSS（フォント/配色/レイアウト/ボタン） =================
st.markdown("""
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700;800&display=swap" rel="stylesheet">

<style>
:root{
  --primary:#f98006;
  --bg-light:#fffaf0;
  --bg-dark:#23190f;
  --text-light:#1f1f1f;
  --text-dark:#ffffff;
  --radius-lg: 2rem;
  --radius-xl: 3rem;
}

html, body, [data-testid="stAppViewContainer"]{
  height:100%;
  font-family: "Plus Jakarta Sans", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Hiragino Kaku Gothic ProN", Meiryo, "Noto Sans JP", sans-serif;
}

/* 背景画像 */
.app-bg{
  position:fixed;
  inset:0;
  z-index:-2;
  background: url("https://lh3.googleusercontent.com/aida-public/AB6AXuABl6ZxpS3FSttuG4bkC9CndCCiS-mN5SPjsld_4EE7Bf9wqXbJ9PN84sWYcMv-663x498kdpRWDCsM5KqEq-wDXAtMbENu5CrpVZYN39gpX90tbX4Himoa5Dmp5qmHdMJ2ImzsidkMVMB39E-x-xBw8BKjMn2rGO2KmzQkE2oU1V2cAUrsatUmU1YGC5lUA3Y9JXpr2AsoW0aQqwouQ89qQFSuUYOilegGELwiV0BKT2CaY_gzAWYsG5LipUxhRuJwzqR8-OXert0")
              center/cover no-repeat fixed;
}
.app-overlay{
  position:fixed;
  inset:0;
  z-index:-1;
  background: rgba(255,250,240,0.85);
}
@media (prefers-color-scheme: dark){
  .app-overlay{ background: rgba(35,25,15,0.85); }
}

/* 中央カード領域 */
.hero{
  display:flex; align-items:center; justify-content:center;
  min-height: calc(100vh - 4rem);
  padding: 2rem;
  text-align:center;
  color: var(--text-light);
}
@media (prefers-color-scheme: dark){
  .hero{ color: var(--text-dark); }
}

.hero h1{
  font-weight: 800;
  letter-spacing: -0.02em;
  font-size: clamp(2.4rem, 4vw + 1rem, 4rem);
  margin: 0 0 0.5rem 0;
}
.hero p{
  margin: 0 auto;
  max-width: 40rem;
  opacity: .85;
  font-size: clamp(1rem, 1.2vw + .8rem, 1.25rem);
}

/* ボタン */
.btn-row{
  display:flex; flex-wrap:wrap; gap:1rem; justify-content:center;
  margin-top: 2.5rem;
}
.btn{
  border:none; cursor:pointer;
  border-radius: 1rem;
  padding: 1.25rem 2rem;
  font-weight: 800;
  font-size: clamp(1.05rem, 1.6vw, 1.4rem);
  transition: filter .15s ease, transform .03s ease;
}
.btn:active{ transform: translateY(1px); }

/* 左の「お試し」 */
.btn-ghost{
  background: color-mix(in srgb, var(--primary) 20%, transparent);
  color: var(--primary);
}
.btn-ghost:hover{ filter: brightness(1.05); }

/* 右の2つ（新規登録 / ログイン） */
.btn-primary{
  background: var(--primary);
  color: white;
  box-shadow: 0 8px 24px rgba(249,128,6,.25);
}
.btn-primary:hover{ filter: brightness(1.08); }

.btn-outline{
  background: rgba(255,255,255,.85);
  border: 2px solid color-mix(in srgb, var(--primary) 60%, transparent);
  color: var(--primary);
}
@media (prefers-color-scheme: dark){
  .btn-outline{ background: rgba(35,25,15,.85); }
}
.btn-outline:hover{ filter: brightness(1.05); }

/* 右の縦並び用 */
.btn-col{ display:flex; flex-direction:column; gap:1rem; min-width: 16rem; }
</style>
""", unsafe_allow_html=True)

# 背景レイヤ
st.markdown('<div class="app-bg"></div><div class="app-overlay"></div>', unsafe_allow_html=True)

# ================= 本文 =================
st.markdown("""
<div class="hero">
  <div>
    <h1>柑橘類の推薦システム</h1>
    <p>あなたにぴったりの品種を紹介します</p>

    <div class="btn-row">
      <form action="" method="post">
        <button name="try" class="btn btn-ghost">お試しで推薦してもらう</button>
      </form>

      <div class="btn-col">
        <form action="" method="post"><button name="signup" class="btn btn-primary">新規登録</button></form>
        <form action="" method="post"><button name="login"  class="btn btn-outline">ログイン</button></form>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ================= クリック処理（Streamlit側で受ける） =================
# フォームの代わりに Streamlit コンポーネントで受けるための見えないボタン
# （上のHTMLボタンの代わりに、ここを使いたい場合は下の3行を表示UIに置き換えてOK）
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("お試しで推薦してもらう", key="try_btn", use_container_width=True):
        st.session_state["page"] = "try"
with col2:
    if st.button("新規登録", key="signup_btn", use_container_width=True):
        st.session_state["page"] = "signup"
with col3:
    if st.button("ログイン", key="login_btn", use_container_width=True):
        st.session_state["page"] = "login"

# ページ遷移の例（必要に応じて実処理に差し替えてください）
page = st.session_state.get("page")
if page == "try":
    st.success("✅ お試しフローへ（ここに推薦UIへ遷移するコードを入れてください）")
elif page == "signup":
    st.info("✍️ 新規登録のフォームへ（実装ポイント）")
elif page == "login":
    st.info("🔐 ログインフォームへ（実装ポイント）")