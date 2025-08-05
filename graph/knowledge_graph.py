# graph/knowledge_graph.py

from enum import Enum
from typing import Dict, List, Set, Any
import json
import os

class EdgeType(Enum):
    AND = "AND"
    OR = "OR"
    IMPLIES = "IMPLIES"
    NOT = "NOT"


class Node:
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any] = None):
        self.id = node_id
        self.type = node_type  # e.g., 'event', 'context', 'tool', etc.
        self.data = data or {}  # Extra info (e.g., coordinates, model path)
        self.edges: List['Edge'] = []

    def add_edge(self, edge: 'Edge'):
        self.edges.append(edge)

    def __repr__(self):
        return f"Node({self.id}, type={self.type})"


class Edge:
    def __init__(self, source: Node, target: Node, edge_type: EdgeType):
        self.source = source
        self.target = target
        self.type = edge_type

    def __repr__(self):
        return f"{self.source.id} -[{self.type.value}]-> {self.target.id}"


class KnowledgeGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    def add_node(self, node_id: str, node_type: str, data: Dict[str, Any] = None):
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id, node_type, data)
        return self.nodes[node_id]

    def add_edge(self, source_id: str, target_id: str, edge_type: EdgeType):
        source = self.nodes[source_id]
        target = self.nodes[target_id]
        edge = Edge(source, target, edge_type)
        source.add_edge(edge)
        
    def update_node(self, node_id: str, node_type: str = None, data: Dict[str, Any] = None):
        node = self.get_node(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found")
        if node_type:
            node.type = node_type
        if data:
            node.data.update(data)
            
    def prune_node(self, node_id: str):
        # Remove node and all edges pointing to or from it
        if node_id not in self.nodes:
            return
        del_node = self.nodes[node_id]
        # Remove edges from other nodes pointing to this one
        for node in self.nodes.values():
            node.edges = [e for e in node.edges if e.target.id != node_id]
        # Remove the node itself
        del self.nodes[node_id]
        
    def prune_failed_nodes(self):
        to_remove = [node_id for node_id, node in self.nodes.items()
                    if node.data.get("failed") is True]
        for node_id in to_remove:
            self.prune_node(node_id)

    def get_node(self, node_id: str) -> Node:
        return self.nodes.get(node_id)

    def traverse_for_goal(self, goal_id: str) -> List[str]:
        """
        Resolves all required steps to achieve a goal.
        For AND/IMPLIES edges: traverse all sources.
        For OR edges: just follow one source (prioritize alphabetically for now).
        """
        path: List[str] = []
        visited: Set[str] = set()

        def dfs(node: Node):
            if node.id in visited:
                return
            visited.add(node.id)

            # Find incoming edges to this node
            incoming = []
            for other_node in self.nodes.values():
                for edge in other_node.edges:
                    if edge.target.id == node.id:
                        incoming.append((edge, other_node))

            # Group edges by type
            and_edges = [(e, n) for e, n in incoming if e.type in {EdgeType.AND, EdgeType.IMPLIES}]
            or_edges = [(e, n) for e, n in incoming if e.type == EdgeType.OR]
            not_edges = [(e, n) for e, n in incoming if e.type == EdgeType.NOT]

            # If any NOT source is visited, block this node
            for _, source_node in not_edges:
                if source_node.data.get("visited", False):
                    return 

            # Resolve all AND/IMPLIES dependencies
            for edge, source_node in and_edges:
                dfs(source_node)

            # Resolve only one OR dependency (e.g., pick first alphabetically for now)
            if or_edges:
                chosen = sorted(or_edges, key=lambda tup: tup[1].id)[0]
                dfs(chosen[1])

            path.append(node.id)

        goal_node = self.get_node(goal_id)
        if goal_node:
            dfs(goal_node)
        return path
    
    def save_to_json(self, filepath: str):
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        data = {
            "nodes": [
                {"id": node.id, "type": node.type, "data": node.data}
                for node in self.nodes.values()
            ],
            "edges": [
                {"source": edge.source.id, "target": edge.target.id, "type": edge.type.value}
                for node in self.nodes.values()
                for edge in node.edges
            ]
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_from_json(self, filepath: str):
        with open(filepath, "r") as f:
            data = json.load(f)

        self.nodes = {}  # clear current graph

        # Add all nodes first
        for node in data["nodes"]:
            self.add_node(node["id"], node["type"], node.get("data", {}))

        # Then add edges
        for edge in data["edges"]:
            self.add_edge(edge["source"], edge["target"], EdgeType(edge["type"]))

    def __repr__(self):
        return f"KnowledgeGraph({len(self.nodes)} nodes)"

