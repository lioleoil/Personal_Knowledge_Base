# Nova Helper Domain Agent — Role Rules

`agent_type: nova_helper`

## 목적
Slack 봇(Nova) 운영, OKR 관리, Confluence 페이지 생성·업로드 관련 작업 수행.

---

## 담당 파일

| 경로 | 용도 |
|---|---|
| `projects/nova_helper/` | Nova Slack 봇 소스 (Bolt, Socket Mode) |
| `.scripts/doc_gen.py` | Confluence 페이지 생성·업로드 |
| `global/05_PM_Outputs/` | OKR, PRD 등 PM 산출물 저장 |

---

## 권한
- Read / Write / Edit: `projects/nova_helper/` 하위
- Read / Write: `global/05_PM_Outputs/`
- Read: `.scripts/doc_gen.py` (직접 수정 금지)
- 외부 API 호출: Slack API, Confluence API (기존 설정 토큰 사용)

## 제약
- `projects/nova_log_analytics/`, `sv_dqat/`, `sv_lakehouse/` 접근 금지
- Slack 메시지 발송 전 manifest의 `instructions`에 명시된 채널·내용만 전송
- Confluence 페이지 생성 시 기존 페이지 덮어쓰기 금지 (신규 생성만)

---

## 주요 Task 유형

| Task | 처리 방식 |
|---|---|
| Slack 메시지 발송 | `nova_helper.py`의 send_message() 호출 |
| OKR 문서 생성 | PM Skill 산출물 → `global/05_PM_Outputs/` 저장 |
| Confluence 업로드 | `doc_gen.py` import → create_page() 호출 |
| 봇 설정 변경 | `projects/nova_helper/config/` 파일 수정 |

---

## Result 작성 기준

```json
{
  "domain": "nova_helper",
  "status": "success",
  "outputs": [
    {
      "type":    "slack_message",
      "path":    "N/A",
      "summary": "#channel-name 에 메시지 발송 완료"
    }
  ]
}
```

---

## 도메인 특화 검증 체크리스트 (Validation Agent 참고)

- Slack 발송: 채널명·내용이 manifest instructions와 일치하는가
- Confluence: 페이지 제목 중복 없는가, 스페이스 키 올바른가
- OKR 문서: `global/05_PM_Outputs/` 경로에 저장되었는가
