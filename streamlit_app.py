import streamlit as st
import json
import os
from collections import Counter

# --- 1. データの読み込み ---
@st.cache_data
def load_fuda_data():
    # クラウド環境でのパス解決
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, 'fuda.json')
    
    if not os.path.exists(file_path):
        st.error("fuda.json が見つかりません。GitHubにアップロードされているか確認してください。")
        return []
        
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

fuda_list = load_fuda_data()
if fuda_list:
    fuda_list = sorted(fuda_list, key=lambda x: x['kimariji'])

# --- 2. セッション状態の初期化 ---
if 'selected_fuda' not in st.session_state:
    st.session_state.selected_fuda = []

st.set_page_config(page_title="かるた配置サポーター", layout="wide")
st.title("🎴 かるた札 選択 & 配置パネル")

# --- 3. 札の選択フェーズ ---
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

# --- 4. 盤面配置フェーズ ---
if len(st.session_state.selected_fuda) == 25:
    st.header("2. 盤面配置")
    st.info("選んだ25枚を各段に振り分けてください。")
    
    # 選択された札のリスト
    options = st.session_state.selected_fuda
    
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("自陣 左")
        l_top = st.multiselect("上段 (左)", options=options, key="l_top")
        l_mid = st.multiselect("中段 (左)", options=options, key="l_mid")
        l_low = st.multiselect("下段 (左)", options=options, key="l_low")

    with col_right:
        st.subheader("自陣 右")
        r_top = st.multiselect("上段 (右)", options=options, key="r_top")
        r_mid = st.multiselect("中段 (右)", options=options, key="r_mid")
        r_low = st.multiselect("下段 (右)", options=options, key="r_low")

    # --- 5. 配置診断ロジック ---
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

# 参考用データ表示
with st.expander("参考：札データ一覧"):
    st.write(fuda_list)
