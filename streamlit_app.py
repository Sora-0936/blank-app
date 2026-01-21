import streamlit as st
import json
import os

# 1. データの読み込み
@st.cache_data
def load_fuda_data():
    file_path = 'fuda. json'
    if not os.path.exists(file_path):
        st.error(f"エラー: {file_path} が見つかりません。GitHubにアップロードされているか確認してください。")
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

fuda_list = load_fuda_data()
fuda_dict = {f["kimariji"]: f for f in fuda_list}

# アプリのタイトル
st.set_page_config(page_title="かるた配置サポーター", layout="wide")
st.title("🎴 競技かるた・初心者向け定位置サポーター")
st.write("自陣の25枚を選んで、自分にぴったりの配置を考えましょう。")

# --- ステップ1: 自陣の25枚を選択 ---
st.sidebar.header("1. 自陣の25枚を選択")
selected_names = st.sidebar.multiselect(
    "札を選んでください",
    options=list(fuda_dict.keys()),
    max_selections=25,
    help="25枚まで選べます。決まり字で検索も可能です。"
)

st.sidebar.write(f"現在の選択: **{len(selected_names)} / 25枚**")

# --- ステップ2: 配置のメイン画面 ---
if len(selected_names) < 25:
    st.warning("左側のサイドバーから、まずは25枚の札を選んでください。")
else:
    st.success("25枚選ばれました！各段に振り分けてみましょう。")
    
    # 25枚を振り分けるためのリスト（現在選択されていない札を表示するため）
    remaining_fuda = list(selected_names)

    # 盤面を模したレイアウト (左陣・右陣 × 3段)
    st.header("2. 盤面配置")
    
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("自陣 左（Hidari）")
        l_top = st.multiselect("上段", options=selected_names, key="l_top")
        l_mid = st.multiselect("中段", options=selected_names, key="l_mid")
        l_low = st.multiselect("下段", options=selected_names, key="l_low")

    with col_right:
        st.subheader("自陣 右（Migi）")
        r_top = st.multiselect("上段", options=selected_names, key="r_top")
        r_mid = st.multiselect("中段", options=selected_names, key="r_mid")
        r_low = st.multiselect("下段", options=selected_names, key="r_low")

    # --- ステップ3: 初心者向け診断アドバイス ---
    st.divider()
    st.header("🔍 配置診断アドバイス")

    # 配置された札の合計を確認
    all_placed = l_top + l_mid + l_low + r_top + r_mid + r_low
    unique_placed = set(all_placed)

    if len(all_placed) != 25:
        st.info(f"現在 {len(all_placed)} 枚配置されています。25枚すべて配置すると詳細なアドバイスが表示されます。")
    elif len(all_placed) != len(unique_placed):
        st.error("⚠️ 同じ札が複数の場所に配置されています。重複を解消してください。")
    else:
        # アドバイスロジックの例
        advices = []
        
        # 1. 一字決まりのチェック
        ichiji = ["む", "す", "め", "ふ", "さ", "ほ", "せ"]
        placed_ichiji = [f for f in all_placed if f in ichiji]
        low_tier_ichiji = [f for f in (l_low + r_low) if f in ichiji]
        
        if len(placed_ichiji) > len(low_tier_ichiji):
            advices.append("💡 **一字決まりの札**は、反応しやすいように下段に置くのがおすすめです。")
        
        # 2. 友札（頭文字）の重複チェック
        first_chars = [f[0] for f in all_placed]
        from collections import Counter
        counts = Counter(first_chars)
        duplicates = [char for char, count in counts.items() if count > 1]
        
        if duplicates:
            advices.append(f"💡 「{'」「'.join(duplicates)}」で始まる**友札**が複数あります。これらは左右に分けて置くと、お手つきを防ぎやすくなります。")

        # アドバイスの表示
        if advices:
            for a in advices:
                st.write(a)
        else:
            st.balloons()
            st.success("素晴らしい配置です！バランス良く配置されています。")

# 100首一覧をいつでも見れるように（デバッグ・参考用）
with st.expander("参考：百人一首 一覧を表示"):
    st.table(fuda_list)
