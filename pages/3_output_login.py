# pages/3_output_login.py
import streamlit as st
import numpy as np
import pandas as pd
from urllib.parse import quote
import textwrap
import base64
from pathlib import Path
import runpy

# ===== ページ設定 =====
st.set_page_config(page_title="柑橘おすすめ診断 - 結果", page_icon="🍊", layout="wide")

@st.cache_data
def local_image_to_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
        st.warning(f"背景画像が見つかりません: {p}")
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

IMG_PATH = Path(__file__).resolve().parent.parent / "other_images/top_background.png"
bg_url = local_image_to_data_url(str(IMG_PATH))

# ===== CSS =====
st.markdown(textwrap.dedent("""
<style>
body { background-color: #FFF8F0; }

.card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,.12);
  border: 1px solid #eee;
}
.card h2, .card h3 { color:#000; margin-top:0; }

.match-score { color:#f59e0b; font-weight:bold; }

.link-btn {
  display:inline-block;
  padding:8px 14px;
  margin:6px 0;
  border-radius:6px;
  color:#fff !important;
  text-decoration:none;
  font-weight:600;
  font-size:14px;
  transition:opacity .15s;
  cursor:pointer;
}
.link-btn img { height:16px; vertical-align:middle; margin-right:6px; }
.link-btn:hover { opacity:.9; }

.amazon-btn { background-color:#00BFFF; }
.rakuten-btn { background-color:#BF0000; }
.satofuru-btn { background-color:#D2691E; }
.x-btn {
  background-color:#ffffff;
  color:#000 !important;
  border:1px solid #ddd;
}

.amazon-btn:hover { background-color:#87CEEB; }
.rakuten-btn:hover { background-color:#990000; }
.satofuru-btn:hover { background-color:#b85c19; }
.x-btn:hover { background-color:#f5f5f5; color:#000 !important; }
</style>
"""), unsafe_allow_html=True)

st.markdown(
    f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: url("{bg_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] {{
        background: transparent !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ===== 外部リンク生成 =====
def build_amazon_url(name: str) -> str:
    # 生果に寄せつつ、除外は「園芸・販促」中心に抑える
    q = quote(f'{name} 柑橘 みかん 生果 -家庭用 -贈答 -苗 -苗木 -種 -栽培 -のぼり')
    return f"https://www.amazon.co.jp/s?k={q}"

def build_rakuten_url(name: str) -> str:
    # 品種名だけだと広すぎるので、ユーザーが実際に入れがちな語を足す
    q = quote(f"{name} 柑橘 みかん 家庭用 贈答")
    return f"https://search.rakuten.co.jp/search/mall/{q}/"

def build_satofuru_url(name: str) -> str:
    # さとふる側の検索URL仕様が不安定なので、site検索で確実に飛ばす
    q = quote(f"site:satofull.jp {name} みかん 柑橘")
    return f"https://www.google.com/search?q={q}"

# ===== 何派 + SNSシェア =====
def _safe_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def compute_taste_type() -> str:
    """
    入力6指標から「◯◯◯◯派」を自動生成する。
    - 上位2特徴を連結（例：さっぱり香り派）
    - 同点が多いときのブレを防ぐために優先順位でタイブレーク
    """
    vals = {
        "sweet": _safe_int(st.session_state.get("val_brix")),
        "sour": _safe_int(st.session_state.get("val_acid")),
        "bitter": _safe_int(st.session_state.get("val_bitterness")),
        "aroma": _safe_int(st.session_state.get("val_aroma")),
        "juicy": _safe_int(st.session_state.get("val_moisture")),
        "texture": _safe_int(st.session_state.get("val_texture")),
    }

    labels = {
        "sweet": "甘党",
        "sour": "さっぱり",
        "bitter": "大人味",
        "aroma": "香り",
        "juicy": "ジューシー",
        "texture": "ぷりぷり",
    }

    # 同点時の優先順位（好みで調整OK）
    # 「香り・酸味・甘さ」あたりが“診断っぽさ”が出やすい
    priority = ["aroma", "sour", "sweet", "juicy", "texture", "bitter"]
    pr = {k: i for i, k in enumerate(priority)}

    # (値が高いほど上) → (同点なら優先順位が高いほど上)
    ranked_keys = sorted(
        vals.keys(),
        key=lambda k: (-vals[k], pr.get(k, 999))
    )

    top1 = ranked_keys[0]
    top2 = ranked_keys[1] if len(ranked_keys) > 1 else top1

    a = labels.get(top1, "好み")
    b = labels.get(top2, "")

    # 2位が同じ特徴になってしまったら1語にする
    if top1 == top2 or b == "":
        return f"{a}派"

    return f"{a}{b}派"


def build_twitter_share(names: list[str]) -> str:

    app_url = "https://citrusapp-ukx8zpjspw4svc7dmd5jnj.streamlit.app/"
    taste_type = compute_taste_type()

    n1 = names[0] if len(names) > 0 and names[0] else "—"
    n2 = names[1] if len(names) > 1 and names[1] else "—"
    n3 = names[2] if len(names) > 2 and names[2] else "—"

    text_raw = (
        "🍊柑橘おすすめ診断の結果！\n\n"
        f"【私は “{taste_type}” でした🍋】\n"
        "あなたは何派？\n\n"
        f"🏆 1位：{n1}\n"
        f"🥈 2位：{n2}\n"
        f"🥉 3位：{n3}\n\n"
        "あなたのタイプも出るよ👇\n"
        "#柑橘おすすめ\n"
        f"{app_url}"
    )

    return f"https://twitter.com/intent/tweet?text={quote(text_raw)}"

# ===== データ取得（nologin と同じ思想）=====
TOPK = 3

top_ids = st.session_state.get("top_ids")
if not top_ids:
    st.error("診断結果が見つからないため，トップページからやり直してほしい．")
    with st.sidebar:
        if st.button("← トップへ戻る", use_container_width=True):
            st.session_state["route"] = "top_login" if st.session_state.get("user_logged_in") else "top"
            st.rerun()
    st.stop()

# 入力値（app.py が session_state に入れてる前提）
try:
    user_vec = np.array(
        [
            int(st.session_state["val_brix"]),
            int(st.session_state["val_acid"]),
            int(st.session_state["val_bitterness"]),
            int(st.session_state["val_aroma"]),
            int(st.session_state["val_moisture"]),
            int(st.session_state["val_texture"]),
        ],
        dtype=float,
    )
except Exception as e:
    st.error(f"入力値が見つからない／取得できませんでした（詳細: {e}）")
    st.stop()

# 2_calculation_logic から DF 作成＆スコアリングを取得
ns = runpy.run_path("pages/2_calculation_logic.py")

prepare_df = ns.get("_prepare_dataframe")
score_items = ns.get("score_items")

if prepare_df is None:
    st.error("2_calculation_logic.py に _prepare_dataframe が見つかりません。")
    st.stop()

df_all = prepare_df()

# score_items が無い場合は最低限のコサイン類似で計算（落ちない保険）
if score_items is None:
    feature_cols = ["brix", "acid", "bitter", "smell", "moisture", "elastic"]
    if not all(c in df_all.columns for c in feature_cols):
        st.error("特徴量カラムが不足しています（brix/acid/bitter/smell/moisture/elastic）。")
        st.stop()
    X = df_all[feature_cols].astype(float).values

    def normalize(v): return v / (np.linalg.norm(v) + 1e-8)
    u = normalize(user_vec)
    Xn = np.array([normalize(x) for x in X])
    scores = Xn @ u
    ranked_all = df_all.copy()
    ranked_all["score"] = scores
else:
    # 2_calculation_logic 側の定義に合わせて呼ぶ（weights は無ければ渡さない）
    try:
        ranked_all = score_items(df_all, user_vec, season_pref="", weights=None)
    except TypeError:
        ranked_all = score_items(df_all, user_vec, season_pref="")

# top_ids の順序を保持して抽出（表示順位は top_ids を優先）
df_sel = ranked_all[ranked_all["id"].isin(top_ids)].copy()
df_sel["__order"] = pd.Categorical(df_sel["id"], categories=top_ids, ordered=True)
df_sel = df_sel.sort_values("__order")

top_items = df_sel.head(TOPK)

# ===== UI =====
st.markdown("### 🍊 柑橘おすすめ診断 - 結果")

cols_top = st.columns(2)
cols_bottom = st.columns(2)
quadrants = [cols_top[0], cols_top[1], cols_bottom[0], cols_bottom[1]]

def pick(row, *keys, default=None):
    for k in keys:
        v = getattr(row, k, None)
        if v is not None and v != "":
            return v
    return default

def render_card(i, row):
    # 列名が name / Item_name どちらでも動くように
    name = pick(row, "name", "Item_name", default="不明")
    desc = pick(row, "description", default="")
    image_url = pick(row, "image_path", default="https://via.placeholder.com/200x150?text=No+Image")
    score_pct = float(pick(row, "score", default=0.0)) * 100

    html = f"""
    <div class="card">
      <h2>{i}. {name}</h2>
      <div style="display:flex;gap:20px;align-items:flex-start;">
        <div style="flex:1;">
          <img src="{image_url}" style="max-width:100%;border-radius:8px;margin-bottom:10px;">
          <p>マッチ度: <span class="match-score">{score_pct:.1f}%</span></p>
          <p style="font-size:14px;color:#333;">{desc}</p>
        </div>
        <div style="flex:1;text-align:center;">
            <a class="link-btn amazon-btn" href="{build_amazon_url(name)}" target="_blank">
                <img src="https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg" alt="Amazon">
                Amazonで生果を探す
            </a><br>
            <a class="link-btn rakuten-btn" href="{build_rakuten_url(name)}" target="_blank">
                <img src="https://upload.wikimedia.org/wikipedia/commons/6/6a/Rakuten_Global_Brand_Logo.svg" alt="Rakuten">
                楽天で贈答/家庭用を探す
            </a><br>
            <a class="link-btn satofuru-btn" href="{build_satofuru_url(name)}" target="_blank">
                <img src="https://www.satofull.jp/favicon.ico" alt="さとふる">
                ふるさと納税で探す
            </a>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

for i, row in enumerate(top_items.itertuples(), start=1):
    with quadrants[i - 1]:
        render_card(i, row)

with quadrants[3]:
    names = [pick(r, "name", "Item_name", default="不明") for r in top_items.itertuples()]
    twitter_url = build_twitter_share(names)

    st.markdown(f"""
    <div class="card" style="text-align:center;">
      <h3>まとめ</h3>
      <a class="link-btn x-btn" href="{twitter_url}" target="_blank">
        <img src="https://cdn.cms-twdigitalassets.com/content/dam/about-twitter/x/brand-toolkit/logo-black.png.twimg.2560.png" alt="X">
        Xでシェア
      </a>
    </div>
    """, unsafe_allow_html=True)

    # まとめカードの下に“もう一回診断”を追加（ログイン版はこれだけ）
    if st.button("🔁 もう一回診断する（入力を変える）", use_container_width=True):
        # 念のため古い結果をクリア
        st.session_state["top_ids"] = None
        st.session_state["route"] = "input"
        st.rerun()


with st.sidebar:
    if st.button("← トップへ戻る", use_container_width=True):
        st.session_state["route"] = "top_login" if st.session_state.get("user_logged_in") else "top"
        st.rerun()
