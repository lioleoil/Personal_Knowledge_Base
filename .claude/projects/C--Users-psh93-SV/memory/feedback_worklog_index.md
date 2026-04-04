---
name: WorkLog INDEX 자동 갱신 규칙
description: 04_WorkLog에 새 파일 저장 후 INDEX.md를 항상 갱신해야 함
type: feedback
---

`C:\Users\psh93\OneDrive\Desktop\Claude\04_WorkLog\` 하위에 새 파일을 저장할 때마다 INDEX.md를 갱신한다.

**Why:** 사용자가 INDEX.md를 통해 전체 파일 현황을 한눈에 파악하길 원함. 파일이 추가됐는데 INDEX가 안 맞으면 참조 신뢰도가 떨어짐.

**How to apply:** 04_WorkLog/ 하위 폴더에 마크다운 파일을 새로 저장한 직후, 아래 명령을 실행해서 INDEX.md를 갱신한다.

```bash
cd "C:/Users/psh93/OneDrive/Desktop/Claude/04_WorkLog" && python3 update_index.py
```

갱신 스크립트 위치: `C:\Users\psh93\OneDrive\Desktop\Claude\04_WorkLog\update_index.py`
