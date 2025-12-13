# app.py
import runpy
import streamlit as st

# アプリ全体のページ設定
st.set_page_config(page_title="柑橘類の推薦システム", page_icon="🍊", layout="wide")

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
st.write("DEBUG route:", st.session_state.get("route"))
st.write("DEBUG input_submitted:", st.session_state.get("input_submitted"))
st.write("DEBUG top_ids:", st.session_state.get("top_ids"))
# =====================================

# ===== top ページ =====
if route == "top":
    # 1_top.py を実行
    runpy.run_path("pages/1_top.py")  # :contentReference[oaicite:0]{index=0}

    # top 内のボタンで 2_input へ遷移
    if st.session_state.get("navigate_to") == "input":
        st.session_state["route"] = "input"
        del st.session_state["navigate_to"]
        st.rerun()

# ===== input ページ =====
elif route == "input":
    # 入力ページの描画
    runpy.run_path("pages/2_input.py")  # :contentReference[oaicite:1]{index=1}

    # 「完了」ボタンが押され，入力・右側コメントが揃っている場合
    if st.session_state.get("input_submitted"):
        # すぐにフラグを下ろして二重実行を防ぐ
        st.session_state["input_submitted"] = False

        # 入力値を取得（2_input.py がセッションに格納している前提）
        try:
            sweetness = int(st.session_state["val_brix"])
            sourness = int(st.session_state["val_acid"])
            bitterness = int(st.session_state["val_bitterness"])
            aroma = int(st.session_state["val_aroma"])
            juiciness = int(st.session_state["val_moisture"])
            texture = int(st.session_state["val_texture"])
        except Exception as e:
            st.error(f"入力値の取得に失敗した．もう一度入力してほしい．（詳細: {e}）")
        else:
            # 計算ロジックを読み込んで top3 ID を取得
            logic_ns = runpy.run_path("pages/2_calculation_logic.py")  # :contentReference[oaicite:2]{index=2}
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
                # 出力IDをセッションに保存して結果ページへ
                st.session_state["top_ids"] = top_ids
                #.  ログイン有無で結果ページ分岐 By 本間
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
