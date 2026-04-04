#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
confluence_plugin.py
PM 산출물 전용 Confluence 업로드 플러그인.
doc_gen.py의 인증·페이지 생성 패턴을 재사용한다.
"""

import os
import base64
import warnings
import requests
import urllib3
from pathlib import Path

# 회사 내부망 self-signed 인증서 경고 억제
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 자동 로드 (nova_helper 루트의 .env 또는 상위 .scripts/.env)
def _load_env():
    env_paths = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".scripts" / ".env",
    ]
    for ep in env_paths:
        if ep.exists():
            for line in ep.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            break

_load_env()

CONFLUENCE_URL       = os.environ.get("CONFLUENCE_URL", "https://stradvision.atlassian.net/wiki")
CONFLUENCE_USERNAME  = os.environ.get("CONFLUENCE_USERNAME", "")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "")
CONFLUENCE_SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY", "TE")


def _auth_header() -> dict:
    token = base64.b64encode(
        f"{CONFLUENCE_USERNAME}:{CONFLUENCE_API_TOKEN}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def _md_to_storage(md: str) -> str:
    """마크다운 → Confluence Storage Format(HTML)."""
    try:
        import markdown as md_lib
        return md_lib.markdown(md, extensions=["fenced_code", "tables"])
    except ImportError:
        # markdown 라이브러리 없으면 그대로 텍스트 래핑
        return f"<p>{md.replace(chr(10), '<br/>')}</p>"


def create_pm_page(title: str, md_text: str,
                   space_key: str = CONFLUENCE_SPACE_KEY,
                   parent_page_id: str = "") -> tuple[str, str]:
    """
    Confluence에 PM 산출물 페이지를 생성한다.
    Returns: (page_id, page_url)
    """
    headers = _auth_header()
    body_html = _md_to_storage(md_text)

    payload: dict = {
        "type":  "page",
        "title": title,
        "space": {"key": space_key},
        "body":  {
            "storage": {
                "value":          body_html,
                "representation": "storage",
            }
        },
    }
    if parent_page_id:
        payload["ancestors"] = [{"id": parent_page_id}]

    resp = requests.post(
        f"{CONFLUENCE_URL}/rest/api/content",
        json=payload,
        headers=headers,
        timeout=30,
        verify=False,
    )

    if not resp.ok:
        raise RuntimeError(f"Confluence 페이지 생성 실패 {resp.status_code}: {resp.text[:400]}")

    data  = resp.json()
    pid   = data["id"]
    links = data.get("_links", {})
    base  = links.get("base", CONFLUENCE_URL)
    tiny  = links.get("tinyui") or f"/pages/{pid}"
    return pid, base + tiny


def upload_pptx_attachment(page_id: str, pptx_path: Path) -> str:
    """
    Confluence 페이지에 PPTX 파일을 첨부한다.
    Returns: attachment URL
    """
    token = base64.b64encode(
        f"{CONFLUENCE_USERNAME}:{CONFLUENCE_API_TOKEN}".encode()
    ).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "X-Atlassian-Token": "no-check",  # CSRF 우회 필수
    }

    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/attachment"

    with open(pptx_path, "rb") as f:
        resp = requests.post(
            url,
            headers=headers,
            files={"file": (pptx_path.name, f,
                   "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
            timeout=60,
            verify=False,
        )

    if not resp.ok:
        raise RuntimeError(f"PPTX 첨부 실패 {resp.status_code}: {resp.text[:400]}")

    results = resp.json().get("results", [])
    if results:
        links  = results[0].get("_links", {})
        base   = links.get("base", CONFLUENCE_URL)
        dl     = links.get("download", "")
        return base + dl
    return ""
