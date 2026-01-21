import streamlit as st
import json

# --- データの読み込み ---
@st.cache_data
def load_fuda_data():
    with open('fuda.json', 'r', encoding='utf-8') as f:
        return json.load(f)

fuda_list = load_fuda_data()
# 五十音順に並べ替え
fuda_list = sorted(fuda_list, key=lambda x: x['kimariji'])

# --- セッション状態の初期化 ---
if 'selected_fuda' not in st.session_state:
    st.session_state.selected_fuda = []

st.set_page_config(page_title="かるた配置サポーター", layout="wide")
st.title("🎴 かるた札 選択パネル")

# --- 選択状況の表示 ---
st.subheader(f"現在の選択: {len(st.session_state.selected_fuda)} / 25 枚")
if len(st.session_state.selected_fuda) > 0:
    with st.expander("選択中の札を確認・リセット"):
        st.write(", ".join(st.session_state.selected_fuda))
        if st.button("選択をすべてクリア"):
            st.session_state.selected_fuda = []
            st.rerun()

st.divider()

# --- 絞り込み機能 ---
col_filter1, col_filter2 = st.columns([1, 2])
with col_filter1:
    filter_type = st.radio("絞り込み", ["すべて", "一字決まり", "二字決まり", "大山札"], horizontal=True)

# --- タブによる五十音検索 ---
tabs = st.tabs(["あ行", "か・さ行", "た・な行", "は・ま行", "や・ら・わ行"])

def render_fuda_grid(target_chars):
    """特定の頭文字で始まる札をグリッド表示する関数"""
    filtered = [f for f in fuda_list if f['kimariji'][0] in target_chars]
    
    # 絞り込み条件の適用
    if filter_type == "一字決まり":
        filtered = [f for f in filtered if f['type'] == 1]
    elif filter_type == "二字決まり":
        filtered = [f for f in filtered if f['type'] == 2]
    elif filter_type == "大山札":
        filtered = [f for f in filtered if f['type'] >= 6]

    # 3列のグリッドで表示
    cols = st.columns(3)
    for i, fuda in enumerate(filtered):
        with cols[i % 3]:
            # すでに選択されているかチェック
            is_selected = fuda['kimariji'] in st.session_state.selected_fuda
            
            # チェックボックスをボタンのように見せる（実際にはCheckbox）
            if st.checkbox(f"{fuda['kimariji']} ({fuda['shimo'][:6]}...)", value=is_selected, key=fuda['id']):
                if fuda['kimariji'] not in st.session_state.selected_fuda:
                    if len(st.session_state.selected_fuda) < 25:
                        st.session_state.selected_fuda.append(fuda['kimariji'])
                    else:
                        st.warning("これ以上選択できません（上限25枚）")
            else:
                if fuda['kimariji'] in st.session_state.selected_fuda:
                    st.session_state.selected_fuda.remove(fuda['kimariji'])

# タブごとの中身
with tabs[0]: render_fuda_grid("あいうえお")
with tabs[1]: render_fuda_grid("かきくけこさしすせそ")
with tabs[2]: render_fuda_grid("たちつてとなにぬねの")
with tabs[3]: render_fuda_grid("はひふへほまみむめも")
with tabs[4]: render_fuda_grid("やゆよらりるれろわ")

st.divider()

# --- 25枚選んだ後の盤面配置へ ---
if len(st.session_state.selected_fuda) == 25:
    if st.button("この25枚で配置を考える ➔", type="primary"):
        st.success("盤面配置モードへ進みます（ここに配置ロジックを繋げます）")
        # ここに、前回の回答で作成した「盤面配置用コード」を記述または呼び出します
