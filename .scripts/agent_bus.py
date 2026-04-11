"""
Agent Bus — 에이전트 간 통신 유틸리티
Task Manifest / Result / Validation / Advice / Report JSON 파일 R/W

버스 파일 위치: PROJECT_ROOT/.agents/bus/
  <task_id>_manifest.json    Execution → Domain
  <task_id>_result.json      Domain → Execution
  <task_id>_validation.json  Validation Agent 판정
  <task_id>_advice.json      Advisor Agent 솔루션
  <task_id>_report.json      Reporter Agent 최종 요약

사용 예:
  from agent_bus import AgentBus, BusFile
  bus = AgentBus(task_id="abc123")
  bus.write_manifest(domain="nova_log_analytics", instructions="이상탐지 실행", ...)
  manifest = bus.read(BusFile.MANIFEST)
  bus.write_validation(verdict="FAIL", issues=[...])
"""
import json, os, uuid
from datetime import datetime
from enum import Enum

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
)
BUS_DIR = os.path.join(PROJECT_ROOT, '.agents', 'bus')


class BusFile(str, Enum):
    MANIFEST   = 'manifest'
    RESULT     = 'result'
    VALIDATION = 'validation'
    ADVICE     = 'advice'
    REPORT     = 'report'


class AgentBus:
    """단일 task_id 기준으로 버스 파일을 읽고 쓰는 유틸리티."""

    def __init__(self, task_id: str | None = None):
        os.makedirs(BUS_DIR, exist_ok=True)
        self.task_id = task_id or str(uuid.uuid4())[:8]

    # ── 내부 헬퍼 ────────────────────────────────────────────────

    def _path(self, file_type: BusFile) -> str:
        return os.path.join(BUS_DIR, f'{self.task_id}_{file_type.value}.json')

    def _write(self, file_type: BusFile, payload: dict) -> str:
        payload['_task_id']   = self.task_id
        payload['_file_type'] = file_type.value
        payload['_written_at'] = datetime.now().isoformat(timespec='seconds')
        path = self._path(file_type)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def read(self, file_type: BusFile) -> dict | None:
        path = self._path(file_type)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ── Manifest (Execution → Domain) ────────────────────────────

    def write_manifest(
        self,
        domain: str,
        instructions: str,
        context_files: list[str] | None = None,
        expected_outputs: list[str] | None = None,
        deadline_hint: str = '10min',
        retry_count: int = 0,
        parent_agent: str = 'execution',
    ) -> str:
        return self._write(BusFile.MANIFEST, {
            'task_id':          self.task_id,
            'created_at':       datetime.now().isoformat(timespec='seconds'),
            'parent_agent':     parent_agent,
            'domain':           domain,
            'instructions':     instructions,
            'context_files':    context_files or [],
            'expected_outputs': expected_outputs or [],
            'deadline_hint':    deadline_hint,
            'retry_count':      retry_count,
        })

    # ── Result (Domain → Execution) ──────────────────────────────

    def write_result(
        self,
        domain: str,
        status: str,           # 'success' | 'partial' | 'error'
        outputs: list[dict],   # [{'type': '...', 'path': '...', 'summary': '...'}]
        errors: list[str] | None = None,
        metadata: dict | None = None,
    ) -> str:
        return self._write(BusFile.RESULT, {
            'domain':   domain,
            'status':   status,
            'outputs':  outputs,
            'errors':   errors or [],
            'metadata': metadata or {},
        })

    # ── Validation (Validation Agent → Bus) ──────────────────────

    def write_validation(
        self,
        verdict: str,          # 'PASS' | 'FAIL' | 'INSUFFICIENT'
        issues: list[dict] | None = None,
        passed_checks: list[str] | None = None,
        advisor_needed: bool = False,
    ) -> str:
        return self._write(BusFile.VALIDATION, {
            'verdict':        verdict,
            'issues':         issues or [],
            'passed_checks':  passed_checks or [],
            'advisor_needed': advisor_needed,
        })

    # ── Advice (Advisor Agent → Bus) ─────────────────────────────

    def write_advice(
        self,
        root_cause: str,
        solutions: list[dict],  # [{'priority': 1, 'action': '...', 'target_agent': '...'}]
        escalate_to_user: bool = False,
    ) -> str:
        return self._write(BusFile.ADVICE, {
            'root_cause':       root_cause,
            'solutions':        solutions,
            'escalate_to_user': escalate_to_user,
        })

    # ── Report (Reporter → Bus) ───────────────────────────────────

    def write_report(
        self,
        summary: str,
        sections: list[dict],   # [{'title': '...', 'content': '...'}]
        artifacts: list[str] | None = None,
        report_path: str | None = None,
    ) -> str:
        return self._write(BusFile.REPORT, {
            'summary':     summary,
            'sections':    sections,
            'artifacts':   artifacts or [],
            'report_path': report_path,
        })

    # ── 조회 헬퍼 ─────────────────────────────────────────────────

    @classmethod
    def list_tasks(cls) -> list[dict]:
        """bus/ 디렉터리의 모든 task_id와 파일 현황을 반환."""
        if not os.path.exists(BUS_DIR):
            return []
        tasks: dict[str, dict] = {}
        for fname in os.listdir(BUS_DIR):
            if not fname.endswith('.json'):
                continue
            parts = fname[:-5].split('_', 1)
            if len(parts) != 2:
                continue
            tid, ftype = parts
            if tid not in tasks:
                tasks[tid] = {'task_id': tid, 'files': []}
            tasks[tid]['files'].append(ftype)
        return sorted(tasks.values(), key=lambda t: t['task_id'])

    @classmethod
    def get_task_status(cls, task_id: str) -> dict:
        """주어진 task_id의 현재 상태를 요약 반환."""
        bus = cls(task_id)
        manifest   = bus.read(BusFile.MANIFEST)
        result     = bus.read(BusFile.RESULT)
        validation = bus.read(BusFile.VALIDATION)
        advice     = bus.read(BusFile.ADVICE)
        report     = bus.read(BusFile.REPORT)
        return {
            'task_id':    task_id,
            'domain':     manifest.get('domain', '?') if manifest else '?',
            'has_result': result is not None,
            'verdict':    validation.get('verdict') if validation else None,
            'has_advice': advice is not None,
            'reported':   report is not None,
        }
