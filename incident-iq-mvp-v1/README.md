# Incident IQ MVP v1 (Streamlit + Azure AI Search + Azure OpenAI)

> 파이썬 3.11 / Streamlit 챗봇 UI / Azure AI Search(벡터+세만틱) / Azure OpenAI(RAG) / Bing Web Search(옵션)

## 1) 준비물
- Python 3.11
- Azure 구독
- Azure AI Search **Standard(S1) 이상** 권장 (벡터 + 세만틱 사용)
- Azure OpenAI (챗/임베딩 모델 배포)
- (옵션) Bing Web Search v7 리소스

## 2) 환경변수
Windows PowerShell 예시:
```powershell
$env:AZURE_SEARCH_ENDPOINT="https://<search-name>.search.windows.net"
$env:AZURE_SEARCH_API_KEY="<admin-key>"
$env:AZURE_SEARCH_INDEX="incident-runbooks"

$env:AZURE_OPENAI_ENDPOINT="https://<aoai-name>.openai.azure.com"
$env:AZURE_OPENAI_API_KEY="<api-key>"
$env:AZURE_OPENAI_DEPLOYMENT="<embedding-deployment>"     # e.g., text-embedding-3-large
$env:AZURE_OPENAI_CHAT_DEPLOYMENT="<chat-deployment>"     # e.g., gpt-4o-mini

# (옵션) 없으면 인터넷 보강검색 비활성
$env:BING_SEARCH_ENDPOINT="https://api.bing.microsoft.com/v7.0/search"
$env:BING_SEARCH_API_KEY="<bing-key>"
```

## 3) 설치 & 로컬 실행

python -m venv .venv
.venv\Scripts\Activate.ps1


```bash
pip install -r requirements.txt
python scripts/create_search_index.py
python scripts/upload_runbooks.py
streamlit run app/streamlit_app.py
```
로컬 URL: http://localhost:8501 (또는 8000)

## 4) Azure Portal로 리소스 생성
- Azure AI Search: **Standard S1 이상** SKU 선택, 키 발급 후 Endpoint/Key 확인
- Azure OpenAI: 리소스 생성 → 모델 배포(챗/임베딩) → Endpoint/Key/Deployment 명 확인
- (옵션) Bing Search v7: 키 발급

## 5) 스크립트로 리소스 배포
```powershell
pwsh scripts/deploy.ps1 -ResourceGroup rg-incident-iq -Location koreacentral -SearchName aisrch-incidentiq -AoaiName aoai-incidentiq -WebAppName web-incidentiq
```

## 6) Web App ZIP 배포 (VS Code/CLI)
```powershell
pwsh scripts/zip_deploy.ps1 -WebAppName web-incidentiq -ResourceGroup rg-incident-iq
```
초기 실행 URL 예시: `https://web-incidentiq.azurewebsites.net`

## 7) 데이터 (Runbook) 업로드
`data/runbooks/*.md` 파일을 수정/추가 후:
```bash
python scripts/upload_runbooks.py
```

## 8) UI 사용법
- 오류/이상징후 현상, 서비스명, 추가정보 입력 → **검색** 버튼 클릭
- 검색 결과가 없으면 인터넷 보강검색(옵션)이 자동으로 수행
- 우측 패널에서 즉시 발송 가능한 공지 포맷 예시를 확인

## 9) 버전/SDK
- azure-search-documents==11.6.0b12
- Streamlit 1.38+
- Python 3.11

## 10) 문제해결
- `PrioritizedFields` import 오류: SDK 베타 버전(11.6.x b12)과 일치하는지 확인
- 포트(8000) 관련: App Service 설정의 `WEBSITES_PORT=8000` 확인
- 모델 권한: Azure OpenAI의 네트워크/키/배포명 확인


## (NEW) .env 사용법
프로젝트 루트에 `.env` 파일을 만들고 아래 예시처럼 값들을 채우세요. (샘플: `.env.example` 제공)

```
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_API_KEY=...
AZURE_SEARCH_INDEX=incident-runbooks

AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini

# 선택
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search
BING_SEARCH_API_KEY=<bing-key>
```

`.env`는 다음 모듈/스크립트에서 자동으로 로드됩니다:
- `app/azure_clients.py` (Streamlit 앱 실행 시)
- `scripts/create_search_index.py`
- `scripts/upload_runbooks.py`

따라서 별도의 셸 환경변수 설정 없이도 실행이 가능합니다.
