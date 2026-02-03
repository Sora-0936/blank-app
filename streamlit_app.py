import streamlit as st
import json
import os
from collections import Counter
from supabase import create_client, Client
import plotly.express as px
import pandas as pd

# --- Supabase接続 ---
# Secretsから取得
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 1. データの読み込み ---
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

st.set_page_config(page_title="競技かるた配置サポーター", layout="wide")

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

try:
    decks_response = supabase.table("karuta_decks").select("*").order("created_at", desc=True).execute()
    saved_decks = decks_response.data
    if saved_decks:
        deck_to_load = st.sidebar.selectbox("過去の配置をロード", saved_decks, format_func=lambda x: f"{x['deck_name']} ({x['created_at'][:10]})")
        if st.sidebar.button("ロードする"):
            load_deck(deck_to_load)
except Exception as e:
    st.sidebar.error(f"エラー内容: {e}")

st.title("🎴 競技かるた配置サポーター ")

# --- 競技かるたガイド（アプリ内表示用） ---
with st.expander("💡 初めての方へ：競技かるたの基本ルールと戦略"):
    st.markdown("""
    ### 1. 競技かるたの基本
    競技かるたは、小倉百人一首を用いた**「畳の上の格闘技」**です。
    - **勝利条件**: 自陣の25枚を先にゼロにした方が勝ちです。
    - **札の取り方**: 読み手が「上の句」を読み始めた瞬間に、場にある「下の句」の札を取ります。
    - **送り札**: 相手陣の札を取った場合、自陣の札を1枚相手に「送る」ことができます。

    ### 2. 戦略の鍵「決まり字」
    全ての歌を最後まで聞く必要はありません。
    - **決まり字**: 「その音を聞けば、その札だと確定する」最小単位の音のことです。
    - **例**: 「む」で始まる歌は1つしかないため（一字決まり）、「む」の瞬間に反応します。

    ### 3. なぜ「配置」が重要なのか？
    自陣の25枚をどこに置くかは、勝敗に直結する非常に重要な戦略です。
    - **暗記の効率**: 決まり字が似ている札（友札）を離して置くことで、お手つきを防ぎます。
    - **守りと攻め**: 自分が得意な札や、短い決まり字の札を反応しやすい位置（下段など）に配置するのが定石です。
    
    ---
    *このアプリを使って、自分だけの最強の配置を研究しましょう！*
    """)
    
# --- 4. 札の選択フェーズ ---
st.subheader(f"1. 自陣の25枚を選択 (現在: {len(st.session_state.selected_fuda)} / 25 枚)")
if len(st.session_state.selected_fuda) > 0:
    with st.expander("選択中の札を確認・リセット"):
        st.write(", ".join(st.session_state.selected_fuda))
        if st.button("選択をすべてクリア"):
            st.session_state.selected_fuda = []
            st.rerun()

st.divider()
filter_type = st.radio("絞り込み", ["すべて", "一字決まり", "二字決まり", "大山札"], horizontal=True)
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
    st.info("一度選んだ札は他の段には表示されなくなります。")
    
    base_options = st.session_state.selected_fuda
    lt = st.session_state.get("l_top", [])
    lm = st.session_state.get("l_mid", [])
    ll = st.session_state.get("l_low", [])
    rt = st.session_state.get("r_top", [])
    rm = st.session_state.get("r_mid", [])
    rl = st.session_state.get("r_low", [])
    
    all_placed_set = set(lt + lm + ll + rt + rm + rl)

    def get_available_options(current_vals):
        others_placed = all_placed_set - set(current_vals)
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

    placed_count = len(all_placed_set)
    st.write(f"📊 現在の配置済み枚数: **{placed_count} / 25**")
    
    # 保存
    with st.expander("✨ この配置を保存する"):
        deck_name = st.text_input("配置名", placeholder="例：基本配置")
        if st.button("Supabaseに保存"):
            if deck_name:
                save_to_supabase(deck_name)
            else:
                st.warning("名前を入力してください")

# --- 7. 配置診断（改善版） ---
    st.divider()
    st.header("🔍 AI配置診断アドバイス")

    all_placed_list = l_top + l_mid + l_low + r_top + r_mid + r_low

    if len(all_placed_list) == 25:
        advices = []
        
        # 札の分類準備
        # fuda_listから情報を引き出すための辞書を作成
        fuda_info = {f['kimariji']: f for f in fuda_list}
        
        # 各段の札リスト
        top_tier = l_top + r_top
        mid_tier = l_mid + r_mid
        low_tier = l_low + r_low
        mid_low_tier = mid_tier + low_tier

        # 1. 決まり字が1字の札 (type == 1)
        ichiji_fuda = [f for f in all_placed_list if fuda_info.get(f, {}).get('type') == 1]
        ichiji_not_in_low = [f for f in ichiji_fuda if f not in low_tier]
        if ichiji_not_in_low:
            advices.append("""
            **【1字決まりの配置】**
            決まり字が1字の札がすべて下段に配置されていないようです。自陣下段に配置することで、相手に取られにくく自分がすぐに反応し取ることができる配置になります。
            また右下段と左下段で、取る1字の札を分けることも重要です。右と左で、どちらの方がよく反応して取ることができるのかを練習するなかで見つけましょう。
            """)

        # 2. 決まり字が2字の札 (type == 2)
        niji_fuda = [f for f in all_placed_list if fuda_info.get(f, {}).get('type') == 2]
        if niji_fuda:
            niji_in_mid_low = [f for f in niji_fuda if f in mid_low_tier]
            # 3分の2以下の場合にアドバイス
            if len(niji_in_mid_low) <= (len(niji_fuda) * 2 / 3):
                advices.append("""
                **【2字決まりの配置】**
                決まり字が2字の札が上段に多く配置されているようです。このままでは、相手にすぐ攻められる配置です。
                中段以下に多く配置することで、札との距離が相手よりも自分との方が近くなり、より取りやすくなります。
                """)

        # 3. 友札は分けて配置されているか
        counts = Counter([f[0] for f in all_placed_list])
        # 同じ音から始まる札（友札候補）
        tomo_chars = [char for char, count in counts.items() if count > 1]
        tomo_issue = False
        for char in tomo_chars:
            # 同じ段に同じ音の札が2枚以上あるかチェック
            if any(len([f for f in tier if f.startswith(char)]) > 1 for tier in [l_top, l_mid, l_low, r_top, r_mid, r_low]):
                tomo_issue = True
                break
        if tomo_issue:
            advices.append("""
            **【友札の配置】**
            友札が隣り合って配置されているようです。そのように配置することで、自陣で取りやすい一方、相手側も狙いやすい配置となってしまいます。
            最初のうちは離して配置することをお勧めします。競技かるたに慣れてきて、くっつけた方が取りやすいと判断した際はそのようにするとよいと思います。
            """)

        # 4. 同じ音から始まる札の分散
        # 同じ側に同じ音が3枚以上固まっている場合などを判定
        scatter_issue = False
        for char in tomo_chars:
            left_side = l_top + l_mid + l_low
            right_side = r_top + r_mid + r_low
            if len([f for f in left_side if f.startswith(char)]) >= 3 or len([f for f in right_side if f.startswith(char)]) >= 3:
                scatter_issue = True
                break
        if scatter_issue:
            advices.append("""
            **【音の分散】**
            同じ音から始まる札がかたまって配置されているようです。この場合、相手は音を聞いただけでそのエリアに手を出し、自分よりも先に札に触ることが考えられます。
            相手が攻めづらい配置にするためにも、なるべく同じ音から始まる札が散らばるような配置を考えましょう。
            """)

        # 5. 大山札 (type == 6)
        oyama_fuda = [f for f in all_placed_list if fuda_info.get(f, {}).get('type') == 6]
        # 下段の端（各リストの最初か最後）にない場合
        oyama_issue = False
        for f in oyama_fuda:
            if f not in [l_low[0] if l_low else "", l_low[-1] if l_low else "", r_low[0] if r_low else "", r_low[-1] if r_low else ""]:
                oyama_issue = True
                break
        if oyama_issue:
            advices.append("""
            **【大山札の配置】**
            大山札が下段の端（内側か外側）に配置されていないようです。大山札を取る際は、手で札を囲うことで相手から守る必要があります。
            中段などでは正確に囲うことができないため、下段の端に配置しましょう。
            """)

        # --- 判定結果の表示 ---
        if advices:
            st.info("💡 **「自分が取りやすく、相手に攻められにくい配置」**を考えることが重要です。これに沿って、あなたの配置に対してアドバイスをします。")
            for a in advices:
                st.write(a)
        else:
            st.balloons()
            st.success("""
            🎉 **よく考えられた配置です！**
            これから自分の配置を覚えて、素早く札を取ることができるように練習を積んでいきましょう。
            また、慣れてきたら、この配置に固執するのではなく、試合展開に応じて臨機応変に対応できるようになるとなお良いですね。
            """)
    else:
        st.warning("まず25枚すべての札を配置してください。")

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
        
# --- 9. 暗記トレーニングフェーズ ---
st.divider()
st.header("🧠 暗記トレーニング")

all_placed_list = (
    st.session_state.get("l_top", []) + st.session_state.get("l_mid", []) + st.session_state.get("l_low", []) +
    st.session_state.get("r_top", []) + st.session_state.get("r_mid", []) + st.session_state.get("r_low", [])
)

# 札をタイル状に表示する関数（関数定義はブロックの外で行うのが一般的）
def display_karuta_row(label, fuda_list):
    st.write(f"**{label}**")
    if fuda_list:
        cols = st.columns(len(fuda_list))
        for i, fuda in enumerate(fuda_list):
            cols[i].button(fuda, key=f"mem_{label}_{fuda}", disabled=True)
    else:
        st.write("（札なし）")

if len(all_placed_list) < 25:
    st.info("25枚すべての配置を完了させると、暗記テストを開始できます。")
else:
    if 'game_mode' not in st.session_state:
        st.session_state.game_mode = "waiting" # waiting, memorizing, testing

    col1, col2 = st.columns(2)
    with col1:
        if st.button("暗記スタート！ (配置を表示)"):
            st.session_state.game_mode = "memorizing"
    with col2:
        if st.button("テスト開始！ (配置を隠す)"):
            st.session_state.game_mode = "testing"

    # --- 暗記モード ---
    if st.session_state.game_mode == "memorizing":
        st.success("今のうちに配置を覚えましょう！")
        
        m_col_left, m_col_right = st.columns(2)
        with m_col_left:
            display_karuta_row("左上段", st.session_state.l_top)
            display_karuta_row("左中段", st.session_state.l_mid)
            display_karuta_row("左下段", st.session_state.l_low)
        with m_col_right:
            display_karuta_row("右上段", st.session_state.r_top)
            display_karuta_row("右中段", st.session_state.r_mid)
            display_karuta_row("右下段", st.session_state.r_low)

    # --- テストモード ---
    elif st.session_state.game_mode == "testing":
        st.warning("空欄を埋めてください。")
        
        user_answers = {}
        test_cols = st.columns(2)
        
        with test_cols[0]:
            st.write("### 左側")
            user_answers["l_top"] = st.multiselect("左上段にあるはずの札は？", options=base_options, key="ans_lt")
            user_answers["l_mid"] = st.multiselect("左中段にあるはずの札は？", options=base_options, key="ans_lm")
            user_answers["l_low"] = st.multiselect("左下段にあるはずの札は？", options=base_options, key="ans_ll")
        with test_cols[1]:
            st.write("### 右側")
            user_answers["r_top"] = st.multiselect("右上段にあるはずの札は？", options=base_options, key="ans_rt")
            user_answers["r_mid"] = st.multiselect("右中段にあるはずの札は？", options=base_options, key="ans_rm")
            user_answers["r_low"] = st.multiselect("右下段にあるはずの札は？", options=base_options, key="ans_rl")
            
        if st.button("答え合わせ"):
            correct_data = {
                "l_top": st.session_state.l_top, "l_mid": st.session_state.l_mid, "l_low": st.session_state.l_low,
                "r_top": st.session_state.r_top, "r_mid": st.session_state.r_mid, "r_low": st.session_state.r_low
            }
            
            pos_labels = {
                "l_top": "左上段", "l_mid": "左中段", "l_low": "左下段",
                "r_top": "右上段", "r_mid": "右中段", "r_low": "右下段"
            }
            
            total_correct_count = 0
            
            for pos, correct_list in correct_data.items():
                user_ans_list = user_answers[pos]
                
                # その段の正解札の集合(set)と、ユーザーの回答札の集合の「積集合（共通部分）」を取り、その数を数える
                correct_set = set(correct_list)
                user_set = set(user_ans_list)
                
                # その段で正解した札の数
                num_correct_in_pos = len(correct_set.intersection(user_set))
                total_correct_count += num_correct_in_pos
                
                # ミスがある場合だけ、どの札が足りないか、または余計かを表示する（任意）
                if set(user_ans_list) != set(correct_list):
                    missing = correct_set - user_set
                    extra = user_set - correct_set
                    error_msg = f"⚠️ {pos_labels[pos]}: "
                    if missing:
                        error_msg += f"不足({', '.join(missing)}) "
                    if extra:
                        error_msg += f"間違い({', '.join(extra)})"
                    st.error(error_msg)

            st.metric("正解した札の数", f"{total_correct_count} / 25")
            
            if total_correct_count == 25:
                st.balloons()
                st.success("満点です！完璧に覚えていますね！")
            elif total_correct_count >= 20:
                st.info(f"あと少し（残り {25 - total_correct_count} 枚）！かなり覚えられています。")
            else:
                # 20枚未満の場合
                st.warning(f"現在は {total_correct_count} 枚正解です。暗記練習をもっと頑張りましょう！")
