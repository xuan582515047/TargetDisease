"""轻量版靶点分析相关的 Pydantic 类型。"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class TargetAnalysisCreate(BaseModel):
    project_id: uuid.UUID
    question: str = Field(min_length=10, max_length=1000)
    mechanism_keywords: list[str] = Field(default_factory=list)


class DiseaseInfo(BaseModel):
    id: str
    source_id: str | None = None
    name_zh: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class CatalogOut(BaseModel):
    version: str
    diseases: list[DiseaseInfo]


class DiseaseSearchHit(BaseModel):
    id: str
    name: str
    description: str | None = None
    imported: bool = False


class DiseaseSearchOut(BaseModel):
    query: str
    translated_query: str | None = None
    diseases: list[DiseaseSearchHit]


class NetworkNodeOut(BaseModel):
    id: str
    type: str
    label: str
    gene_id: str | None = None
    n_score: float | None = None
    relevance_score: float | None = None


class NetworkEdgeOut(BaseModel):
    id: str
    source: str
    target: str
    type: str
    score: float
    source_id: str | None = None
    version: str | None = None


class NetworkOut(BaseModel):
    nodes: list[NetworkNodeOut]
    edges: list[NetworkEdgeOut]
    total_nodes: int
    total_edges: int
    display_nodes: int
    display_edges: int
    truncated: bool
    threshold: float
    min_score: float | None = None



