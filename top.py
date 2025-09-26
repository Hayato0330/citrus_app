import streamlit as st

# ページ全体の設定
st.set_page_config(page_title="My Streamlit App", layout="wide")

# CSSでオレンジ＆白の基調色を設定
st.markdown(
    """
    <style>
    body {
        background-color: #FFFFFF;
    }
    .title {
        color: #FF7F00; /* オレンジ */
        text-align: center;
        font-size: 36px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .description {
        text-align: center;
        font-size: 18px;
        color: #444444;
        margin-bottom: 40px;
    }
    .stButton>button {
        background-color: #FF7F00; 
        color: white;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        font-size: 16px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF9933;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# タイトルと説明
st.markdown("<div class='title'>Streamlit アプリ</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='description'>これはデモ用のトップページです。下のボタンからページへ移動してください。</div>",
    unsafe_allow_html=True
)

# 中央から下にかけて左右に分割
col1, col2 = st.columns(2)

with col1:
    st.write("### 左：お試しページへ")
    if st.button("お試し"):
        st.switch_page("pages/1_Try.py")

with col2:
    st.write("### 右：ユーザー操作")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("新規登録"):
            st.switch_page("pages/2_Register.py")
    with c2:
        if st.button("ログイン"):
            st.switch_page("pages/3_Login.py")