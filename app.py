import runpy
import streamlit as st

# アプリ全体のページ設定（必要に応じて調整）
st.set_page_config(page_title="柑橘類の推薦システム", page_icon="🍊", layout="wide")

# 初期ルートを top に設定
if "route" not in st.session_state:
    st.session_state["route"] = "top"

# ルーティング本体
route = st.session_state["route"]

if route == "top":

    # 1_top.py を実行（数字始まりなので import ではなく run_path を使う）
    runpy.run_path("pages/1_top.py")

    # ボタンが押されていれば route を切り替えて即時再実行
    if st.session_state.get("navigate_to") == "input":
        st.session_state["route"] = "input"
        del st.session_state["navigate_to"]  # ここで消費してクリア
        st.rerun()

elif route == "input":
    # 2_input.py を実行
    runpy.run_path("pages/2_input.py")

    # ついでに戻るボタンを用意（任意）
    with st.sidebar:
        if st.button("← トップへ戻る", use_container_width=True):
            st.session_state["route"] = "top"
            st.rerun()

elif route == "result":
    # 3_output_nologin.py を実行（結果ページ）
    runpy.run_path("pages/3_output_nologin.py")
