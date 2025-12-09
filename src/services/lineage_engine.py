# src/services/lineage_engine.py
from src.models.artifacts import ArtifactLineageGraph, ArtifactLineageNode, ArtifactLineageEdge


def compute_lineage_graph(artifact):
    """
    Minimal valid lineage graph: one node representing the artifact itself,
    no edges. Shape complies with the spec.
    """
    try:
        node = ArtifactLineageNode(
            artifact_id=artifact.metadata.id,
            name=artifact.metadata.name,
            source="config_json",
            metadata={},
        )
        graph = ArtifactLineageGraph(nodes=[node], edges=[])
        return graph
    except Exception:
        return None
