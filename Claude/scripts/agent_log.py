"""
에이전트 실행 기록 유틸리티
에이전트가 자신의 상태를 업데이트할 때 사용:

  import sys
  sys.path.insert(0, 'C:/Users/psh93/OneDrive/Desktop/Claude/scripts')
  from agent_log import AgentLog

  log = AgentLog(
      agent_id  = "대화재분류_2026-03-15",
      title     = "Python_Scripts 대화 재분류",
      folder    = "04_WorkLog/Python_Scripts",   # 프로젝트 루트 기준 상대경로
  )
  log.update(status='running', progress=30, message='파일 읽는 중')
  log.add('첫 번째 항목 처리 완료')
  log.done('완료 메시지')      # status=completed, progress=100
  log.error('오류 메시지')     # status=error
"""
import json, os
from datetime import datetime

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
)


class AgentLog:
    def __init__(self, agent_id: str, title: str, folder: str):
        """
        agent_id : 고유 식별자 (예: "Q1_대화재분류")
        title    : 표시용 제목
        folder   : 프로젝트 루트 기준 상대경로 (예: "04_WorkLog/Python_Scripts")
        """
        self.agent_id = agent_id
        self.title    = title
        self.folder   = folder

        agents_dir = os.path.join(PROJECT_ROOT, folder, '.agents')
        os.makedirs(agents_dir, exist_ok=True)

        date_str  = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        safe_id   = agent_id.replace(' ', '_').replace('/', '-')
        self._path = os.path.join(agents_dir, f'{date_str}_{safe_id}.json')

        self._data = {
            'agent_id':    agent_id,
            'title':       title,
            'folder':      folder,
            'started_at':  datetime.now().isoformat(timespec='seconds'),
            'completed_at': None,
            'status':      'running',
            'progress':    0,
            'message':     '시작',
            'log':         [],
        }
        self._save()

    def update(self, status: str = None, progress: int = None, message: str = None):
        if status   is not None: self._data['status']   = status
        if progress is not None: self._data['progress'] = progress
        if message  is not None: self._data['message']  = message
        self._save()

    def add(self, entry: str):
        """로그 항목 한 줄 추가."""
        ts = datetime.now().strftime('%H:%M:%S')
        self._data['log'].append(f'{ts}  {entry}')
        self._save()

    def done(self, message: str = '완료'):
        self._data.update({
            'status':       'completed',
            'progress':     100,
            'message':      message,
            'completed_at': datetime.now().isoformat(timespec='seconds'),
        })
        self._save()

    def error(self, message: str):
        self._data.update({
            'status':       'error',
            'message':      message,
            'completed_at': datetime.now().isoformat(timespec='seconds'),
        })
        self._save()

    def _save(self):
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @property
    def path(self) -> str:
        return self._path
