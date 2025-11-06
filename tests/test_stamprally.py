import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import pytest
import pandas as pd
from src.stamprally_analyze import build_graph
from io import BytesIO

def test_build_graph():
    # テスト用のデータフレームを作成
    data = {
        'user_id': [1, 1, 2, 2],
        'point': ['A', 'B', 'A', 'C'],
        'timestamp': pd.to_datetime(['2023-01-01 10:00', '2023-01-01 10:05', '2023-01-01 10:10', '2023-01-01 10:15'])
    }
    df = pd.DataFrame(data)

    # グラフを構築
    G, node_counts, point_to_id = build_graph(df)

    # ノードとエッジの数を確認
    assert len(G.nodes()) == 3  # A, B, Cの3つのノード
    assert len(G.edges()) == 2   # A->B, A->C 2つのエッジ

    # ノード訪問人数の確認
    assert node_counts['A'] == 2
    assert node_counts['B'] == 1
    assert node_counts['C'] == 1

    # 期待されるエッジ
    assert ('A', 'B') in G.edges()
    assert ('A', 'C') in G.edges()
    # ユニークな遷移先組み合わせは2つ
    assert len(G.edges()) == 2

    # エッジ重み A->B
    e_ab = G.get_edge_data('A', 'B') or {}
    w_ab = e_ab.get('weight')
    assert w_ab == 1

    # エッジ重み A->C
    e_ac = G.get_edge_data('A', 'C') or {}
    w_ac = e_ac.get('weight')
    assert w_ac == 1

def test_single_node_no_edges():
    # 単一ノードのみのデータ（エッジが生成されない）
    data = {
        'user_id': [1, 2, 3],
        'point': ['X', 'X', 'X'],
        'timestamp': pd.to_datetime(['2023-01-01 10:00', '2023-01-01 10:05', '2023-01-01 10:10'])
    }
    df = pd.DataFrame(data)

    G, node_counts, point_to_id = build_graph(df)

    # ノードは1つ存在し、エッジはない
    assert len(G.nodes()) == 1
    assert len(G.edges()) == 0
    assert node_counts.get('X') == 3

# pytestを実行するためのエントリーポイント
if __name__ == "__main__":
    pytest.main()
