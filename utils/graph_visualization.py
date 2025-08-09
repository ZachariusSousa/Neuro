import argparse, json, math, sys, os

# Optional deps; we fall back gracefully
try:
    import networkx as nx  # type: ignore
except Exception:
    nx = None

try:
    from networkx.drawing.nx_agraph import graphviz_layout  # type: ignore
    _HAS_GRAPHVIZ = True
except Exception:
    _HAS_GRAPHVIZ = False

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None


TYPE_COLORS = {
    "event": "#FFEEAD",
    "context": "#B5EAD7",
    "tool": "#C7CEEA",
    "goal": "#FFDAC1",
}

EDGE_STYLE = {
    "AND":  {"color": "#27ae60", "style": "solid",  "width": 2.2},
    "OR":   {"color": "#2980b9", "style": "solid",  "width": 2.2},
    "IMPLIES": {"color": "#7f8c8d", "style": "solid", "width": 1.6},
    "NOT":  {"color": "#c0392b", "style": "dashed", "width": 2.8},
}

def load_json_graph(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Validate minimal shape
    if "nodes" not in data or "edges" not in data:
        raise ValueError("JSON missing 'nodes' or 'edges' keys; expected output of KnowledgeGraph.save_to_json")
    return data

def build_nx(data):
    if nx is None:
        raise RuntimeError("This script requires networkx. Try: pip install networkx matplotlib pygraphviz")
    G = nx.DiGraph()
    for n in data["nodes"]:
        # id, type, data
        nid = n["id"]
        ntype = n.get("type", "")
        meta = n.get("data", {}) or {}
        G.add_node(nid, type=ntype, **meta)
    for e in data["edges"]:
        G.add_edge(e["source"], e["target"], etype=e.get("type", "IMPLIES"))
    return G

def compute_layout(G, layout, seed=42):
    if layout == "graphviz" and _HAS_GRAPHVIZ:
        pos = graphviz_layout(G, prog="dot")
        # swap to approximate LR
        return {k: (v[1], -v[0]) for k, v in pos.items()}
    # spring fallback
    k = 1 / math.sqrt(max(1, len(G)))
    return nx.spring_layout(G, seed=seed, k=k)

def draw_graph(G, pos, with_labels=True, figsize=(10,6), dpi=140):
    if plt is None:
        raise RuntimeError("This script requires matplotlib. Try: pip install matplotlib")

    # Nodes
    node_colors, node_sizes, outlines = [], [], []
    for n, attrs in G.nodes(data=True):
        ntype = attrs.get("type", "")
        node_colors.append(TYPE_COLORS.get(ntype, "#E0E0E0"))
        conf = float(attrs.get("confidence", attrs.get("success_rate", 0.0)) or 0.0)
        conf = max(0.0, min(1.0, conf))
        node_sizes.append(600 + 1400 * conf)
        outlines.append("#111111" if attrs.get("visited", False) else "#333333")

    # Edges
    edge_solid, edge_dashed = [], []
    edge_colors_solid, edge_colors_dashed = [], []
    edge_widths_solid, edge_widths_dashed = [], []
    edge_labels = {}
    for u, v, a in G.edges(data=True):
        et = a.get("etype", "IMPLIES")
        style = EDGE_STYLE.get(et, EDGE_STYLE["IMPLIES"])
        (edge_solid if style["style"] == "solid" else edge_dashed).append((u, v))
        (edge_colors_solid if style["style"] == "solid" else edge_colors_dashed).append(style["color"])
        (edge_widths_solid if style["style"] == "solid" else edge_widths_dashed).append(style["width"])
        edge_labels[(u, v)] = et

    plt.figure(figsize=figsize, dpi=dpi)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes,
                           edgecolors=outlines, linewidths=1.6)

    if edge_solid:
        nx.draw_networkx_edges(
            G, pos, edgelist=edge_solid, edge_color=edge_colors_solid, width=edge_widths_solid,
            arrows=True, arrowstyle='-|>', arrowsize=16, connectionstyle="arc3,rad=0.05"
        )
    if edge_dashed:
        nx.draw_networkx_edges(
            G, pos, edgelist=edge_dashed, edge_color=edge_colors_dashed, width=edge_widths_dashed,
            style="dashed", arrows=True, arrowstyle='-|>', arrowsize=16, connectionstyle="arc3,rad=0.05"
        )

    if with_labels:
        nx.draw_networkx_labels(G, pos, font_size=9)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, label_pos=0.5)

    # Legend (simple)
    import matplotlib.patches as mpatches
    from matplotlib.lines import Line2D
    node_legend = [mpatches.Patch(facecolor=c, edgecolor="#333333", label=t) for t, c in TYPE_COLORS.items()]
    edge_legend = [
        Line2D([0], [0], color=EDGE_STYLE["AND"]["color"], lw=2.2, label="AND"),
        Line2D([0], [0], color=EDGE_STYLE["OR"]["color"], lw=2.2, label="OR"),
        Line2D([0], [0], color=EDGE_STYLE["IMPLIES"]["color"], lw=1.6, label="IMPLIES"),
        Line2D([0], [0], color=EDGE_STYLE["NOT"]["color"], lw=2.8, linestyle="--", label="NOT"),
    ]
    leg1 = plt.legend(handles=node_legend, title="Node type", loc="upper left", bbox_to_anchor=(1.01, 1.0))
    plt.gca().add_artist(leg1)
    plt.legend(handles=edge_legend, title="Edge type", loc="upper left", bbox_to_anchor=(1.01, 0.6))

    plt.axis("off")
    return plt

def export_dot(data, path):
    def esc(s: str) -> str:
        return s.replace('"', r'\"')
    lines = ['digraph KG {', '  rankdir=LR;']
    for n in data["nodes"]:
        nid = n["id"]; ntype = n.get("type",""); meta = n.get("data", {}) or {}
        visited = meta.get("visited", False)
        base = TYPE_COLORS.get(ntype, "#E0E0E0")
        outline = "#111111" if visited else "#333333"
        conf = float(meta.get("confidence", meta.get("success_rate", 0.0)) or 0.0)
        conf = max(0.0, min(1.0, conf))
        penwidth = 1 + 2 * conf
        label = f"{nid}\\n({ntype})" if ntype else f"{nid}"
        lines.append(
            f'  "{esc(nid)}" [label="{esc(label)}", fillcolor="{base}", color="{outline}", style="filled", penwidth={penwidth}];'
        )
    for e in data["edges"]:
        et = e.get("type", "IMPLIES")
        style = EDGE_STYLE.get(et, EDGE_STYLE["IMPLIES"])
        lines.append(
            f'  "{esc(e["source"])}" -> "{esc(e["target"])}" [label="{et}", color="{style["color"]}", style="{style["style"]}", penwidth={style["width"]}];'
        )
    lines.append('}')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    ap = argparse.ArgumentParser(description="Visualize a KnowledgeGraph JSON file.")
    ap.add_argument("--input", "-i", required=True, help="Path to graph.json produced by KnowledgeGraph.save_to_json")
    ap.add_argument("--out", "-o", help="Image path to save (png/svg/pdf). If omitted, just shows window.")
    ap.add_argument("--dot", help="Also export Graphviz DOT to this path.")
    ap.add_argument("--layout", choices=["graphviz","spring"], default="graphviz",
                    help="Layout engine (graphviz uses pygraphviz if available; falls back to spring).")
    ap.add_argument("--no-labels", action="store_true", help="Hide node/edge labels.")
    ap.add_argument("--dpi", type=int, default=140, help="Figure DPI.")
    ap.add_argument("--width", type=float, default=10.0, help="Figure width inches.")
    ap.add_argument("--height", type=float, default=6.0, help="Figure height inches.")
    ap.add_argument("--seed", type=int, default=42, help="Seed for spring layout.")
    args = ap.parse_args()

    data = load_json_graph(args.input)

    if args.dot:
        export_dot(data, args.dot)
        print(f"Wrote DOT: {args.dot}")

    G = build_nx(data)
    pos = compute_layout(G, args.layout, seed=args.seed)
    pltobj = draw_graph(G, pos, with_labels=not args.no_labels,
                        figsize=(args.width, args.height), dpi=args.dpi)

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        pltobj.tight_layout()
        pltobj.savefig(args.out, bbox_inches="tight")
        print(f"Wrote image: {args.out}")
        pltobj.close()
    else:
        pltobj.show()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[visualize_kg] ERROR: {e}", file=sys.stderr)
        sys.exit(1)