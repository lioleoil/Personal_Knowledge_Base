---
name: 토큰 효율화 매뉴얼 자동 적용
description: 모든 작업에 03_Instructions/Claude_Code_효율화_매뉴얼.md의 규칙을 자동으로 적용할 것
type: feedback
---

모든 작업 시작 전에 `03_Instructions/Claude_Code_효율화_매뉴얼.md`의 규칙을 자동 적용한다.

**Why:** 에이전트 작업에서 토큰이 과다 소비됨 (Q1: 104k, Q3: 35k). 대용량 파일 전체 읽기, verbatim 복사, 권한 없는 서브에이전트 재실행이 주요 원인.

**How to apply:**
- 파일 읽기 전 항상 Grep으로 위치 먼저 파악 → offset+limit으로 타겟 Read
- 서브에이전트에 반드시 "Write/Edit 권한 필요" + "대용량 파일 Grep 우선" 지시
- 내용 복사는 verbatim 금지 → 핵심 요약 형태로 append
- 이미 존재하는 문서는 재생성하지 않고 참조
