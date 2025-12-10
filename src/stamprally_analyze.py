import pandas as pd
import networkx as nx
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import matplotlib_fontja
from io import BytesIO
from streamlit_agraph import agraph, Node, Edge, Config

def build_graph(df):
    points = df["point"].unique()
    encoder = LabelEncoder()
    point_ids = encoder.fit_transform(points)
    point_to_id = dict(zip(points, point_ids))
    # id_to_point = dict(zip(point_ids, points))

    node_counts = df.groupby("point")["user_id"].nunique().to_dict()

    df_sorted = df.sort_values(["user_id", "timestamp"])
    edges = []
    for user, group in df_sorted.groupby("user_id"):
        pts = group["point"].tolist()
        for i in range(len(pts) - 1):
            edges.append((pts[i], pts[i + 1]))

    edges_df = pd.DataFrame(edges, columns=["from", "to"])
    edge_counts = edges_df.value_counts().reset_index(name="weight")

    G = nx.DiGraph()
    # どのノードもエッジが無くてもグラフに含める（単一ノードの場合に layout 等で失敗しないようにする）
    for p in points:
        G.add_node(p)
    for _, row in edge_counts.iterrows():
        G.add_edge(row["from"], row["to"], weight=row["weight"])

    return G, node_counts, point_to_id

def draw_graph(G, node_counts, point_to_id, pos=None):
    # ノードラベルの準備
    node_labels = {n: f"{n}\n{node_counts.get(n, 0)} 人" for n in G.nodes()}
    def node_number(node):
        return point_to_id.get(node, 0)

    # エッジの分類（順方向・逆方向）
    forward_edges, backward_edges = [], []
    for u, v in G.edges():
        if node_number(u) < node_number(v):
            forward_edges.append((u, v))
        else:
            backward_edges.append((u, v))

    # グラフの描画
    plt.figure(figsize=(10, 7))
    if pos is None:
        pos = nx.spring_layout(G, seed=42)
    max_weight = max(nx.get_edge_attributes(G, "weight").values()) if G.edges() else 1

    max_node_count = max(node_counts.values()) if node_counts else 1
    node_sizes = [node_counts.get(n, 0) / max_node_count * 2000 + 500 for n in G.nodes()]

    widths_fwd = [G[u][v]["weight"] / max_weight * 5 + 1 for u, v in forward_edges]
    widths_bwd = [G[u][v]["weight"] / max_weight * 5 + 1 for u, v in backward_edges]

    nx.draw_networkx_edges(G, pos, edgelist=forward_edges, edge_color="b", width=widths_fwd, style="solid",
                             arrowstyle="->", arrowsize=20, connectionstyle="arc3,rad=0.15")
    nx.draw_networkx_edges(G, pos, edgelist=backward_edges, edge_color="g", width=widths_bwd, style="dashed",
                             arrowstyle="->", arrowsize=20, connectionstyle="arc3,rad=0.15")
    nx.draw_networkx_nodes(G, pos, node_color="skyblue", node_size=node_sizes, alpha=0.7)
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_family="IPAexGothic", font_size=10)

    def make_label_dict(G, edges):
        return {(u, v): f"{u}→{v}\n{G[u][v]['weight']} 人" for u, v in edges}

    forward_labels = make_label_dict(G, forward_edges)
    backward_labels = make_label_dict(G, backward_edges)

    label_objs_fwd = nx.draw_networkx_edge_labels(G, pos, edge_labels=forward_labels,
                                                   label_pos=0.3, font_color="b", font_family="IPAexGothic", rotate=False)
    label_objs_bwd = nx.draw_networkx_edge_labels(G, pos, edge_labels=backward_labels,
                                                   label_pos=0.3, font_color="g", font_family="IPAexGothic", rotate=False)

    for label_dict, bg_color, border_color, linestyle in [
        (label_objs_fwd, "white", "b", "solid"),
        (label_objs_bwd, "white", "g", "dashed"),
    ]:
        for t in label_dict.values():
            t.set_bbox(dict(facecolor=bg_color, edgecolor=border_color,
                            boxstyle="round,pad=0.3", lw=1, linestyle=linestyle))

    plt.axis("off")

    # 画像の保存
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close()
    buf.seek(0)

    # ノードの訪問者数データフレーム
    nodes_df = pd.DataFrame({
        'ポイント': list(G.nodes()),
        '訪問者数': [node_counts.get(n, 0) for n in G.nodes()]
    }).sort_values('訪問者数', ascending=False)

    nodes_list = list(G.nodes())
    if len(nodes_list) <= 1:
        edges_matrix = pd.DataFrame(0, index=nodes_list, columns=nodes_list)
        # index/columns の名前を削除してデフォルトに戻す
        edges_matrix.index.name = None
        edges_matrix.columns.name = None
    else:
        edges_data = []
        for u, v in G.edges():
            edges_data.append({
                'From': u,
                'To': v,
                '移動者数': G[u][v]['weight']
            })
        edges_df = pd.DataFrame(edges_data)

        # エッジの移動者数を二次元の表に変換
        edges_matrix = edges_df.pivot(index='From', columns='To', values='移動者数').fillna(0)

        # すべてのノードを行列に含める（ノードが一つだけでも空の行/列があるとエラーになるのを防ぐ）
        nodes_list = list(G.nodes())
        if len(nodes_list) > 0:
            edges_matrix = edges_matrix.reindex(index=nodes_list, columns=nodes_list, fill_value=0)
            # index/columns の名前を削除してデフォルトに戻す
            edges_matrix.index.name = None
            edges_matrix.columns.name = None

    return {
        'image': buf,
        'nodes_data': nodes_df,
        'edges_matrix': edges_matrix,
        'pos': pos
    }

def draw_agraph(G, node_counts, point_to_id):
    nodes = []
    if not list(G.nodes()):
        return None

    # ノード訪問者数の正規化（サイズに反映）
    node_counts_values = [node_counts.get(n, 0) for n in G.nodes()]
    max_node_count = max(node_counts_values) if node_counts_values else 1
    min_node_count = min(node_counts_values) if node_counts_values else 0

    def scale_node_size(count):
        if max_node_count == min_node_count:
            return 20
        # 15から35の範囲にスケーリング
        return 15 + (count - min_node_count) / (max_node_count - min_node_count) * 20

    for node_name in G.nodes():
        count = node_counts.get(node_name, 0)
        nodes.append(Node(id=node_name,
                        label=f"{node_name}\n{count}人",
                        size=scale_node_size(count),
                        # font={{'size': 14}
                        ))

    edges = []
    if list(G.edges()):
        # エッジの重みの正規化（太さに反映）
        weights = [data['weight'] for _, _, data in G.edges(data=True)]
        max_weight = max(weights) if weights else 1
        min_weight = min(weights) if weights else 1

        def scale_edge_width(weight):
            if max_weight == min_weight:
                return 2
            # 1から8の範囲にスケーリング
            return 1 + (weight - min_weight) / (max_weight - min_weight) * 7
        
        def node_number(node):
            return point_to_id.get(node, 0)

        for u, v, data in G.edges(data=True):
            weight = data.get('weight', 1)
            
            edge_kwargs = {
                'label': str(weight),
                'width': scale_edge_width(weight),
                'smooth': {'enabled': True, 'roundness': 0.15}
            }

            # 順方向と逆方向でエッジの曲げ方と色を変更
            if node_number(u) < node_number(v):
                # 順方向
                edge_kwargs['smooth']['type'] = 'curvedCW'
                edge_kwargs['color'] = {'color': 'blue'}
            else:
                # 逆方向
                edge_kwargs['smooth']['type'] = 'curvedCCW'
                edge_kwargs['color'] = {'color': 'green'}
            
            edges.append(Edge(source=u,
                            target=v,
                            **edge_kwargs
                            ))

    config = Config(width=800,
                    height=700,
                    directed=True,
                    physics=True,
                    nodeHighlightBehavior=True,
                    collapsible=False,
                    node={'labelProperty': 'label'},
                    link={'renderLabel': True, 'labelProperty': 'label', 'font': {'size': 12, 'color': 'black'}}
                   )

    return agraph(nodes=nodes, edges=edges, config=config)
