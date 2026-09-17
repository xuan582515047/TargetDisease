"""Open Targets Platform GraphQL 客户端（仅疾病检索与元信息查询）。

用途：辅助用户从 Open Targets 发现疾病、查看其稳定 ID 与关联靶点数量，
用于「挑选要导入的疾病」。分析主流程仍读取本地快照，不依赖本模块。

接口文档：https://platform-docs.opentargets.org/data-access/graphql-api
"""
from __future__ import annotations

import httpx

ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"
TIMEOUT = 60.0

SEARCH_QUERY = """
query SearchDiseases($q: String!, $size: Int!) {
  search(queryString: $q, entityNames: ["disease"], page: {index: 0, size: $size}) {
    total
    hits {
      id
      entity
      name
      description
    }
  }
}
"""

COUNT_QUERY = """
query DiseaseTargetCount($diseaseId: String!) {
  disease(efoId: $diseaseId) {
    id
    name
    associatedTargets(page: {index: 0, size: 1}) {
      count
    }
  }
}
"""


class OpenTargetsError(Exception):
    """Open Targets 请求失败。"""


def _post(query: str, variables: dict) -> dict:
    try:
        resp = httpx.post(
            ENDPOINT,
            json={"query": query, "variables": variables},
            timeout=TIMEOUT,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        raise OpenTargetsError(f"Open Targets 网络错误：{exc}") from exc
    if resp.status_code != 200:
        raise OpenTargetsError(f"Open Targets 返回 {resp.status_code}")
    payload = resp.json()
    if "errors" in payload:
        raise OpenTargetsError(f"GraphQL 错误：{payload['errors']}")
    return payload.get("data") or {}


def search_diseases(query: str, size: int = 20) -> list[dict]:
    """按名称搜索疾病，返回 [{id, entity, name, description}]。"""
    data = _post(SEARCH_QUERY, {"q": query, "size": size}).get("search") or {}
    return data.get("hits") or []


def disease_target_count(disease_id: str) -> dict | None:
    """查询单个疾病的关联靶点数量，返回 {id, name, target_count}，失败返回 None。"""
    try:
        data = _post(COUNT_QUERY, {"diseaseId": disease_id}).get("disease")
    except OpenTargetsError:
        return None
    if not data:
        return None
    associated = data.get("associatedTargets") or {}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "target_count": associated.get("count"),
    }
