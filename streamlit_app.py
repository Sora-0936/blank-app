import streamlit as st
import json
import os
from collections import Counter
from supabase import create_client, Client

# --- Supabase設定 ---
# このブロックをインポートのすぐ下に配置してください
if "supabase_url" in st.secrets and "supabase_key" in st.secrets:
    try:
        url: str = st.secrets["supabase_url"]
        key: str = st.secrets["supabase_key"]
        # ここで 'supabase' という変数を作っています
        supabase: Client = create_client(url, key)
    except Exception as e:
        st.error(f"Supabaseへの接続に失敗しました: {e}")
        st.stop()
else:
    st.error("StreamlitのSecretsに 'supabase_url' と 'supabase_key' が設定されていません。")
    st.stop() # 設定がない場合はここで処理を止める

# --- 1. データの読み込み (既存) ---
@st.cache_data
def load_fuda_data():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, 'fuda.json')
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

fuda_list = load_fuda_data()
if fuda_list:
    fuda_list = sorted(fuda_list, key=lambda x: x['kimariji'])

# --- 2. セッション状態の初期化 ---
if 'selected_fuda' not in st.session_state:
    st.session_state.selected_fuda = []
if 'placement' not in st.session_state:
    st.session_state.placement = {
        "l_top": [], "l_mid": [], "l_low": [],
        "r_top": [], "r_mid": [], "r_low": []
    }

st.set_page_config(page_title="かるた配置サポーター", layout="wide")

# --- 3. Supabase連携機能 (保存と読込) ---
st.sidebar.header("💾 保存済みデータ")

def save_to_supabase(name):
    data = {
        "deck_name": name,
        "selected_fuda": st.session_state.selected_fuda,
        "placement": {
            "l_top": st.session_state.l_top, "l_mid": st.session_state.l_mid, "l_low": st.session_state.l_low,
            "r_top": st.session_state.r_top, "r_mid": st.session_state.r_mid, "r_low": st.session_state.r_low
        }
    }
    response = supabase.table("karuta_decks").insert(data).execute()
    if response.data:
        st.sidebar.success(f"保存しました: {name}")

def load_deck(deck):
    st.session_state.selected_fuda = deck['selected_fuda']
    st.session_state.placement = deck['placement']
    st.rerun()

# 既存データの取得
try:
    decks_response = supabase.table("karuta_decks").select("*").order("created_at", desc=True).execute()
    saved_decks = decks_response.data
    
    if saved_decks:
        deck_to_load = st.sidebar.selectbox("過去の配置をロード", saved_decks, format_func=lambda x: f"{x['deck_name']} ({x['created_at'][:10]})")
        if st.sidebar.button("ロードする"):
            load_deck(deck_to_load)
except Exception as e:
    st.sidebar.error(f"エラー内容: {e}")

st.title("🎴 かるた配置サポーター (Supabase連携版)")

# --- 4. 札の選択フェーズ ---
st.subheader(f"1. 自陣の25枚を選択 (現在: {len(st.session_state.selected_fuda)} / 25 枚)")

# (中略: render_fuda_grid などの選択ロジックは元のコードと同じ)
# ※ st.session_state.selected_fuda を使って描画

# --- 5. 盤面配置フェーズ ---
if len(st.session_state.selected_fuda) == 25:
    st.divider()
    st.header("2. 盤面配置")
    
    options = st.session_state.selected_fuda
    p = st.session_state.placement # ロードされた値をデフォルトにする

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("自陣 左")
        l_top = st.multiselect("上段 (左)", options, default=p.get("l_top", []), key="l_top")
        l_mid = st.multiselect("中段 (左)", options, default=p.get("l_mid", []), key="l_mid")
        l_low = st.multiselect("下段 (左)", options, default=p.get("l_low", []), key="l_low")
    with col_right:
        st.subheader("自陣 右")
        r_top = st.multiselect("上段 (右)", options, default=p.get("r_top", []), key="r_top")
        r_mid = st.multiselect("中段 (右)", options, default=p.get("r_mid", []), key="r_mid")
        r_low = st.multiselect("下段 (右)", options, default=p.get("r_low", []), key="r_low")

    # --- 6. データの保存実行 ---
    st.divider()
    with st.expander("✨ この配置を保存する"):
        deck_name = st.text_input("配置に名前をつけて保存", placeholder="2024年大会用など")
        if st.button("Supabaseに保存"):
            if deck_name:
                save_to_supabase(deck_name)
            else:
                st.warning("名前を入力してください")

    # (中略: 診断ロジックは元のコードと同じ)

import plotly.express as px
import pandas as pd

# --- 7. 統計分析フェーズ ---
st.divider()
st.header("📊 配置の傾向分析")

if st.checkbox("保存データから配置のクセを分析する"):
    try:
        # Supabaseから全データを取得
        res = supabase.table("karuta_decks").select("placement").execute()
        all_decks = res.data

        if not all_decks:
            st.info("データがまだありません。まずは配置を保存してください。")
        else:
            # データの整形
            positions = ["l_top", "l_mid", "l_low", "r_top", "r_mid", "r_low"]
            pos_labels = {
                "l_top": "左上段", "l_mid": "左中段", "l_low": "左下段",
                "r_top": "右上段", "r_mid": "右中段", "r_low": "右下段"
            }
            
            # 各札がどの位置に何回置かれたか集計
            stats_data = []
            for deck in all_decks:
                placement = deck['placement']
                for pos in positions:
                    for fuda_name in placement.get(pos, []):
                        stats_data.append({"fuda": fuda_name, "position": pos_labels[pos]})
            
            df = pd.DataFrame(stats_data)

            # 分析対象の選択
            analysis_target = st.selectbox("分析する札を選択", ["すべての札（総数）"] + sorted(list(df['fuda'].unique())))

            if analysis_target == "すべての札（総数）":
                plot_df = df['position'].value_counts().reindex(pos_labels.values()).fillna(0).reset_index()
                plot_df.columns = ['位置', '配置回数']
                title = "全札の配置分布（どの段がよく使われているか）"
            else:
                plot_df = df[df['fuda'] == analysis_target]['position'].value_counts().reindex(pos_labels.values()).fillna(0).reset_index()
                plot_df.columns = ['位置', '配置回数']
                title = f"札「{analysis_target}」の過去の配置傾向"

            # 2x3のヒートマップ風に表示するための座標設定
            grid_map = {
                "左上段": [0, 0], "左中段": [1, 0], "左下段": [2, 0],
                "右上段": [0, 1], "右中段": [1, 1], "右下段": [2, 1]
            }
            plot_df['row'] = plot_df['位置'].map(lambda x: grid_map[x][0])
            plot_df['col'] = plot_df['位置'].map(lambda x: grid_map[x][1])

            # 可視化：Plotlyのヒートマップ
            z_data = [[0, 0], [0, 0], [0, 0]]
            for _, row in plot_df.iterrows():
                z_data[row['row']][row['col']] = row['配置回数']

            fig = px.imshow(
                z_data,
                labels=dict(x="左右", y="段", color="回数"),
                x=['左', '右'],
                y=['上段', '中段', '下段'],
                text_auto=True,
                color_continuous_scale="Reds",
                title=title
            )
            st.plotly_chart(fig, use_container_width=True)

            st.caption("※保存されたすべてのデッキデータから集計しています。")

    except Exception as e:
        st.error(f"分析データの取得に失敗しました: {e}")
