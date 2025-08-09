#!/usr/bin/env python3
import json
import os

# Minimal mock graph data in the same format as KnowledgeGraph.save_to_json()
mock_graph = {
    "nodes": [
        {"id": "MineWood", "type": "event", "data": {"confidence": 0.9, "visited": True}},
        {"id": "MineIron", "type": "event", "data": {"confidence": 0.7}},
        {"id": "CraftPickaxe", "type": "tool", "data": {"confidence": 0.6}},
        {"id": "MineDiamond", "type": "goal", "data": {"confidence": 0.8}},
        {"id": "HasIronPickaxe", "type": "context", "data": {}},
    ],
    "edges": [
        {"source": "MineWood", "target": "CraftPickaxe", "type": "AND"},
        {"source": "MineIron", "target": "CraftPickaxe", "type": "AND"},
        {"source": "CraftPickaxe", "target": "HasIronPickaxe", "type": "IMPLIES"},
        {"source": "HasIronPickaxe", "target": "MineDiamond", "type": "AND"},
    ]
}

def main():
    # Ensure target folder exists
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_graphs")
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, "mock_graph.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mock_graph, f, indent=2)

    print(f"Mock graph JSON written to: {os.path.abspath(out_path)}")

if __name__ == "__main__":
    main()
