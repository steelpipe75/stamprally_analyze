import streamlit as st
import pandas as pd
from src.stamprally_analyze import build_graph, draw_graph
import datetime

def main():
    # ページ設定
    st.set_page_config(
        page_title="スタンプラリー分析支援アプリ",
        page_icon="💻",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("スタンプラリー分析支援アプリ")

    # 曜日マッピング
    weekdays_map = {
        "月曜日": 0, "火曜日": 1, "水曜日": 2, "木曜日": 3,
        "金曜日": 4, "土曜日": 5, "日曜日": 6
    }

    # サイドバーでファイルアップロードと時刻範囲選択UIを常に表示
    with st.sidebar:
        st.header("データ入力")
        uploaded_file = st.file_uploader("CSVファイルを選択してください", type=["csv"])

        # Check if a new file has been uploaded or the file has been cleared
        if 'last_uploaded_file_name' not in st.session_state:
            st.session_state.last_uploaded_file_name = None

        if uploaded_file is not None and st.session_state.last_uploaded_file_name != uploaded_file.name:
            st.session_state.pos = None
            st.session_state.last_uploaded_file_name = uploaded_file.name
        elif uploaded_file is None and st.session_state.last_uploaded_file_name is not None:
            # File was cleared
            st.session_state.pos = None
            st.session_state.last_uploaded_file_name = None

        time_range = st.slider(
            "分析対象時刻範囲",
            value=(datetime.time(0, 0, 0), datetime.time(23, 59, 59)),
            step=datetime.timedelta(minutes=1)
        )

        # 曜日選択UI
        selected_weekdays_names = st.multiselect(
            "分析対象曜日",
            options=list(weekdays_map.keys()),
            default=list(weekdays_map.keys()) # デフォルトは全選択
        )

    # time_rangeからstartとendの時刻を取得
    start_time = time_range[0]
    end_time = time_range[1]

    # 選択された曜日を数値に変換
    selected_weekdays_numbers = [weekdays_map[day] for day in selected_weekdays_names]

    # レイアウトの初期化と再計算ボタン
    if 'pos' not in st.session_state:
        st.session_state.pos = None

    # ファイルが選択されていない場合はメッセージを表示
    if uploaded_file is None:
        st.info("👈 サイドバーからCSVファイルを選択してください")
        return

    # ファイルが選択された場合の処理
    # CSVファイルの読み込み
    df = pd.read_csv(uploaded_file)

    # 必要な列の確認
    if "user_id" not in df.columns or "point" not in df.columns:
        st.error("CSVファイルに'user_id'または'point'列が存在しません。")
        return

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        st.error("CSVファイルに'timestamp'列が存在しません。")
        return

    # 時刻のみを取得する関数
    def get_time_only(dt):
        return dt.time()

    # 曜日を取得する関数
    def get_weekday_number(dt):
        return dt.weekday()

    # 選択された時刻範囲でデータをフィルタリング（日付は無視）
    time_filtered_df = df[df["timestamp"].apply(lambda x: start_time <= get_time_only(x) <= end_time)]
    
    # 選択された曜日でデータをフィルタリング
    if selected_weekdays_numbers: # 選択された曜日がある場合のみフィルタリング
        filtered_df = time_filtered_df[time_filtered_df["timestamp"].apply(lambda x: get_weekday_number(x) in selected_weekdays_numbers)]
    else:
        filtered_df = time_filtered_df

    # フィルタ後にデータが空の場合はメッセージ表示して早期終了
    if filtered_df.empty:
        st.warning("選択した時刻範囲に該当するデータがありません。別の範囲を選択してください。")
        st.subheader("利用したデータ")
        st.write(filtered_df)
        st.session_state.pos = None
    else:
        # グラフの構築
        G, node_counts, point_to_id = build_graph(filtered_df)

        # グラフの描画
        st.subheader("人流グラフ")

        # 座標編集ウィジェットからの更新を st.session_state.pos に反映
        if st.session_state.get('pos'):
            for node_id in st.session_state.pos.keys():
                widget_key_x = f"pos_x_{node_id}"
                widget_key_y = f"pos_y_{node_id}"
                if widget_key_x in st.session_state and widget_key_y in st.session_state:
                    st.session_state.pos[node_id] = (
                        st.session_state[widget_key_x],
                        st.session_state[widget_key_y]
                    )

        graph_data = draw_graph(G, node_counts, point_to_id, pos=st.session_state.pos)
        st.session_state.pos = graph_data['pos']

        # 画像の表示
        st.image(graph_data['image'], use_container_width='auto')

        # ノード座標の編集UI
        with st.expander("ノード座標の編集"):
            if st.session_state.get('pos'):
                id_to_point = {v: k for k, v in point_to_id.items()}

                # ヘッダー
                col1, col2, col3 = st.columns([2, 3, 3])
                col1.write("**ポイント**")
                col2.write("**X座標**")
                col3.write("**Y座標**")

                for node_id, coords in sorted(st.session_state.pos.items()):
                    if node_id not in G.nodes:
                        continue
                    
                    node_name = id_to_point.get(node_id, f"ID: {node_id}")
                    
                    col1, col2, col3 = st.columns([2, 3, 3])
                    with col1:
                        st.write(node_name)
                    with col2:
                        st.number_input(
                            "X",
                            value=float(coords[0]),
                            key=f"pos_x_{node_id}",
                            step=0.01,
                            label_visibility="collapsed"
                        )
                    with col3:
                        st.number_input(
                            "Y",
                            value=float(coords[1]),
                            key=f"pos_y_{node_id}",
                            step=0.01,
                            label_visibility="collapsed"
                        )

        # データの表示
        st.subheader("人流データ")

        # 時刻範囲の表示
        st.write(f"分析対象時刻: {start_time.strftime('%H:%M:%S')} から {end_time.strftime('%H:%M:%S')}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総ユーザー数", filtered_df['user_id'].nunique())
        with col2:
            st.metric("総スタンプ数", len(filtered_df))
        with col3:
            st.metric("総移動数", G.number_of_edges())

        # ポイントごとの訪問者数
        st.subheader("ポイントごとの訪問者数")
        st.dataframe(graph_data['nodes_data'])

        # ポイント間の移動者数
        st.subheader("ポイント間の移動者数 (行:from. 列:to)")
        st.dataframe(graph_data['edges_matrix'])

        st.subheader("利用したデータ")
        st.dataframe(filtered_df)

        # --- ダウンロード機能: フィルタ済データと表示している人流データを1つのCSVにまとめてダウンロード ---
        def make_combined_csv(filtered_df, nodes_df, edges_df, analysis_time_str, total_users, total_stamps, total_moves):
            # nodes_df と edges_df は pandas.DataFrame と仮定
            parts = []

            # --- Analysis summary ---
            parts.append('# Analysis summary')
            # 保存しやすいように key,value 形式のCSVを作る
            summary_df = pd.DataFrame([
                ["analysis_time", analysis_time_str],
                ["total_users", total_users],
                ["total_stamps", total_stamps],
                ["total_moves", total_moves]
            ], columns=["metric", "value"])
            parts.append(summary_df.to_csv(index=False))

            # nodes data セクション
            parts.append('# Nodes (ポイントごとの訪問者数)')
            parts.append(nodes_df.to_csv(index=False))

            # edges matrix セクション
            parts.append('\n# Edges (ポイント間の移動者数 行:from 列:to)')
            # edges_df をそのままCSV化（indexを含める）
            parts.append(edges_df.to_csv())

            # 元データ（フィルタ済）セクション
            parts.append('\n# Filtered raw data (利用したデータ)')
            parts.append(filtered_df.to_csv(index=False))

            # 結合してバイト列に変換（Excelで開いて文字化けしないようにBOM付きUTF-8にする）
            csv_text = "\n".join(parts)
            return csv_text.encode('utf-8-sig')

        try:
            nodes_df = graph_data.get('nodes_data') if 'graph_data' in locals() else None
            edges_df = graph_data.get('edges_matrix') if 'graph_data' in locals() else None
            # 分析サマリ値を計算
            analysis_time_str = f"{start_time.strftime('%H:%M:%S')} から {end_time.strftime('%H:%M:%S')}"
            total_users = int(filtered_df['user_id'].nunique())
            total_stamps = int(len(filtered_df))
            total_moves = int(G.number_of_edges())

            if nodes_df is not None and edges_df is not None:
                csv_bytes = make_combined_csv(filtered_df, nodes_df, edges_df, analysis_time_str, total_users, total_stamps, total_moves)
                st.download_button(
                    label="CSVをダウンロード（人流データ＋利用データ）",
                    data=csv_bytes,
                    file_name="stamprally_combined.csv",
                    mime="text/csv"
                )
            else:
                # 万が一 graph_data が無い場合はダウンロードを出さない
                st.info("ダウンロード可能な人流データがまだ生成されていません。")
        except Exception as e:
            st.error(f"ダウンロード用CSV生成中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
