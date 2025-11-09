import os, json
from typing import Dict, List

def get_lineage(model_dir: str, registry_root: str) -> List[str]:
    """
    Builds the lineage chain for a model by recursively reading its config.json.
    model_dir: path to the model's folder in the registry
    registry_root: root folder where all models are stored
    Returns list from oldest ancestor -> this model.
    """
    lineage = []
    visited = set()

    def trace(path):
        if path in visited: # keep track of visited locations
            return
        visited.add(path)
        cfg_path = os.path.join(registry_root, path, "config.json") # load model's config.json

        # look for no config (base/root model)
        if not os.path.exists(cfg_path):
            lineage.append(path)
            return
        with open(cfg_path) as f:
            cfg = json.load(f)
        parent = cfg.get("base_model_name_or_path")

        # append to lineage & recurse to parent
        lineage.append(path)
        if parent and os.path.isdir(os.path.join(registry_root, parent)):
            trace(parent)

    trace(model_dir)
    return lineage[::-1]   # ancestor -> descendant
