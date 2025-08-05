# tests/test_knowledge_graph.py

import pytest
from graph.knowledge_graph import KnowledgeGraph, EdgeType
import sys
import os
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_add_node_and_edge():
    kg = KnowledgeGraph()
    kg.add_node("mine_diamond", "event", {"model": "path/to/model.pt"})
    kg.add_node("has_iron_pickaxe", "tool")
    kg.add_edge("has_iron_pickaxe", "mine_diamond", EdgeType.IMPLIES)

    assert "mine_diamond" in kg.nodes
    assert "has_iron_pickaxe" in kg.nodes
    assert len(kg.get_node("has_iron_pickaxe").edges) == 1
    assert kg.get_node("has_iron_pickaxe").edges[0].target.id == "mine_diamond"

def test_traversal_order():
    kg = KnowledgeGraph()
    kg.add_node("wood", "event")
    kg.add_node("stick", "event")
    kg.add_node("pickaxe", "event")
    kg.add_edge("wood", "stick", EdgeType.IMPLIES)
    kg.add_edge("stick", "pickaxe", EdgeType.IMPLIES)

    path = kg.traverse_for_goal("pickaxe")
    assert path == ["wood", "stick", "pickaxe"]

def test_or_logic():
    kg = KnowledgeGraph()
    kg.add_node("coal", "item")
    kg.add_node("charcoal", "item")
    kg.add_node("torch", "event")

    kg.add_edge("coal", "torch", EdgeType.OR)
    kg.add_edge("charcoal", "torch", EdgeType.OR)

    path = kg.traverse_for_goal("torch")

    # Accept either coal or charcoal as valid
    assert path in [["coal", "torch"], ["charcoal", "torch"]]

def test_save_and_load():
    import os

    kg1 = KnowledgeGraph()
    kg1.add_node("iron", "item")
    kg1.add_node("pickaxe", "event")
    kg1.add_edge("iron", "pickaxe", EdgeType.IMPLIES)

    # Save to a permanent subfolder
    path = "data/knowledge_graphs/test_graph.json"
    kg1.save_to_json(path)

    kg2 = KnowledgeGraph()
    kg2.load_from_json(path)

    # Clean up
    os.remove(path)

    path_result = kg2.traverse_for_goal("pickaxe")
    assert path_result == ["iron", "pickaxe"]
    
def test_update_node():
    kg = KnowledgeGraph()
    kg.add_node("crafting_table", "tool", {"uses": 1})
    kg.update_node("crafting_table", data={"uses": 2, "crafted": True})

    node = kg.get_node("crafting_table")
    assert node.data["uses"] == 2
    assert node.data["crafted"] is True

def test_prune_node():
    kg = KnowledgeGraph()
    kg.add_node("useless", "event")
    kg.add_node("valuable", "event")
    kg.add_edge("valuable", "useless", EdgeType.IMPLIES)

    kg.prune_node("useless")
    assert "useless" not in kg.nodes
    assert len(kg.get_node("valuable").edges) == 0

def test_prune_failed_nodes():
    kg = KnowledgeGraph()
    kg.add_node("bad_skill", "event", {"failed": True})
    kg.add_node("good_skill", "event", {"failed": False})
    kg.prune_failed_nodes()

    assert "bad_skill" not in kg.nodes
    assert "good_skill" in kg.nodes

def test_not_logic_blocks_path():
    kg = KnowledgeGraph()
    kg.add_node("no_pickaxe", "state", {"visited": True})
    kg.add_node("mine", "event")
    kg.add_edge("no_pickaxe", "mine", EdgeType.NOT)

    path = kg.traverse_for_goal("mine")
    assert "mine" not in path  # mining blocked due to visited contradiction

def test_success_rate_update():
    kg = KnowledgeGraph()
    kg.add_node("build", "event", {"success_rate": 0.5})
    kg.update_node("build", data={"success_rate": 0.9, "visited": True})

    node = kg.get_node("build")
    assert node.data["success_rate"] == 0.9
    assert node.data["visited"] is True
