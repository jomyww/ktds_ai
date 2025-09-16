from __future__ import annotations
import os, json, time, math, datetime
from typing import List, Dict, Any, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType, VectorizedQuery
from azure.search.documents import SearchClient
import httpx
from app.azure_clients import load_settings, search_client
from app.notice_templates import incident_suspected, incident_resolved, outage_declared, outage_cleared
from app.prompts import SYSTEM_PROMPT, USER_TEMPLATE


# Custom exception to signal AOAI content filter / Responsible AI policy blocks
class AOAIContentFilterError(RuntimeError):
    def __init__(self, body: dict):
        self.body = body
        msg = f"AOAI content filter: {body}"
        super().__init__(msg)

# ---------- Embeddings via Azure OpenAI ----------
async def aembed(texts: List[str], settings) -> List[List[float]]:
    base = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
    url = f"{base}/openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT}/embeddings?api-version=2023-05-15"
    headers = {"api-key": settings.AZURE_OPENAI_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json={"input": texts})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # surface response body for debugging
            body = None
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise RuntimeError(f"Embedding request failed: {resp.status_code} {body}") from e
        data = resp.json()
        return [d["embedding"] for d in data["data"]]

async def achat(messages: List[Dict[str, str]], settings) -> str:
    base = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
    url = f"{base}/openai/deployments/{settings.AZURE_OPENAI_CHAT_DEPLOYMENT}/chat/completions?api-version=2025-01-01-preview"
    headers = {"api-key": settings.AZURE_OPENAI_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json={"messages": messages, "temperature": 0.2})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # include response body to diagnose 400 errors
            body = None
            try:
                body = resp.json()
            except Exception:
                body = {'text': resp.text}
            # detect AOAI content-filter / ResponsibleAIPolicyViolation errors and raise a structured exception
            err = body.get('error') if isinstance(body, dict) else None
            if err and (err.get('code') == 'content_filter' or (err.get('innererror') and err['innererror'].get('code') == 'ResponsibleAIPolicyViolation')):
                raise AOAIContentFilterError(body) from e
            raise RuntimeError(f"Chat completions request failed: {resp.status_code} {body}") from e
        data = resp.json()
        return data["choices"][0]["message"]["content"]

# ---------- Bing Web Search (optional) ----------
async def bing_search(query: str, settings) -> List[Dict[str, str]]:
    if not (settings.BING_SEARCH_ENDPOINT and settings.BING_SEARCH_API_KEY):
        return []
    headers = {"Ocp-Apim-Subscription-Key": settings.BING_SEARCH_API_KEY}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(settings.BING_SEARCH_ENDPOINT, params={"q": query, "mkt": "ko-KR", "count": 5}, headers=headers)
        r.raise_for_status()
        j = r.json()
        results = []
        for v in j.get("webPages", {}).get("value", []):
            results.append({"name": v.get("name"), "url": v.get("url"), "snippet": v.get("snippet", "")})
        return results

# ---------- RAG Search ----------
async def rag_search(symptom: str, service: str, extra: str, settings) -> Tuple[List[dict], str]:
    sc: SearchClient = search_client(settings)
    # combine keyword + vector query
    try:
        # vectorize query
        qvec = await aembed([f"{symptom}\n{service}\n{extra}"], settings)
        vector_query = VectorizedQuery(vector=qvec[0], k_nearest_neighbors=8, fields="contentVector")
        # When using vector queries, do not request semantic captions/answers (these cannot be combined)
        use_vector = True
        if use_vector:
            results = sc.search(
                search_text=symptom,
                top=8,
                vector_queries=[vector_query],
                query_type=QueryType.SIMPLE,
                filter=None,
            )
        else:
            # semantic-only search (no vector) — use semantic parameters
            results = sc.search(
                search_text=symptom,
                top=8,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="default-semantic-config",
                query_caption=QueryCaptionType.EXTRACTIVE,
                query_answer=QueryAnswerType.EXTRACTIVE,
                filter=None,
            )
    except Exception:
        # fallback without vector
        results = sc.search(search_text=symptom, top=8, query_type=QueryType.SIMPLE)

    hits = []
    for doc in results:
        hits.append({
            "id": doc.get("id"),
            "service": doc.get("service"),
            "severity": doc.get("severity"),
            "title": doc.get("title"),
            "impact": doc.get("impact"),
            "actions": doc.get("actions"),
            "content": doc.get("content"),
            "score": doc["@search.score"]
        })
    reason = "azure_ai_search" if hits else "no_rag_hits"
    return hits, reason

# ---------- Orchestrator ----------
async def generate_incident_response(symptom: str, service: str, extra: str) -> Dict[str, Any]:
    settings = load_settings()
    hits, reason = await rag_search(symptom, service, extra, settings)

    web_refs = []
    context_chunks = []
    if not hits:
        # internet backup search
        web_refs = await bing_search(f"{service} {symptom} 대응 방안", settings)

    # Compose prompt
    context_text = ""
    for h in hits[:5]:
        context_text += f"\n### {h['title']} (sev:{h.get('severity','N/A')})\n{h['content']}\n대응:{h.get('actions','')}\n"    
    if web_refs:
        context_text += "\n[인터넷 참고자료]\n" + "\n".join([f"- {w['name']} ({w['url']})" for w in web_refs])

    user_text = USER_TEMPLATE.format(symptom=symptom, service=service, extra=extra)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n[검색컨텍스트]\n" + context_text},
        {"role": "user", "content": user_text},
    ]
    try:
        answer = await achat(messages, settings)
    except AOAIContentFilterError as afe:
        # The request was blocked by AOAI Responsible AI policy. Try a sanitized retry without context.
        try:
            sanitized_user = f"요약/간단 조치 안내를 작성해 주세요. 문제: {symptom} 서비스: {service}. 추가 정보는 생략합니다."
            sanitized_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": sanitized_user},
            ]
            answer = await achat(sanitized_messages, settings)
            # mark reason to indicate content-filter fallback
            reason = "aoai_content_filter_sanitized"
        except Exception:
            # still blocked or other error -> return a helpful message to the user
            answer = (
                "생성 실패: 요청이 콘텐츠 정책에 의해 차단되었습니다. 민감하거나 성적인 표현이 포함되어 있지 않은지 확인하고, "
                "문장을 간단하게 줄여 다시 시도해 주세요."
            )
            reason = "aoai_content_filter_blocked"
    except Exception as e:
        # bubble up other errors
        raise

    now = datetime.datetime.now()
    notices = {
        "suspected": incident_suspected(service, symptom, now),
        "resolved": incident_resolved(service, symptom, impact="영향도 확인중", event_time=now, resolved_time=now, action="조치"),
        "declared": outage_declared(service, symptom, impact="영향도 확인중", declare_time=now),
        "cleared": outage_cleared(service, symptom, impact="영향도 확인중", start_time=now, end_time=now, root_cause="원인분석중", actions="조치내역 정리")
    }
    return {"hits": hits, "reason": reason, "web_refs": web_refs, "answer": answer, "notices": notices}
