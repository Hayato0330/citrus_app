# app.py
import runpy
import streamlit as st

from log_utils import append_simple_log

# アプリ全体のページ設定
st.set_page_config(page_title="柑橘類の推薦システム", page_icon="🍊", layout="wide")

# ==== LINE OAuth====
oauth_ns = runpy.run_path("pages/3_line_oauth.py")
oauth_ns["handle_line_oauth"]()
# =========================================

# ====ログイン有無・ユーザー情報==== By 本間
if "user_logged_in" not in st.session_state:
    st.session_state["user_logged_in"] = False
    st.session_state["auth_provider"] = None
    st.session_state["user_id"] = None
    st.session_state["user_name"] = None
    st.session_state["user_email"] = None
    st.session_state["user_picture"] = None
    
if "top_ids" not in st.session_state:
    st.session_state["top_ids"] = None

# 初期ルートを top に設定
if "route" not in st.session_state:
    st.session_state["route"] = "top"

# 入力完了フラグ初期化
if "input_submitted" not in st.session_state:
    st.session_state["input_submitted"] = False

route = st.session_state["route"]

# ===== DEBUG（原因特定用：一時的）=====
# st.write("DEBUG route:", st.session_state.get("route"))
# st.write("DEBUG logged_in:", st.session_state.get("user_logged_in"))
# =====================================

# ===== top ページ（未ログイン）=====
if route == "top":
    runpy.run_path("pages/1_top.py")

    if st.session_state.get("navigate_to") == "input":
        st.session_state["route"] = "input"
        del st.session_state["navigate_to"]
        st.rerun()

    if st.session_state.get("navigate_to") == "login":
        del st.session_state["navigate_to"]
        # OAuth は app.py 冒頭で常に処理されるので rerun だけでOK
        st.rerun()

# ===== top_login ページ（ログイン後トップ）=====
elif route == "input":
    # 入力ページの描画
    runpy.run_path("pages/2_input.py")

    # 「完了」ボタンが押された場合
    if st.session_state.get("input_submitted"):
        # すぐにフラグを下ろして二重実行を防ぐ
        st.session_state["input_submitted"] = False

        input_dict = st.session_state.get("user_preferences")
        if not isinstance(input_dict, dict):
            st.error("入力内容の取得に失敗した．もう一度入力してほしい．")
        else:
            try:
                sweetness = int(input_dict["brix"])
                sourness = int(input_dict["acid"])
                bitterness = int(input_dict["bitterness"])
                aroma = int(input_dict["aroma"])
                juiciness = int(input_dict["moisture"])
                texture = int(input_dict["texture"])
            except Exception as e:
                st.error(f"入力値の取得に失敗した．もう一度入力してほしい．（詳細: {e}）")
            else:
                # 計算ロジックを読み込んで top3 ID を取得
                logic_ns = runpy.run_path("pages/2_calculation_logic.py")
                calculate_top3_ids = logic_ns["calculate_top3_ids"]

                try:
                    top_ids = calculate_top3_ids(
                        sweetness=sweetness,
                        sourness=sourness,
                        bitterness=bitterness,
                        aroma=aroma,
                        juiciness=juiciness,
                        texture=texture,
                    )
                except Exception as e:
                    st.error(f"類似度計算中にエラーが発生した．R2の設定やCSVを確認してほしい．（詳細: {e}）")
                else:
                    # 出力IDをセッションに保存
                    st.session_state["top_ids"] = top_ids

                    # D1へ入力値と結果をまとめて保存
                    result_for_log = [
                        {"id": int(item_id), "rank": rank}
                        for rank, item_id in enumerate(top_ids, start=1)
                    ]
                    append_simple_log(input_dict=input_dict, result_value=result_for_log)

                    # ログイン有無で結果ページ分岐
                    if st.session_state["user_logged_in"]:
                        st.session_state["route"] = "result_login"
                    else:
                        st.session_state["route"] = "result"

                    st.rerun()

    # サイドバーにトップへ戻るボタン
    with st.sidebar:
        if st.button("← トップへ戻る", use_container_width=True):
            st.session_state["route"] = "top"
            st.rerun()

# ===== login ページ =====
elif route == "login":
    runpy.run_path("pages/3_Login.py")

# ===== 結果表示ページ =====
## ログイン有
elif route == "result_login":
    if not st.session_state.get("top_ids"):
        st.session_state["route"] = "top"
        st.rerun()
    runpy.run_path("pages/3_output_login.py")

    with st.sidebar:
        if st.button("← 入力に戻る", use_container_width=True):
            st.session_state["route"] = "input"
            st.rerun()

## ログイン無
elif route == "result":
    if not st.session_state.get("top_ids"):
        st.session_state["route"] = "top"
        st.rerun()
    runpy.run_path("pages/3_output_nologin.py")

    with st.sidebar:
        if st.button("← 入力に戻る", use_container_width=True):
            st.session_state["route"] = "input"
            st.rerun()
