import streamlit as st
import json

# データの読み込み関数（cache_dataを使うと動作が速くなります）
@st.cache_data
def load_fuda_data():
    with open('fuda.json', 'r', encoding='utf-8') as f:
        return json.load(f)

fuda_list = load_fuda_data()
fuda_dict = {f["kimariji"]: f for f in fuda_list} # 決まり字で検索しやすくする

st.title("かるた初期配置サポーター")

# --- ステップ1: 自陣の25枚を選ぶ ---
st.header("1. 自陣の25枚を選択")
selected_fuda = st.multiselect(
    "25枚選んでください（検索も可能です）",
    options=list(fuda_dict.keys()),
    max_selections=25
)

st.write(f"現在 **{len(selected_fuda)} / 25** 枚選択されています。")
