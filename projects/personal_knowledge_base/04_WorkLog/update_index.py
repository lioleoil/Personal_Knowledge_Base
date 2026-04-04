"""
04_WorkLog INDEX.md 자동 갱신 스크립트
새 마크다운 파일이 추가될 때마다 실행하면 INDEX.md를 최신 상태로 업데이트함
실행: python update_index.py
"""
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

FOLDER_DESC = {
    'Nova':               'Nova 대시보드, 사내 서비스 기획/릴리즈',
    'ODD':                'OpenODD, 운행설계영역',
    'OpenLABEL':          'ASAM OpenLABEL, SV→OpenLABEL 마이그레이션',
    'DQA':                '데이터 품질 분석, 라벨 검증',
    'Gen1_Gen2_Labeling': 'OD/RMD/3DP 라벨링 성능 측정, Policy',
    'Gen2_Policy':        'Sequence 기반 Gen2 Annotation Policy 수립·조항 작성·번역',
    'Career':             '이직, 커리어 전략, 이력서, 포트폴리오',
    'Python_Scripts':     'Python 스크립트, 자동화, 파일 처리',
    'Strategy_Business':  '전략 문서, KPI/OKR, 비즈니스 번역',
    'Misc':               '기타 (개인 관심사, 일회성 질문)',
}

lines = [
    "# WorkLog INDEX",
    "",
    f"> 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "",
    "---",
    "",
    "## 폴더별 파일 목록",
    "",
]

total_files = 0
for folder in sorted(FOLDER_DESC.keys()):
    folder_path = os.path.join(BASE, folder)
    if not os.path.isdir(folder_path):
        continue
    md_files = [f for f in os.listdir(folder_path)
                if f.endswith('.md') and f != 'update_index.py']
    if not md_files:
        continue
    desc = FOLDER_DESC.get(folder, '')
    lines.append(f"### {folder}/ — {desc}")
    lines.append("")
    for mf in sorted(md_files):
        mtime = os.path.getmtime(os.path.join(folder_path, mf))
        mdate = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        lines.append(f"- [{mf}]({folder}/{mf}) _(저장: {mdate})_")
        total_files += 1
    lines.append("")

lines += [
    "---",
    "",
    f"**총 파일 수: {total_files}개**",
    "",
    "> 새 파일 추가 후 `python update_index.py` 실행하면 이 파일이 자동 갱신됩니다.",
]

index_path = os.path.join(BASE, 'INDEX.md')
with open(index_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"INDEX.md 갱신 완료 ({total_files}개 파일)")
