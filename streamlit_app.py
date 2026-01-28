import streamlit as st
import json
import os
from collections import Counter
from supabase import create_client, Client

# Supabase接続
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

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
if len(st.session_state.selected_fuda) > 0:
    with st.expander("選択中の札を確認・リセット"):
        st.write(", ".join(st.session_state.selected_fuda))
        if st.button("選択をすべてクリア"):
            st.session_state.selected_fuda = []
            st.rerun()

st.divider()

# 絞り込み機能
filter_type = st.radio("絞り込み", ["すべて", "一字決まり", "二字決まり", "大山札"], horizontal=True)

# 五十音タブ
tabs = st.tabs(["あ行", "か・さ行", "た・な行", "は・ま行", "や・ら・わ行"])

def render_fuda_grid(target_chars):
    filtered = [f for f in fuda_list if f['kimariji'][0] in target_chars]
    if filter_type == "一字決まり":
        filtered = [f for f in filtered if f['type'] == 1]
    elif filter_type == "二字決まり":
        filtered = [f for f in filtered if f['type'] == 2]
    elif filter_type == "大山札":
        filtered = [f for f in filtered if f['type'] >= 6]

    cols = st.columns(3)
    for i, fuda in enumerate(filtered):
        with cols[i % 3]:
            # チェックボックスの状態管理
            is_selected = fuda['kimariji'] in st.session_state.selected_fuda
            if st.checkbox(f"{fuda['kimariji']} ({fuda['shimo'][:6]}...)", value=is_selected, key=f"select_{fuda['id']}"):
                if fuda['kimariji'] not in st.session_state.selected_fuda:
                    if len(st.session_state.selected_fuda) < 25:
                        st.session_state.selected_fuda.append(fuda['kimariji'])
                        st.rerun()
                    else:
                        st.warning("これ以上選択できません（上限25枚）")
            else:
                if fuda['kimariji'] in st.session_state.selected_fuda:
                    st.session_state.selected_fuda.remove(fuda['kimariji'])
                    st.rerun()

with tabs[0]: render_fuda_grid("あいうえお")
with tabs[1]: render_fuda_grid("かきくけこさしすせそ")
with tabs[2]: render_fuda_grid("たちつてとなにぬねの")
with tabs[3]: render_fuda_grid("はひふへほまみむめも")
with tabs[4]: render_fuda_grid("やゆよらりるれろわ")

st.divider()

# --- 5. 盤面配置フェーズ ---
if len(st.session_state.selected_fuda) == 25:
    st.header("2. 盤面配置")
    st.info("選んだ25枚を各段に振り分けてください。一度選んだ札は他の段には表示されなくなります。")
    
    # 選択された札の全リスト
    base_options = st.session_state.selected_fuda
    
    # すでにどこかの段に配置されている札を特定する
    # セッション状態から現在の選択値を取得（未選択時は空リスト）
    lt = st.session_state.get("l_top", [])
    lm = st.session_state.get("l_mid", [])
    ll = st.session_state.get("l_low", [])
    rt = st.session_state.get("r_top", [])
    rm = st.session_state.get("r_mid", [])
    rl = st.session_state.get("r_low", [])
    
    all_placed = set(lt + lm + ll + rt + rm + rl)

    def get_available_options(current_segment_values):
        """
        現在の段で選ばれている札 + まだどこにも選ばれていない札 を返す
        """
        # 他の段で使われている札を除外
        others_placed = all_placed - set(current_segment_values)
        return [f for f in base_options if f not in others_placed]

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("自陣 左")
        l_top = st.multiselect("上段 (左)", options=get_available_options(lt), key="l_top")
        l_mid = st.multiselect("中段 (左)", options=get_available_options(lm), key="l_mid")
        l_low = st.multiselect("下段 (左)", options=get_available_options(ll), key="l_low")

    with col_right:
        st.subheader("自陣 右")
        r_top = st.multiselect("上段 (右)", options=get_available_options(rt), key="r_top")
        r_mid = st.multiselect("中段 (右)", options=get_available_options(rm), key="r_mid")
        r_low = st.multiselect("下段 (右)", options=get_available_options(rl), key="r_low")

    # 配置状況のサマリー
    placed_count = len(all_placed)
    st.write(f"📊 現在の配置済み枚数: **{placed_count} / 25**")
    if placed_count < 25:
        st.write(f"残り: {', '.join([f for f in base_options if f not in all_placed])}")

    # --- 6. データの保存実行 ---
    st.divider()
    with st.expander("✨ この配置を保存する"):
        deck_name = st.text_input("配置に名前をつけて保存", placeholder="2024年大会用など")
        if st.button("Supabaseに保存"):
            if deck_name:
                save_to_supabase(deck_name)
            else:
                st.warning("名前を入力してください")

    # --- 7. 配置診断ロジック ---
    st.divider()
    st.header("🔍 配置診断アドバイス")

    all_placed = l_top + l_mid + l_low + r_top + r_mid + r_low
    unique_placed = set(all_placed)

    if len(all_placed) < 25:
        st.write(f"現在 {len(all_placed)} / 25 枚配置済みです。すべて配置すると診断が始まります。")
    elif len(all_placed) > 25 or len(all_placed) != len(unique_placed):
        st.error("⚠️ 札が重複して配置されているか、枚数が合いません。確認してください。")
    else:
        # アドバイスの生成
        advices = []
        ichiji = ["む", "す", "め", "ふ", "さ", "ほ", "せ"]
        placed_ichiji = [f for f in all_placed if f in ichiji]
        low_tier_ichiji = [f for f in (l_low + r_low) if f in ichiji]
        
        if len(placed_ichiji) > len(low_tier_ichiji):
            advices.append("💡 **一字決まりの札**は、より反応しやすいように「下段」に置くのが定石です。")
        
        first_chars = [f[0] for f in all_placed]
        counts = Counter(first_chars)
        duplicates = [char for char, count in counts.items() if count > 1]
        
        if duplicates:
            advices.append(f"💡 「{'」「'.join(duplicates)}」で始まる**友札**が自陣に複数あります。これらを左右に分けて配置すると、お手つきを防ぎやすくなります。")

        if advices:
            for a in advices:
                st.write(a)
        else:
            st.balloons()
            st.success("素晴らしい配置です！基本に忠実なバランスです。")

else:
    st.warning("まず上のパネルから25枚の札を選んでください。")


# 100首一覧をいつでも見れるように（デバッグ・参考用）
with st.expander("参考：百人一首 一覧を表示"):
    st.table(fuda_list)


import plotly.express as px
import pandas as pd

# --- 8. 統計分析フェーズ ---
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
