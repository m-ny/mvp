"""
LVMH Module 4 — CRM 语音录入分析 Demo UI（Streamlit）
运行（在 mvp 根目录）: streamlit run module_4/app.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

_MOD_DIR = Path(__file__).resolve().parent
if str(_MOD_DIR) not in sys.path:
    sys.path.insert(0, str(_MOD_DIR))

from test_deepseek_extract import extract_from_transcript  # noqa: E402

DB_MOCK_DIR = _MOD_DIR / "database_mock"
PROFILE_GLOB = "profile_*.json"


def _inject_luxury_css() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer {visibility: hidden;}
        .block-container {padding-top: 1.2rem; padding-bottom: 1.2rem;}
        .stApp {background: linear-gradient(180deg, #0f0f10 0%, #151517 100%); color: #f3f3f4;}
        .crm-title {font-size: 1.65rem; font-weight: 700; letter-spacing: 0.2px; color: #f7f3e8;}
        .crm-sub {color: #b8b8bc; font-size: 0.92rem; margin-bottom: 0.8rem;}
        .card {
            background: #1b1b1f;
            border: 1px solid #2a2a2f;
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 10px;
        }
        .gold-line {height: 2px; width: 64px; background: #c8a96b; border-radius: 2px; margin: 6px 0 14px 0;}
        .mini-label {font-size: 0.78rem; color: #9f9fa6; text-transform: uppercase; letter-spacing: 0.6px;}
        .mini-value {font-size: 0.98rem; color: #f3f3f4; margin-top: 4px;}
        .status-chip {display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 0.82rem; font-weight: 600;}
        .contact-item {
            background: #1a1a1d; border: 1px solid #2d2d32; border-radius: 10px; padding: 10px; margin-bottom: 8px;
        }
        .contact-name {font-size: 0.95rem; font-weight: 600; color: #f3f3f4;}
        .contact-sub {font-size: 0.78rem; color: #a9a9af;}
        .history-detail-btn button {
            background: #242429 !important;
            color: #f5f5f7 !important;
            border: 1px solid #3a3a41 !important;
        }
        .history-detail-btn button:hover {
            background: #2e2e35 !important;
            color: #ffffff !important;
            border: 1px solid #50505a !important;
        }
        .l1-grid {display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 10px;}
        .l1-card {
            background:#1b1b1f; border:1px solid #2a2a2f; border-radius:12px; padding:12px;
        }
        .l1-key {font-size:0.78rem; color:#bdbdc4; margin-bottom:6px;}
        .l1-latest, .l1-history {
            color:#f2f2f5; line-height:1.45; font-size:0.95rem;
            white-space: normal; overflow: visible; text-overflow: clip; word-break: break-word;
        }
        .l1-history {color:#d5d5db; margin-top:6px; font-size:0.87rem;}
        .stTextInput label, .stTextArea label, .stSelectbox label {color:#f2f2f6 !important;}
        .stMarkdown, .stCaption, .stText {color:#f2f2f6;}
        textarea:disabled, input:disabled {
            color: #f3f3f7 !important;
            -webkit-text-fill-color: #f3f3f7 !important;
            opacity: 1 !important;
        }
        [data-testid="stTooltipIcon"] svg {fill: #d9d9df !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session() -> None:
    st.session_state.setdefault("active_profile", None)
    st.session_state.setdefault("active_raw_text", "")
    st.session_state.setdefault("selected_client", None)
    st.session_state.setdefault("client_needs_text", "")
    st.session_state.setdefault("view_visit_id", None)
    st.session_state.setdefault("edit_signature", "")
    st.session_state.setdefault("edit_mode", False)
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("history_loaded", False)
    st.session_state.setdefault("active_visit_id", None)


def _obj_value(profile: dict, key: str) -> str:
    v = profile.get(key)
    if isinstance(v, dict):
        raw = v.get("_value")
        return "—" if raw is None or raw == "" else str(raw)
    if v is None or v == "":
        return "—"
    return str(v)


def _split_timeline_text(text: str) -> tuple[str, str]:
    """
    将
    "客户行程：xxx | 行动死线/下次到店：yyy"
    拆成 (xxx, yyy)。
    无法匹配时返回 (原文, "")。
    """
    s = (text or "").strip()
    if not s or s == "—":
        return "—", ""
    if "客户行程：" in s and "| 行动死线/下次到店：" in s:
        left = s.split("客户行程：", 1)[1].split("| 行动死线/下次到店：", 1)[0].strip()
        right = s.split("| 行动死线/下次到店：", 1)[1].strip()
        return left or "—", right
    return s, ""


def _extract_name_from_profile(profile: dict) -> str:
    tr = _obj_value(profile, "target_recipients")
    if tr != "—" and tr not in ("客户本人", "客户本人（女性）", "客户本人（男性）"):
        return tr[:18]
    return ""


def _status_color(status: str) -> tuple[str, str]:
    # 与 confidence 的红黄绿解耦：状态用冷暖中性色块，不使用警报红
    if status == "已成交":
        return "#1f6f4a", "#d3f6e7"
    if status == "意向待定":
        return "#8a6b24", "#fbe8b3"
    if status == "仅浏览":
        return "#3a4b63", "#d8e7ff"
    return "#5a5a60", "#efefef"


def _load_records() -> list[dict]:
    rows = []
    if not DB_MOCK_DIR.is_dir():
        return rows
    for fp in DB_MOCK_DIR.glob(PROFILE_GLOB):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            profile = data.get("ai_profile_edited") or {}
            meta = data.get("meta") or {}
            saved_at = data.get("saved_at") or "1970-01-01T00:00:00"
            name = (meta.get("client_display_name") or "").strip()
            if not name:
                nc = meta.get("new_customer") or {}
                name = (nc.get("name") or "").strip()
            if not name:
                name = _extract_name_from_profile(profile)
            if not name:
                name = "客户_" + saved_at.replace("-", "").replace(":", "").replace("T", "_")[:13]
            rows.append(
                {
                    "visit_id": data.get("visit_id") or saved_at,
                    "name": name,
                    "saved_at": saved_at,
                    "profile": profile,
                    "raw_text": data.get("raw_transcript_ca") or "",
                    "meta": meta,
                    "path": fp,
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    rows.sort(key=lambda x: x["saved_at"], reverse=True)
    return rows


def _group_records(records: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for r in records:
        grouped.setdefault(r["name"], []).append(r)
    for k in grouped:
        grouped[k].sort(key=lambda x: x["saved_at"], reverse=True)
    return grouped


def _safe_visit_id(visit_id: str) -> str:
    return (visit_id or datetime.now().isoformat(timespec="seconds")).replace(":", "").replace("-", "").replace("T", "_")


def _save_profile_record(record: dict, customer_mode: str) -> str:
    DB_MOCK_DIR.mkdir(parents=True, exist_ok=True)
    existing_path = record.get("path")
    if existing_path:
        fp = Path(existing_path)
    else:
        fp = DB_MOCK_DIR / f"profile_{_safe_visit_id(record.get('visit_id'))}.json"
    payload = {
        "visit_id": record.get("visit_id"),
        "saved_at": record.get("saved_at") or datetime.now().isoformat(timespec="seconds"),
        "meta": {
            "customer_segment": customer_mode,
            "client_display_name": record.get("name"),
            "returning_client_label": record.get("name") if customer_mode == "Returning Customer" else None,
        },
        "raw_transcript_ca": record.get("raw_text") or "",
        "ai_profile_edited": record.get("profile") or {},
    }
    fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(fp)


def _upsert_history_record(record: dict, *, allow_insert: bool = True) -> bool:
    history: list[dict] = st.session_state.get("history", [])
    vid = record.get("visit_id")
    for i, r in enumerate(history):
        if r.get("visit_id") == vid:
            history[i] = record
            st.session_state.history = history
            return True
    if allow_insert:
        history.append(record)
        st.session_state.history = history
        return True
    return False


def _aggregate_l1(records: list[dict], latest_profile: dict, current_saved_at: str | None = None) -> dict:
    fields = {
        "服务对象": "target_recipients",
        "长期事件": "life_event",
        "体型信息": "size_height",
        "预算": "budget",
        "购买频率": "purchase_frequency",
        "审美偏好": "aesthetic_preference",
        "关注单品": "interested_items",
    }
    agg: dict = {}
    cutoff = current_saved_at
    for label, key in fields.items():
        latest = _obj_value(latest_profile, key)
        hist_values: list[str] = []
        for r in records:
            if cutoff and r.get("saved_at") >= cutoff:
                # 只看“当前这次之前”的历史，避免看到未来记录
                continue
            v = _obj_value(r["profile"], key)
            if v != "—" and v != latest and v not in hist_values:
                hist_values.append(v)
        agg[label] = {"latest": latest, "history": hist_values}
    return agg


def _obj_dict(profile: dict, key: str) -> dict:
    v = profile.get(key)
    if isinstance(v, dict):
        return {
            "_value": v.get("_value"),
            "_evidence": v.get("_evidence"),
            "_confidence": v.get("_confidence"),
        }
    if key == "summary":
        return {"_value": profile.get("summary"), "_evidence": None, "_confidence": None}
    return {"_value": None, "_evidence": None, "_confidence": None}


ALL_TAG_KEYS = [
    "summary",
    "target_recipients",
    "life_event",
    "timeline",
    "size_height",
    "budget",
    "purchase_frequency",
    "aesthetic_preference",
    "interested_items",
    "client_constraints",
    "visit_purpose",
    "purchase_decision_status",
    "positive_signals",
    "negative_reasons",
    "trend_signals",
    "mood",
    "next_step_intent",
    "client_timeline",
    "ca_action_item",
]


def _ensure_edit_buffer(profile: dict, signature: str) -> None:
    if st.session_state.get("edit_signature") == signature:
        return
    st.session_state["edit_summary"] = str(profile.get("summary") or "")
    for key in ALL_TAG_KEYS:
        if key == "summary":
            continue
        st.session_state[f"edit_{key}"] = str(_obj_value(profile, key)).replace("—", "")
    # timeline 自动拆分：客户行程进 client_timeline，行动死线进 ca_action_item
    raw_client_tl = str(_obj_value(profile, "client_timeline")).replace("—", "")
    c_part, a_part = _split_timeline_text(raw_client_tl)
    if c_part:
        st.session_state["edit_client_timeline"] = "" if c_part == "—" else c_part
    if a_part and not st.session_state.get("edit_ca_action_item"):
        st.session_state["edit_ca_action_item"] = a_part
    st.session_state["edit_signature"] = signature


def _help_from_evidence(profile: dict, key: str) -> str:
    ev = _obj_dict(profile, key).get("_evidence")
    if not ev:
        return "🗣️ 原始依据：暂无"
    return f"🗣️ 原始依据：{ev}"


def _render_edit_input(label: str, key: str, profile: dict, *, multiline: bool = False, tooltip: bool = False) -> None:
    help_text = _help_from_evidence(profile, key) if tooltip else None
    widget_key = f"edit_{key}" if key != "summary" else "edit_summary"
    if multiline:
        st.text_area(label, key=widget_key, height=88, help=help_text)
    else:
        st.text_input(label, key=widget_key, help=help_text)


def _build_profile_from_edits(base_profile: dict) -> dict:
    out = dict(base_profile)
    out["summary"] = st.session_state.get("edit_summary", "")
    for key in ALL_TAG_KEYS:
        if key == "summary":
            continue
        base = _obj_dict(base_profile, key)
        out[key] = {
            "_value": st.session_state.get(f"edit_{key}") or None,
            "_evidence": base.get("_evidence"),
            "_confidence": base.get("_confidence") or "Low",
        }
    out["L1_Client_Profile"] = {
        "target_recipients": out.get("target_recipients"),
        "life_event": out.get("life_event"),
        "size_height": out.get("size_height"),
        "budget": out.get("budget"),
        "aesthetic_preference": out.get("aesthetic_preference"),
    }
    out["L2_Constraints"] = {"client_constraints": out.get("client_constraints")}
    out["L3_Visit_Funnel"] = {
        "visit_purpose": out.get("visit_purpose"),
        "purchase_decision_status": out.get("purchase_decision_status"),
        "positive_signals": out.get("positive_signals"),
        "negative_reasons": out.get("negative_reasons"),
        "interested_items": out.get("interested_items"),
        "trend_signals": out.get("trend_signals"),
        "mood": out.get("mood"),
    }
    out["L4_Next_Steps"] = {
        "client_timeline": out.get("client_timeline"),
        "ca_action_item": out.get("ca_action_item"),
    }
    return out


def _render_l1(profile: dict, selected_records: list[dict], current_saved_at: str | None = None, *, edit_mode: bool = False) -> None:
    st.markdown("### L1 基础画像")
    agg = _aggregate_l1(selected_records, profile, current_saved_at=current_saved_at)
    cols = st.columns(2)
    labels = list(agg.keys())
    for idx, label in enumerate(labels):
        data = agg[label]
        with cols[idx % 2]:
            hist_text = "；".join(data["history"][:2]) if data["history"] else "无"
            st.markdown(
                f"""
                <div class="l1-card">
                  <div class="l1-key">{label}</div>
                  <div class="l1-latest">当前：{data["latest"]}</div>
                  <div class="l1-history">历史：{hist_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    if edit_mode:
        st.markdown("#### 编辑标签（L1）")
        e1, e2, e3 = st.columns(3)
        with e1:
            _render_edit_input("服务对象", "target_recipients", profile)
            _render_edit_input("体型信息", "size_height", profile)
            _render_edit_input("购买频率", "purchase_frequency", profile)
        with e2:
            _render_edit_input("长期事件（life_event）", "life_event", profile, multiline=True)
            _render_edit_input("预算", "budget", profile)
        with e3:
            _render_edit_input("审美偏好", "aesthetic_preference", profile, multiline=True)
            _render_edit_input("关注单品（interested_items）", "interested_items", profile, multiline=True)
        _render_edit_input("Summary", "summary", profile, multiline=True)


def _render_l2(profile: dict, *, edit_mode: bool = False) -> None:
    st.markdown("### L2 个人禁忌与硬约束 (Constraints & Dislikes)")
    if edit_mode:
        _render_edit_input(
            "硬约束（可编辑）",
            "client_constraints",
            profile,
            multiline=True,
            tooltip=True,
        )
    else:
        st.markdown(
            f"""
            <div class="card">
              <div class="mini-label">硬约束</div>
              <div class="mini-value">{_obj_value(profile, "client_constraints")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("ⓘ 将鼠标悬停编辑模式字段可查看原始依据")


def _render_l3(profile: dict, *, edit_mode: bool = False) -> None:
    st.markdown("### L3 决策漏斗")
    status = _obj_value(profile, "purchase_decision_status")
    bg, fg = _status_color(status)
    st.markdown(
        f"<span class='status-chip' style='background:{bg}; color:{fg};'>{status}</span>",
        unsafe_allow_html=True,
    )
    if edit_mode:
        e1, e2, e3 = st.columns(3)
        with e1:
            _render_edit_input("Visit Purpose", "visit_purpose", profile, multiline=True, tooltip=True)
            _render_edit_input("决策状态", "purchase_decision_status", profile)
        with e2:
            _render_edit_input("Positive Signals", "positive_signals", profile, multiline=True, tooltip=True)
            _render_edit_input("Negative Reasons", "negative_reasons", profile, multiline=True, tooltip=True)
        with e3:
            _render_edit_input("Trend Signals", "trend_signals", profile, multiline=True, tooltip=True)
            _render_edit_input("Mood", "mood", profile)
    else:
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">Visit Purpose</div>
                  <div class="mini-value">{_obj_value(profile, "visit_purpose")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">决策状态</div>
                  <div class="mini-value">{_obj_value(profile, "purchase_decision_status")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">Positive Signals</div>
                  <div class="mini-value">{_obj_value(profile, "positive_signals")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">Negative Reasons</div>
                  <div class="mini-value">{_obj_value(profile, "negative_reasons")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">Trend Signals</div>
                  <div class="mini-value">{_obj_value(profile, "trend_signals")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">Mood</div>
                  <div class="mini-value">{_obj_value(profile, "mood")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_l4(profile: dict, *, edit_mode: bool = False) -> None:
    st.markdown("### L4 下一步待办")
    c_timeline_raw = _obj_value(profile, "client_timeline")
    c_timeline_only, c_action_from_timeline = _split_timeline_text(c_timeline_raw)
    action_value = _obj_value(profile, "ca_action_item")
    if (not action_value or action_value == "—") and c_action_from_timeline:
        action_value = c_action_from_timeline
    if edit_mode:
        e1, e2 = st.columns(2)
        with e1:
            st.text_area("客户时间线", key="edit_client_timeline", height=88)
        with e2:
            st.text_area("CA 下一步待办", key="edit_ca_action_item", height=88)
    else:
        s1, s2 = st.columns(2)
        with s1:
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">客户时间线</div>
                  <div class="mini-value">{c_timeline_only}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">CA 下一步待办</div>
                  <div class="mini-value">{action_value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_history(records: list[dict]) -> None:
    st.markdown("### 历史记录（可迭代）")
    if not records:
        st.caption("暂无历史记录。")
        return
    st.caption(f"累计到店记录：{len(records)}")
    for idx, r in enumerate(records[:8]):
        p = r["profile"]
        summary = p.get("summary") or "—"
        client_tl = _obj_value(p, "client_timeline")
        ca_tl = _obj_value(p, "ca_action_item")
        timeline = f"客户：{client_tl} | CA：{ca_tl}"
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">{r['saved_at'].replace("T", " ")[:16]}</div>
                  <div class="mini-value"><b>Summary</b>: {summary}</div>
                  <div class="mini-value"><b>Timeline</b>: {timeline}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown("<div class='history-detail-btn'>", unsafe_allow_html=True)
            if st.button("查看本次详情", key=f"drill_{idx}_{r['saved_at']}", use_container_width=True):
                st.session_state.view_visit_id = r["saved_at"]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="LVMH CRM Demo", layout="wide")
    _inject_luxury_css()
    _init_session()

    if not st.session_state.history_loaded:
        all_records = _load_records()
        st.session_state.history = all_records
        st.session_state.history_loaded = True
    grouped = _group_records(st.session_state.get("history", []))

    with st.sidebar:
        st.markdown("## 输入区")
        st.toggle("✏️ Edit", key="edit_mode", help="关闭：静态卡片；开启：可编辑输入框。")
        if st.button("清空输入", use_container_width=True):
            st.session_state.client_needs_text = ""

        st.text_input("客户名称（可选）", key="typed_customer_name", placeholder="例如：王女士 / 陈先生")
        st.text_area(
            "Transcript",
            key="client_needs_text",
            height=180,
            placeholder="粘贴 CA 语音转写内容...",
        )
        trigger = st.button("✨ 提取客户画像", use_container_width=True, type="primary")

        if trigger:
            raw = (st.session_state.get("client_needs_text") or "").strip()
            if not raw:
                st.error("请先输入 Transcript。")
            else:
                with st.spinner("LLM 提取中..."):
                    try:
                        extracted = extract_from_transcript(raw)
                        visit_id = datetime.now().isoformat(timespec="seconds")
                        st.session_state.active_profile = extracted
                        st.session_state.active_raw_text = raw
                        st.session_state.active_visit_id = visit_id
                        manual = (st.session_state.get("typed_customer_name") or "").strip()
                        if manual:
                            st.session_state.selected_client = manual
                        current_name = manual or st.session_state.get("selected_client") or _extract_name_from_profile(extracted) or "未命名客户"
                        draft_record = {
                            "visit_id": visit_id,
                            "name": current_name,
                            "saved_at": visit_id,
                            "profile": extracted,
                            "raw_text": raw,
                            "meta": {"source": "runtime"},
                            "path": None,
                        }
                        _upsert_history_record(draft_record, allow_insert=True)
                        st.session_state.view_visit_id = None
                        st.session_state.edit_signature = ""
                    except Exception as e:
                        st.error(f"提取失败：{e}")

        st.divider()
        st.markdown("## Returning Customers")
        if not grouped:
            st.caption("暂无历史客户。")
        else:
            for client_name, records in grouped.items():
                latest = records[0]["saved_at"].replace("T", " ")[:16]
                if st.button(f"{client_name}", key=f"client_{client_name}", use_container_width=True):
                    st.session_state.selected_client = client_name
                    st.session_state.active_profile = records[0]["profile"]
                    st.session_state.active_raw_text = records[0].get("raw_text", "")
                    st.session_state.active_visit_id = records[0].get("visit_id")
                    st.session_state.edit_signature = ""
                st.markdown(
                    f"<div class='contact-item'><div class='contact-sub'>最近：{latest} · {len(records)} 次到店</div></div>",
                    unsafe_allow_html=True,
                )

    st.markdown("<div class='crm-title'>LVMH · Voice-to-CRM Demo</div>", unsafe_allow_html=True)
    st.markdown("<div class='gold-line'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='crm-sub'>右侧展示为卡片化客户档案；状态色与置信度视觉已解耦，避免冲突。</div>",
        unsafe_allow_html=True,
    )

    profile = st.session_state.get("active_profile")
    selected = st.session_state.get("selected_client")
    selected_records = grouped.get(selected, []) if selected else []
    drill_id = st.session_state.get("view_visit_id")
    drill_rank = None
    drill_total = len(selected_records)
    drill_time_label = None
    current_saved_at = selected_records[0]["saved_at"] if selected_records else None
    if drill_id and selected_records:
        for r in selected_records:
            if r["saved_at"] == drill_id:
                profile = r["profile"]
                st.session_state.active_raw_text = r.get("raw_text", "")
                st.session_state.active_visit_id = r.get("visit_id")
                current_saved_at = r["saved_at"]
                drill_time_label = r["saved_at"].replace("T", " ")[:19]
                break
        # 计次按时间正序：最早=第1次，最新=第N次
        asc_records = sorted(selected_records, key=lambda x: x["saved_at"])
        for i, r in enumerate(asc_records):
            if r["saved_at"] == drill_id:
                drill_rank = i + 1
                break

    if profile:
        signature = f"{st.session_state.get('active_visit_id') or 'noid'}|{selected or 'adhoc'}|{current_saved_at or 'temp'}"
        _ensure_edit_buffer(profile, signature)
        if drill_id:
            h1, h2 = st.columns([1, 3])
            with h1:
                if st.button("⬅️ 返回最新档案", type="secondary"):
                    st.session_state.view_visit_id = None
                    st.rerun()
            with h2:
                if drill_rank is not None and drill_time_label:
                    st.caption(f"当前查看：第 {drill_rank}/{drill_total} 次到店 · {drill_time_label}")
                else:
                    st.caption("当前查看：历史记录详情")
        if selected:
            st.caption(f"当前客户：`{selected}`")
        _render_l1(profile, selected_records, current_saved_at=current_saved_at, edit_mode=st.session_state.get("edit_mode", False))
        st.divider()
        _render_l2(profile, edit_mode=st.session_state.get("edit_mode", False))
        st.divider()
        _render_l3(profile, edit_mode=st.session_state.get("edit_mode", False))
        st.divider()
        _render_l4(profile, edit_mode=st.session_state.get("edit_mode", False))
        st.divider()
        _render_history(selected_records)
        edited_profile = _build_profile_from_edits(profile)

        with st.expander("🎙️ View Original Transcript", expanded=False):
            raw_text = st.session_state.get("active_raw_text") or "暂无原始记录。"
            st.markdown(
                f"""
                <div class="card">
                  <div class="mini-label">Original Voice Memo</div>
                  <div class="mini-value">{raw_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns([1, 2])
        with col1:
            customer_mode = "Returning Customer" if selected else "New Customer"
            if st.button("💾 保存本次记录", type="primary", use_container_width=True):
                typed = (st.session_state.get("typed_customer_name") or "").strip()
                display_name = typed or selected or _extract_name_from_profile(profile) or "未命名客户"
                visit_id = st.session_state.get("active_visit_id") or datetime.now().isoformat(timespec="seconds")
                history = st.session_state.get("history", [])
                target = None
                for rec in history:
                    if rec.get("visit_id") == visit_id:
                        target = rec
                        break
                if target is None:
                    st.error("当前记录缺少 visit_id，无法覆盖保存。请重新生成后再保存。")
                    return
                target["profile"] = edited_profile
                target["name"] = display_name
                target["raw_text"] = st.session_state.get("active_raw_text") or st.session_state.get("client_needs_text") or ""
                ok = _upsert_history_record(target, allow_insert=False)
                if not ok:
                    st.error("覆盖保存失败：未找到对应历史记录。")
                    return
                path = _save_profile_record(target, customer_mode=customer_mode)
                target["path"] = path
                _upsert_history_record(target, allow_insert=False)
                st.session_state.active_profile = edited_profile
                st.success(f"已保存：{path}")
                st.rerun()
        with col2:
            st.caption("保存后会覆盖更新当前 visit，不会新增重复记录。")
    else:
        st.info("在左侧输入 Transcript 并点击「提取客户画像」，结果将在这里以 L1-L4 卡片展示。")


if __name__ == "__main__":
    main()
