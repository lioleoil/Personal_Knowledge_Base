# Plan: README.md + CLAUDE.md 통합

## Context
README.md와 CLAUDE.md 모두 "저장소 목적"과 "폴더 구조" 섹션을 가지고 있어 중복 유지 비용이 발생한다.
CLAUDE.md는 Claude Code가 자동으로 읽는 운영 매뉴얼이고, README.md는 사람이 읽는 소개 문서인데,
이 저장소는 개인 로컬 저장소라 GitHub 전시 용도가 없으므로 분리 유지 필요성이 없다.
목표: CLAUDE.md에 모든 내용을 통합하고 README.md를 삭제한다.

## 중복 섹션 (현재 양쪽에 존재)
- 저장소 목적 설명
- 폴더 구조 (01_Identity ~ 04_WorkLog ~ .status)

## README.md 고유 내용 (CLAUDE.md에 추가할 것)
- 각 폴더 내 실제 파일명 상세 설명 (예: user_identity.md, your_curse_explained.md)
- 업데이트 이력 테이블

## CLAUDE.md 고유 내용 (그대로 유지)
- 자주 쓰는 명령
- 토큰 자동 추적 규칙
- 토큰 효율화 규칙
- 핵심 파일 목록
- 인터랙션 규칙
- 에이전트 실행 기록 관리
- 서브에이전트 표준 지시문 템플릿

## 통합 후 CLAUDE.md 섹션 순서
1. 저장소 목적
2. 폴더 구조 및 역할 (README의 파일 상세 내용 포함하여 강화)
3. 핵심 파일
4. 자주 쓰는 명령
5. 토큰 자동 추적 (Claude 필수 규칙)
6. 토큰 효율화 필수 규칙
7. 인터랙션 규칙
8. 에이전트 실행 기록 관리
9. 서브에이전트 표준 지시문 템플릿
10. 업데이트 이력 (README에서 이전)

## 변경 파일
- `CLAUDE.md` — 위 구조로 전면 재작성 (Edit)
- `README.md` — 삭제

## 검증
- CLAUDE.md 내 모든 기존 섹션이 누락 없이 포함됐는지 확인
- README.md 고유 내용(파일 상세, 업데이트 이력)이 CLAUDE.md에 반영됐는지 확인
- README.md 삭제 확인
