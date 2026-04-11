"""
permission_bus.py
권한 레지스트리(allowed_permissions.json) 기반 에이전트 권한 체크 유틸리티.

사용법:
    from permission_bus import PermissionBus
    pb = PermissionBus()
    if pb.is_auto_approved('file_write'):
        ...
    elif pb.requires_user_approval('file_delete'):
        pb.request_permission(task_id, 'file_delete', context='index.py 삭제')
"""
import json
import os
from datetime import datetime

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
)
REGISTRY_PATH = os.path.join(
    PROJECT_ROOT, 'global', '04_AgentEcosystem', 'allowed_permissions.json'
)
BUS_DIR = os.path.join(PROJECT_ROOT, '.agents', 'bus')


class PermissionBus:
    def __init__(self):
        self._registry = self.load_registry()

    def load_registry(self) -> dict:
        if not os.path.exists(REGISTRY_PATH):
            return {}
        with open(REGISTRY_PATH, encoding='utf-8') as f:
            return json.load(f)

    def is_auto_approved(self, perm_type: str) -> bool:
        """auto_approved 목록에 있고 granted=true이면 True."""
        entry = self._registry.get('auto_approved', {}).get(perm_type)
        return bool(entry and entry.get('granted', False))

    def requires_user_approval(self, perm_type: str) -> bool:
        """user_approval_required 목록에 있으면 True."""
        return perm_type in self._registry.get('user_approval_required', {})

    def request_permission(self, task_id: str, perm_type: str, context: str = '') -> str:
        """
        권한 요청 파일을 버스에 작성한다.
        반환: 요청 파일 경로
        """
        os.makedirs(BUS_DIR, exist_ok=True)
        path = os.path.join(BUS_DIR, f'{task_id}_permission_request.json')
        payload = {
            'task_id':   task_id,
            'perm_type': perm_type,
            'context':   context,
            'status':    'pending',
            'requested_at': datetime.now().isoformat(),
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def grant_permission(self, task_id: str, perm_type: str) -> str:
        """
        권한 승인 파일을 버스에 작성한다 (Advisor 또는 사용자가 호출).
        반환: 승인 파일 경로
        """
        os.makedirs(BUS_DIR, exist_ok=True)
        path = os.path.join(BUS_DIR, f'{task_id}_granted_permissions.json')
        # 기존 파일이 있으면 목록에 추가
        granted = []
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            granted = data.get('granted', [])

        if perm_type not in granted:
            granted.append(perm_type)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'task_id': task_id,
                'granted': granted,
                'updated_at': datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)
        return path

    def is_granted(self, task_id: str, perm_type: str) -> bool:
        """승인 파일에 해당 권한이 있으면 True."""
        path = os.path.join(BUS_DIR, f'{task_id}_granted_permissions.json')
        if not os.path.exists(path):
            return False
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return perm_type in data.get('granted', [])

    def check(self, task_id: str, perm_type: str, context: str = '') -> bool:
        """
        통합 권한 체크.
        - auto_approved → True (즉시 승인)
        - is_granted → True (이미 수동 승인됨)
        - requires_user_approval → 요청 파일 작성 후 False 반환
        - 레지스트리 미등록 → False
        """
        if self.is_auto_approved(perm_type):
            return True
        if self.is_granted(task_id, perm_type):
            return True
        if self.requires_user_approval(perm_type):
            self.request_permission(task_id, perm_type, context)
        return False
