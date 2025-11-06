import pandas as pd
import networkx as nx
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import matplotlib_fontja
from io import BytesIO

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

def draw_graph(G, node_counts, point_to_id):
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
    pos = nx.spring_layout(G, seed=42)

    nx.draw_networkx_edges(G, pos, edgelist=forward_edges, edge_color="b", width=1, style="solid",
                             arrowstyle="->", arrowsize=20, connectionstyle="arc3,rad=0.15")
    nx.draw_networkx_edges(G, pos, edgelist=backward_edges, edge_color="g", width=1, style="dashed",
                             arrowstyle="->", arrowsize=20, connectionstyle="arc3,rad=0.15")
    nx.draw_networkx_nodes(G, pos, node_color="skyblue")
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
        'edges_matrix': edges_matrix
    }
