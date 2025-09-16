from datetime import datetime

def fmt_time(dt: datetime) -> str:
    return dt.strftime("%m/%d %H:%M")

def incident_suspected(service_name: str, symptom: str, event_time: datetime) -> str:
    return f"""[이상징후 발생 공지]
1. 서비스명 : {service_name}
- 발생시간 : {fmt_time(event_time)}
2. 영향도 : 영향도 확인중
3. 현상 : {symptom}
4. 공지사항 : {symptom} 이벤트 발생하여 운영부서 확인 중입니다.
5. 문의처 : 통합관제센터
"""

def incident_resolved(service_name: str, symptom: str, impact: str, event_time: datetime, resolved_time: datetime, action: str) -> str:
    return f"""[이상징후 해소 공지]
1. 서비스명 : {service_name}
- 발생시간 : {fmt_time(event_time)}
- 해소시간 : {fmt_time(resolved_time)}
2. 영향도 : {impact}
3. 현상 : {symptom}
4. 공지사항 : {symptom} 이벤트 발생하였으나 운영부서에서 {action} 하여 정상화 되었습니다.
5. 문의처 : 통합관제센터
"""

def outage_declared(service_name: str, symptom: str, impact: str, declare_time: datetime) -> str:
    return f"""[장애 발생 공지]
1. 서비스명 : {service_name}
- 장애발생시간 : {fmt_time(declare_time)}
2. 영향도 : {impact}
3. 장애현상 : {symptom}
4. 공지사항 : 해당 이슈는 장애로 판단되어 비상대응을 진행합니다.
5. 문의처 : 통합관제센터
"""

def outage_cleared(service_name: str, symptom: str, impact: str, start_time: datetime, end_time: datetime, root_cause: str, actions: str) -> str:
    return f"""[장애 종료 공지]
1. 서비스명 : {service_name}
- 장애발생시간 : {fmt_time(start_time)}
- 장애종료시간 : {fmt_time(end_time)}
2. 영향도 : {impact}
3. 장애현상 : {symptom}
4. 원인 : {root_cause}
5. 조치내용 : {symptom} 이벤트 발생하였으나 운영부서에서 {actions} 하여 정상화 되었습니다.
6. 문의처 : 통합관제센터
"""
