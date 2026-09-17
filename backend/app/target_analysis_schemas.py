"""轻量版靶点分析相关的 Pydantic 类型。"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, model_validator


class TargetAnalysisCreate(BaseModel):
    project_id: uuid.UUID
    disease_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=10, max_length=1000)
    mechanism_keywords: list[str] = Field(default_factory=list)


class RerankRequest(BaseModel):
    w_a: float
    w_n: float

    @model_validator(mode="after")
    def _check_weights(self):
        if self.w_a < 0 or self.w_n < 0:
            raise ValueError("权重不能为负")
        if abs((self.w_a + self.w_n) - 1.0) > 1e-6:
            raise ValueError("权重之和必须为 1")
        return self


class DiseaseInfo(BaseModel):
    id: str
    source_id: str | None = None
    name_zh: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class CatalogOut(BaseModel):
    version: str
    diseases: list[DiseaseInfo]


class NetworkNodeOut(BaseModel):
    id: str
    type: str
    label: str
    gene_id: str | None = None
    a_score: float | None = None
    n_score: float | None = None
    fusion_score: float | None = None
    status: str | None = None


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



