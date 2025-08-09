#!/usr/bin/env python3
# Minimal KG visualizer: spring layout only, tiny CLI.
# Usage:
#   python utils/graph_visualization.py -i data/knowledge_graphs/mock_graph.json -o data/knowledge_graphs/mock_graph.png
#   (omit -o to show an interactive window)

import json, os, argparse
import networkx as nx
import matplotlib.pyplot as plt

TYPE_COLORS = {
    "event":   "#FFEEAD",
    "context": "#B5EAD7",
    "tool":    "#C7CEEA",
    "goal":    "#FFDAC1",
}
EDGE_STYLE = {
    "AND":     {"color": "#27ae60", "style": "solid",  "width": 2.0},
    "OR":      {"color": "#2980b9", "style": "solid",  "width": 2.0},
    "IMPLIES": {"color": "#7f8c8d", "style": "solid",  "width": 1.6},
    "NOT":     {"color": "#c0392b", "style": "dashed", "width": 2.4},
}

def load_graph_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_graph(data):
    G = nx.DiGraph()
    for n in data["nodes"]:
        G.add_node(n["id"], type=n.get("type",""), **(n.get("data", {}) or {}))
    for e in data["edges"]:
        G.add_edge(e["source"], e["target"], etype=e.get("type", "IMPLIES"))
    return G

def draw(G, with_labels=True, width=10, height=6, dpi=140):
    pos = nx.spring_layout(G, seed=42)
    # Nodes
    node_colors, node_sizes, outlines = [], [], []
    for nid, attrs in G.nodes(data=True):
        node_colors.append(TYPE_COLORS.get(attrs.get("type",""), "#E0E0E0"))
        conf = float(attrs.get("confidence", attrs.get("success_rate", 0.0)) or 0.0)
        conf = min(max(conf, 0.0), 1.0)
        node_sizes.append(600 + 1400 * conf)
        outlines.append("#111111" if attrs.get("visited", False) else "#333333")

    # Edges
    solid, dashed = [], []
    solid_colors, dashed_colors, solid_w, dashed_w = [], [], [], []
    edge_labels = {}
    for u, v, a in G.edges(data=True):
        et = a.get("etype", "IMPLIES")
        st = EDGE_STYLE.get(et, EDGE_STYLE["IMPLIES"])
        (solid if st["style"] == "solid" else dashed).append((u, v))
        (solid_colors if st["style"] == "solid" else dashed_colors).append(st["color"])
        (solid_w if st["style"] == "solid" else dashed_w).append(st["width"])
        edge_labels[(u, v)] = et

    plt.figure(figsize=(width, height), dpi=dpi)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes,
                           edgecolors=outlines, linewidths=1.4)
    if solid:
        nx.draw_networkx_edges(G, pos, edgelist=solid, edge_color=solid_colors, width=solid_w,
                               arrows=True, arrowstyle='-|>', arrowsize=14)
    if dashed:
        nx.draw_networkx_edges(G, pos, edgelist=dashed, edge_color=dashed_colors, width=dashed_w,
                               style="dashed", arrows=True, arrowstyle='-|>', arrowsize=14)

    if with_labels:
        nx.draw_networkx_labels(G, pos, font_size=9)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, label_pos=0.5)

    plt.axis("off")
    return plt

def main():
    ap = argparse.ArgumentParser(description="Minimal KG visualizer (spring layout).")
    ap.add_argument("-i", "--input", required=True, help="Path to graph JSON.")
    ap.add_argument("-o", "--out", help="Output image path (png/svg/pdf). If omitted, shows window.")
    ap.add_argument("--no-labels", action="store_true", help="Hide node/edge labels.")
    args = ap.parse_args()

    data = load_graph_json(args.input)
    G = build_graph(data)
    fig = draw(G, with_labels=not args.no_labels)

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        fig.tight_layout()
        fig.savefig(args.out, bbox_inches="tight")
        print(f"Wrote: {os.path.abspath(args.out)}")
        fig.close()
    else:
        plt.show()

if __name__ == "__main__":
    main()
