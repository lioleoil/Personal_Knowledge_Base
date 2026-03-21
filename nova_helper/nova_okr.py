#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nova_okr.py
/nova_okr 슬랙 커맨드 — OKR 브레인스토밍 파이프라인 모달 + 핸들러.
nova_helper.py가 app 인스턴스를 주입해서 등록한다.
"""

import threading
from pm_pipeline import run_okr_pipeline

MODAL = {
    "type": "modal",
    "callback_id": "nova_okr_modal",
    "title": {"type": "plain_text", "text": "OKR 브레인스토밍"},
    "submit": {"type": "plain_text", "text": "실행"},
    "close":  {"type": "plain_text", "text": "취소"},
    "blocks": [
        {
            "type": "input",
            "block_id": "context_block",
            "label": {"type": "plain_text", "text": "컨텍스트 (제품명 / 상황)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "context_input",
                "placeholder": {"type": "plain_text", "text": "예: Nova Platform Q2"},
            },
        },
        {
            "type": "input",
            "block_id": "quarter_block",
            "label": {"type": "plain_text", "text": "분기"},
            "element": {
                "type": "static_select",
                "action_id": "quarter_select",
                "options": [
                    {"text": {"type": "plain_text", "text": "2026 Q1"}, "value": "2026 Q1"},
                    {"text": {"type": "plain_text", "text": "2026 Q2"}, "value": "2026 Q2"},
                    {"text": {"type": "plain_text", "text": "2026 Q3"}, "value": "2026 Q3"},
                    {"text": {"type": "plain_text", "text": "2026 Q4"}, "value": "2026 Q4"},
                ],
                "initial_option": {
                    "text": {"type": "plain_text", "text": "2026 Q2"},
                    "value": "2026 Q2",
                },
            },
        },
        {
            "type": "input",
            "block_id": "keywords_block",
            "label": {"type": "plain_text", "text": "전략 키워드 (슬래시로 구분)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "keywords_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "예: 유저 활성화 / 아키텍처 전환 / 신규 도메인 확장",
                },
            },
        },
        {
            "type": "input",
            "block_id": "options_block",
            "label": {"type": "plain_text", "text": "산출물 옵션"},
            "element": {
                "type": "checkboxes",
                "action_id": "options_check",
                "options": [
                    {"text": {"type": "plain_text", "text": "PPT 생성 (Gemini AI)"},
                     "value": "ppt"},
                    {"text": {"type": "plain_text", "text": "Confluence 업로드"},
                     "value": "confluence"},
                ],
                "initial_options": [
                    {"text": {"type": "plain_text", "text": "PPT 생성 (Gemini AI)"},
                     "value": "ppt"},
                    {"text": {"type": "plain_text", "text": "Confluence 업로드"},
                     "value": "confluence"},
                ],
            },
            "optional": True,
        },
        {
            "type": "input",
            "block_id": "parent_page_block",
            "label": {"type": "plain_text", "text": "Confluence 부모 페이지 ID (선택)"},
            "hint": {
                "type": "plain_text",
                "text": "비워두면 TE 스페이스 루트에 생성됩니다.",
            },
            "element": {
                "type": "plain_text_input",
                "action_id": "parent_page_input",
                "placeholder": {"type": "plain_text", "text": "예: 123456789"},
            },
            "optional": True,
        },
    ],
}


def register(app):
    """nova_helper.py에서 app 인스턴스를 받아 커맨드·뷰를 등록한다."""

    @app.command("/nova_okr")
    def handle_command(ack, body, client):
        ack()
        client.views_open(trigger_id=body["trigger_id"], view=MODAL)

    @app.view("nova_okr_modal")
    def handle_submission(ack, body, client, view):
        ack()

        vals     = view["state"]["values"]
        context  = vals["context_block"]["context_input"]["value"] or ""
        quarter  = vals["quarter_block"]["quarter_select"]["selected_option"]["value"]
        keywords = vals["keywords_block"]["keywords_input"]["value"] or ""

        selected = [o["value"] for o in
                    (vals["options_block"]["options_check"].get("selected_options") or [])]
        do_ppt        = "ppt" in selected
        do_confluence = "confluence" in selected
        parent_page   = (vals["parent_page_block"]["parent_page_input"].get("value") or "").strip()

        user_id    = body["user"]["id"]
        channel_id = user_id  # DM으로 결과 전송

        threading.Thread(
            target=run_okr_pipeline,
            kwargs=dict(
                context=context,
                quarter=quarter,
                keywords=keywords,
                do_ppt=do_ppt,
                do_confluence=do_confluence,
                parent_page_id=parent_page,
                user_id=user_id,
                channel_id=channel_id,
                slack_client=client,
            ),
            daemon=True,
        ).start()
