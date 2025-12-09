from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, AnyUrl


# === Basic Artifact Types ===

class ArtifactType(str, Enum):
    model = "model"
    dataset = "dataset"
    code = "code"


class ArtifactID(str):
    """Alias type for artifact IDs."""
    # You can keep it as plain str; OpenAPI pattern is enforced via validation if you want.


class ArtifactMetadata(BaseModel):
    name: str
    id: str       # ArtifactID
    type: ArtifactType


class ArtifactData(BaseModel):
    url: AnyUrl
    download_url: Optional[AnyUrl] = None  # readOnly in spec


class Artifact(BaseModel):
    metadata: ArtifactMetadata
    data: ArtifactData


class ArtifactQuery(BaseModel):
    name: str
    types: Optional[List[ArtifactType]] = None


class ArtifactRegEx(BaseModel):
    regex: str


# === Rating ===

class SizeScore(BaseModel):
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float


class ModelRating(BaseModel):
    name: str
    category: str
    net_score: float
    net_score_latency: float
    ramp_up_time: float
    ramp_up_time_latency: float
    bus_factor: float
    bus_factor_latency: float
    performance_claims: float
    performance_claims_latency: float
    license: float
    license_latency: float
    dataset_and_code_score: float
    dataset_and_code_score_latency: float
    dataset_quality: float
    dataset_quality_latency: float
    code_quality: float
    code_quality_latency: float
    reproducibility: float
    reproducibility_latency: float
    reviewedness: float
    reviewedness_latency: float
    tree_score: float
    tree_score_latency: float
    size_score: SizeScore
    size_score_latency: float


# === Lineage ===

class ArtifactLineageNode(BaseModel):
    artifact_id: str
    name: str
    source: str
    metadata: Optional[Dict[str, Any]] = None


class ArtifactLineageEdge(BaseModel):
    from_node_artifact_id: str
    to_node_artifact_id: str
    relationship: str


class ArtifactLineageGraph(BaseModel):
    nodes: List[ArtifactLineageNode]
    edges: List[ArtifactLineageEdge]


# === Cost ===

class ArtifactCostEntry(BaseModel):
    standalone_cost: Optional[float] = None
    total_cost: float


ArtifactCost = Dict[str, ArtifactCostEntry]


# === License Check ===

class SimpleLicenseCheckRequest(BaseModel):
    github_url: AnyUrl


# === Auth & Tracks ===

class User(BaseModel):
    name: str
    is_admin: bool


class UserAuthenticationInfo(BaseModel):
    password: str


class AuthenticationRequest(BaseModel):
    user: User
    secret: UserAuthenticationInfo


# spec treats token as simple string
AuthenticationToken = str