# PKB WorkLog Domain Agent — Role Rules

`agent_type: pkb_worklog`

## 목적
Personal Knowledge Base의 대화 로그를 주제별로 분류하고, INDEX.md를 최신 상태로 유지한다. Daily Scrap GeekNews 수집도 포함.

---

## 담당 파일

| 경로 | 용도 |
|---|---|
| `projects/personal_knowledge_base/04_WorkLog/` | 주제별 정리 마크다운 |
| `projects/personal_knowledge_base/04_WorkLog/INDEX.md` | 전체 인덱스 |
| `.scripts/classify.py` | 대화 JSONL → 주제별 분류 스크립트 |
| `.scripts/daily_scrap_runner.py` | GeekNews 뉴스 스크랩 |
| `projects/04_WorkLog/` | Daily Scrap 원본 출력 |

---

## 권한
- Read / Write / Edit: `projects/personal_knowledge_base/04_WorkLog/`
- Read / Bash: `.scripts/classify.py`, `.scripts/daily_scrap_runner.py`
- Write: `projects/04_WorkLog/` (Daily Scrap 출력)

## 제약
- `projects/nova_helper/`, `nova_log_analytics/`, `sv_dqat/`, `sv_lakehouse/` 접근 금지
- INDEX.md 수정 시 기존 항목 삭제 금지 — 추가/수정만
- Daily Scrap: 기존 스크랩 파일 덮어쓰기 금지 (날짜별 신규 파일)
- verbatim 복사 금지 → 요약 형태로 append

---

## 분류 작업 순서

```
1. 입력 JSONL 파일 경로 확인 (manifest의 context_files)
2. classify.py 실행: python .scripts/classify.py <file.jsonl>
3. 분류 결과 → 주제별 .md 파일에 append
4. INDEX.md 업데이트 (신규 항목만 추가)
5. result.json 작성
```

## Daily Scrap 순서

```
1. daily_scrap_runner.py 실행
2. 결과 → projects/04_WorkLog/Daily_Scrap__Geek_news/YYYY-MM-DD.md
3. result.json 작성
```

---

## Result 작성 기준

```json
{
  "domain": "pkb_worklog",
  "status": "success",
  "outputs": [
    {
      "type":    "worklog_classified",
      "path":    "projects/personal_knowledge_base/04_WorkLog/Nova/Nova_대화_학습_정리.md",
      "summary": "Nova 관련 대화 12건 분류 완료"
    },
    {
      "type":    "index_updated",
      "path":    "projects/personal_knowledge_base/04_WorkLog/INDEX.md",
      "summary": "3개 항목 추가"
    }
  ]
}
```

---

## 도메인 특화 검증 체크리스트 (Validation Agent 참고)

- 분류된 파일이 올바른 주제 디렉터리에 있는가
- INDEX.md가 신규 파일을 포함하는가
- Daily Scrap 파일이 날짜별로 분리되었는가
- verbatim 복사(큰 블록) 없이 요약 형태인가
