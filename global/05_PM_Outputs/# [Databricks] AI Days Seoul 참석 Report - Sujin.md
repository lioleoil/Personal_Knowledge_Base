---
tags:
  - databricks
  - ai-days
  - seoul
  - data-analytics
  - odd
  - pm-output
aliases:
  - Databricks AI Days Seoul Sujin
category: PM-Output
project: Nova
related-synthesis: "[[Nova/SYNTHESIS|Nova 지식 합성]]"
updated: 2026-04-22
---

## 1. Executive Summary
본 보고서는 Data Analytics의 E2E 파이프라인과 ODD(Operational Design Domain) 자동화 관점을 통합하여, 데이터 기반 의사결정 구조를 **자율화·자동화·표준화**하는 방향성을 제시합니다.
핵심은 단순 데이터 활용을 넘어, **인과 기반 의사결정 루프와 자동화된 데이터셋 생성 구조를 결합**하여 플랫폼 환경에서 확장 가능한 분석 체계를 구축하는 것입니다.

## 2. E2E Pipeline 관점

### 2.1 데이터 민주화 (Data Democratization)
* 분석의 출발점은 데이터 접근성 확보입니다.
* **Tmap 사례**
  * Self-serving 분석 환경을 구축하였습니다.
  * 단순 데이터 추출 요청이 **68% 감소**하였습니다.
  * 전사 구성원의 **71%가 데이터에 접근**할 수 있게 되었습니다.  
→ 정량적 지표 기반으로 데이터 활용 수준을 관리하며,  
분석 조직의 병목을 제거하는 구조가 중요합니다.

### 2.2 인과관계 기반 파이프라인 (Causal Analytics Loop)
* 단순 상관관계 분석에서 벗어나 **“왜 발생했는가”**에 집중합니다.
* **Cafe24 사례 구조**
  1. 관찰 (Observation)
  2. 가설 설정 (Hypothesis)
  3. 검증 (Validation)
  4. 액션 실행 (Action)
  5. 피드백 수집 (Feedback)  
→ 이 과정을 하나의 **End-to-End Loop**로 설계하여  
분석 → 실행 → 학습이 반복되는 구조를 확보합니다.

## 3. ODD Automation 관점

### 3.1 ODD 데이터셋 자동화 구조
* **Databricks Apps 기반 구조를 활용합니다.**
  * 완전관리형 서버리스 환경을 제공합니다.
  * Git 기반 배포를 지원합니다.
  * Lakebase / AppKit 연동이 가능합니다.  
→ 이를 통해 **ODD 학습 데이터셋 구축 및 조건 조합 커스터마이징을 자동화할 수 있습니다.**  
→ ODD 생성 및 관리 기능을 애플리케이션 형태로 구현할 수 있습니다.

### 3.2 신뢰성 확보 구조 (LLM + Cross Validation)
* **KCD 사례 기반 패턴을 적용합니다.**
  * LLM을 활용하여 전처리를 자동화합니다.
  * 디테일 모델을 통해 결과를 검증합니다.
  * 교차검증을 통해 품질을 확보합니다.  
→ 자동화와 정확성을 동시에 확보하는 구조를 구현할 수 있습니다.  
→ 해당 방식은 ODD 생성 파이프라인에도 동일하게 적용 가능합니다.

### 3.3 AI Gateway 기반 운영 통제
* LLM 활용을 위한 운영 레이어를 통합 관리합니다.
  * 모델 라우팅을 수행합니다.
  * 비용을 추적합니다.
  * 가드레일을 관리합니다.  
→ 모델 변경 시에도 **애플리케이션 코드 수정 없이 전환이 가능합니다.**  
→ 운영 유연성과 비용 통제를 동시에 확보할 수 있습니다.

## 4. Supporting Tools & Infrastructure

### 4.1 개발 생산성
* SV 전용 MCP + Genie Code를 활용합니다.
  * 바이브 코딩 기반으로 파이프라인 개발 생산성을 향상시킵니다.
* AI Dev Kit + AI Gateway를 활용합니다.
  * 다양한 모델을 유연하게 사용할 수 있습니다.

### 4.2 데이터 인프라
* **Lakebase (Managed PostgreSQL)**를 활용합니다.
  * Zero-copy 브랜칭을 지원합니다.
  * 운영 환경에 영향을 주지 않고 개발 환경을 격리할 수 있습니다.
  * **서울 리전 Q2 배포가 예정되어 있습니다.**  
→ 실험, 개발, 운영 환경을 비용 부담 없이 분리할 수 있습니다.

## 5. Integrated Direction
* 데이터 민주화를 통해 접근성을 확보합니다.
* 인과 파이프라인을 통해 의사결정을 정교화합니다.
* ODD 자동화를 통해 데이터 생성 구조를 혁신합니다.
* AI Gateway를 통해 운영 통제 및 확장성을 확보합니다.  

→ 결과적으로, Data Analytics는  
**“분석 → 생성 → 검증 → 실행”이 하나의 플랫폼 내에서 순환되는 구조로 진화합니다.**  
→ 이는 단순 분석 기능을 넘어  
**데이터 기반 의사결정 시스템 자체를 제품화하는 방향으로 확장됩니다.**