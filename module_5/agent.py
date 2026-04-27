"""
Module 5 — Outreach Angle Agent MVP
输入: Supabase — module2_trend_shortlist（经 Top-N + 只读知识库视图进模型）+ module4_client_memories
      （列表仅轻量字段；调用模型前按人所选从数据库拉取该客户完整记忆，等价「按需 tool」）
输出: outreach 建议 + 微信草稿 + run_log.json

运行方式:
  python agent.py              # CA 工作台：展示完整客户池 → 输入序号或 ID 圈选 / all 全选
  python agent.py --demo       # 仅展示客户池（不调模型，无需 API key）
  python agent.py --all
  # 全选里只跑第 1–2 位（避免一次跑太多；本机终端可分段跑完再拼 run_log）
  python agent.py --all --from-index 1 --to-index 2
  python agent.py --clients BENCH_001,BENCH_003

  Web（最小 CA 页，列表多选）:
  python module_5/web_ca.py   # 仓库根目录执行，默认 http://127.0.0.1:5050
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
import config  # noqa: F401 — 仓库根 .env + OPENROUTER→OPENAI 单钥传播
from config import BRAND as _CONFIG_BRAND_DEFAULT
from pipeline_inputs import load_m5_pipeline_inputs, resolve_m5_offline_snapshot_path
from module_5.supabase_reader import fetch_m4_client_full_by_pk
from module_5.trend_kb import build_readonly_trend_kb


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_env_file(_REPO_ROOT / ".env")
_load_env_file(Path(__file__).resolve().parent / ".env")

# ============================================================
# 配置区
# ============================================================
API_KEY = os.environ.get("ANTHROPIC_API_KEY") or ""
MODEL = os.environ.get("DEFAULT_MODEL", "openai/gpt-4o-mini")
# 须与 module1_brand_products.brand 完全一致（如 Tiffany & Co.）；env 在上方 _load_env_file 已合并
BRAND = (os.environ.get("BRAND") or "").strip() or _CONFIG_BRAND_DEFAULT


def _env_float(key: str, default: float) -> float:
    v = os.environ.get(key, "").strip()
    if not v:
        return default
    try:
        return float(v)
    except ValueError:
        return default


TEMPERATURE = _env_float("M5_TEMPERATURE", 0.55)
PROMPT_VERSION = os.environ.get("M5_PROMPT_VERSION", "v2.1").strip() or "v2.1"
LLM_TIMEOUT_SECONDS = _env_float("M5_LLM_TIMEOUT_SECONDS", 75.0)


@dataclass
class M5RunContext:
    trend_kb: dict[str, Any]
    catalog_rows: list[dict[str, Any]] = field(default_factory=list)
    catalog_load_meta: dict[str, Any] = field(default_factory=dict)


def _catalog_enabled() -> bool:
    return os.environ.get("M5_INCLUDE_BRAND_CATALOG", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _load_brand_catalog_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load M1 catalog once per M5 run; per-client code only ranks/serializes it."""
    meta: dict[str, Any] = {"brand": BRAND}
    if not _catalog_enabled():
        return [], {"disabled": True}
    snap = resolve_m5_offline_snapshot_path(_REPO_ROOT)
    if snap is not None and snap.is_file():
        try:
            data = json.loads(snap.read_text(encoding="utf-8"))
            if "catalog_rows" in data:
                rows = data.get("catalog_rows")
                if not isinstance(rows, list):
                    rows = []
                meta.update(
                    {
                        "rows": len(rows),
                        "from_offline_snapshot": str(snap),
                    }
                )
                return list(rows), meta
        except Exception as e:
            return [], {"error": str(e)[:200], "from_snapshot": str(snap), "brand": BRAND}
    try:
        from supabase_client import is_configured

        if not is_configured():
            return [], {"disabled": True, "reason": "supabase_not_configured"}
        from module_1.supabase_reader import read_brand_products

        ds = (os.environ.get("M5_CATALOG_DATA_SOURCE") or "").strip() or None
        rows = read_brand_products(brand=BRAND, data_source=ds)
        meta.update({"rows": len(rows), "data_source": ds})
        return rows, meta
    except Exception as e:
        return [], {"error": str(e)[:200], "brand": BRAND}


def _brand_catalog_block(
    mem: dict,
    trend_kb: dict,
    catalog_rows: list[dict[str, Any]] | None = None,
    catalog_load_meta: dict[str, Any] | None = None,
) -> tuple[str, dict]:
    """
    M1 商品目录：默认 RAG Top-K（向量检索 + 词重叠回退）；M5_CATALOG_RAG=0 时为截断全量列表。
    返回 (prompt_json 片段, 追溯用 meta)。
    """
    meta: dict = dict(catalog_load_meta or {})
    if not _catalog_enabled():
        return "", meta
    try:
        rows = list(catalog_rows or [])
        if not rows:
            return "", meta

        rag_on = os.environ.get("M5_CATALOG_RAG", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )
        try:
            small_catalog_max = int(os.environ.get("M5_CATALOG_SMALL_MAX", "25").strip() or "25")
        except ValueError:
            small_catalog_max = 25
        # Tiffany/demo catalogs are tiny; avoid remote embedding per client and pass the
        # whole small catalog as read-only context.
        if len(rows) <= small_catalog_max:
            try:
                top_k_small = int(os.environ.get("M5_CATALOG_RAG_TOP_K", "10").strip() or "10")
            except ValueError:
                top_k_small = 10
            max_n = max(top_k_small, len(rows))
            picked = rows[:max_n]
            meta.update({"method": "small_catalog_full", "rows": len(picked), "candidates": len(rows)})
            return json.dumps(picked, ensure_ascii=False, indent=2), meta

        if not rag_on:
            raw_max = os.environ.get("M5_CATALOG_PROMPT_MAX", "40").strip() or "40"
            try:
                max_n = int(raw_max)
            except ValueError:
                max_n = 40
            picked = rows if max_n <= 0 else rows[:max_n]
            meta.update({"method": "full_list_truncated", "rows": len(picked), "candidates": len(rows)})
            return json.dumps(picked, ensure_ascii=False, indent=2), meta

        try:
            top_k = int(os.environ.get("M5_CATALOG_RAG_TOP_K", "10").strip() or "10")
        except ValueError:
            top_k = 10
        embed_model = (
            os.environ.get("M5_CATALOG_EMBED_MODEL", "openai/text-embedding-3-small").strip()
        )
        api_key = (
            os.environ.get("OPENROUTER_API_KEY", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
        )
        from module_5.catalog_rag import retrieve_top_products

        picked, rmeta = retrieve_top_products(rows, mem, trend_kb, top_k, api_key, embed_model)
        meta.update(rmeta)
        if not picked:
            return "", meta
        return json.dumps(picked, ensure_ascii=False, indent=2), meta
    except Exception as e:
        return "", {"error": str(e)[:200]}


# ============================================================
# 文件路径
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_PROMPT_PATH = os.path.join(SCRIPT_DIR, "system-prompt v2.1.md")
RUN_LOG_PATH = os.path.join(SCRIPT_DIR, "run_log.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_system_prompt() -> str:
    """
    System prompt 全文（可 env 覆盖路径、可选截掉 FEW-SHOT 以省 token）。

    Env:
      M5_SYSTEM_PROMPT_PATH — 使用指定 md（相对路径相对仓库根或 module_5 目录试解析）
      M5_STRIP_FEWSHOT=1   — 去掉从「# FEW-SHOT EXAMPLES」到文末（少样本最占 token）
    """
    path = os.environ.get("M5_SYSTEM_PROMPT_PATH", "").strip()
    if path:
        p = Path(path)
        if not p.is_absolute():
            for base in (Path(SCRIPT_DIR), _REPO_ROOT):
                cand = (base / path).resolve()
                if cand.is_file():
                    p = cand
                    break
            else:
                p = (_REPO_ROOT / path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"M5_SYSTEM_PROMPT_PATH: not found: {p}")
        text = load_text(str(p))
    else:
        text = load_text(SYSTEM_PROMPT_PATH)
    if os.environ.get("M5_STRIP_FEWSHOT", "").strip().lower() in ("1", "true", "yes", "on"):
        marker = "# FEW-SHOT EXAMPLES"
        if marker in text:
            text = text[: text.index(marker)].rstrip() + "\n"
    return text


def call_llm(system_prompt, user_prompt, temperature: float | None = None):
    """
    优先 OpenRouter：设置了 OPENROUTER_API_KEY（或 ANTHROPIC_API_BASE_URL 指向 openrouter）时
    走 OpenAI 兼容 /chat/completions；否则直连 Anthropic Messages API。
    """
    t = TEMPERATURE if temperature is None else temperature
    _base = os.environ.get("ANTHROPIC_API_BASE_URL", "").strip()
    _or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    _use_openrouter = bool(_or_key) or ("openrouter" in _base.lower())
    if _use_openrouter:
        from openai import OpenAI

        key = _or_key or API_KEY
        if not key:
            raise ValueError(
                "OpenRouter：请设置 OPENROUTER_API_KEY 或 ANTHROPIC_API_KEY（可填同一 OpenRouter key）"
            )
        or_base = _base if "openrouter" in _base.lower() else "https://openrouter.ai/api/v1"
        client = OpenAI(
            base_url=or_base.rstrip("/"),
            api_key=key,
            timeout=LLM_TIMEOUT_SECONDS,
            default_headers={
                "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER", "https://github.com/m-ny-mvp"),
                "X-Title": os.environ.get("OPENROUTER_X_TITLE", "Module 5 Outreach"),
            },
        )
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            temperature=t,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = (response.choices[0].message.content or "").strip()
        u = response.usage
        pt = getattr(u, "prompt_tokens", None) or 0
        ct = getattr(u, "completion_tokens", None) or 0
        return content, {
            "model": MODEL,
            "input_tokens": pt,
            "output_tokens": ct,
            "total_tokens": pt + ct,
        }

    if not API_KEY:
        raise ValueError(
            "未配置 LLM：请设置 OPENROUTER_API_KEY（推荐）或 ANTHROPIC_API_KEY，并写入 .env。"
        )
    _kw = {"api_key": API_KEY}
    if _base:
        _kw["base_url"] = _base
    _kw["timeout"] = LLM_TIMEOUT_SECONDS
    client = anthropic.Anthropic(**_kw)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=t,
    )
    content = response.content[0].text
    usage = response.usage
    return content, {
        "model": MODEL,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.input_tokens + usage.output_tokens,
    }


def parse_agent_output(raw_output):
    text = raw_output.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _merge_usage(primary: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": extra.get("model") or primary.get("model") or MODEL,
        "input_tokens": int(primary.get("input_tokens") or 0) + int(extra.get("input_tokens") or 0),
        "output_tokens": int(primary.get("output_tokens") or 0) + int(extra.get("output_tokens") or 0),
        "total_tokens": int(primary.get("total_tokens") or 0) + int(extra.get("total_tokens") or 0),
    }


def _draft_quality_issues(parsed_output: dict[str, Any], mem: dict[str, Any]) -> list[str]:
    """Prompt-level rules are not enough for small models; catch common unsafe rewrites."""
    source_text = json.dumps(_compact_memory_for_prompt(mem), ensure_ascii=False)
    drafts = parsed_output.get("wechat_drafts") or []
    messages = [
        str(d.get("message") or "")
        for d in drafts
        if isinstance(d, dict) and str(d.get("message") or "").strip()
    ]
    issues: list[str] = []
    if not messages:
        issues.append("wechat_drafts is empty; provide two copy-ready WeChat drafts unless confidence is low.")

    unsupported_terms = ("手写", "两张", "一套", "今天", "稍后", "已确认", "确认好")
    for term in unsupported_terms:
        if term not in source_text and any(term in m for m in messages):
            issues.append(f"Unsupported detail '{term}' appears in draft but not in client memory.")

    weak_phrases = ("最近有想法吗", "随时可以聊聊", "完美无缺", "更特别")
    for phrase in weak_phrases:
        if any(phrase in m for m in messages):
            issues.append(f"Weak or over-polished phrase '{phrase}' should be rewritten.")

    if len(messages) >= 2:
        first_opening = messages[0].split("，", 1)[0]
        second_opening = messages[1].split("，", 1)[0]
        if first_opening and first_opening == second_opening and "想到" in messages[0] and "想到" in messages[1]:
            issues.append("Both drafts use the same remembered-opening pattern; vary the second draft.")

    return issues


def _sanitize_wechat_drafts(parsed_output: dict[str, Any], mem: dict[str, Any]) -> None:
    """Small deterministic polish after the LLM; keeps the stored draft copy-ready."""
    source_text = json.dumps(_compact_memory_for_prompt(mem), ensure_ascii=False)
    drafts = parsed_output.get("wechat_drafts") or []
    if not isinstance(drafts, list):
        return
    for draft in drafts:
        if not isinstance(draft, dict):
            continue
        msg = str(draft.get("message") or "")
        if not msg:
            continue

        replacements = {
            "我这边整理了": "我整理了",
            "我这边可以": "我可以",
            "如果您方便，我可以": "我可以",
            "如果方便的话，我": "我",
            "确认好": "确认",
            "确保您的礼物包装完美无缺": "把包装和贺卡细节也一起说明清楚",
            "请您稍等，我会尽快给您回复。": "",
        }
        for old, new in replacements.items():
            msg = msg.replace(old, new)

        if "手写" not in source_text:
            msg = msg.replace("手写贺卡", "贺卡").replace("手写", "")
        if "两张" not in source_text:
            msg = re.sub(r"两张\s*Tiffany\s*的?\s*", "Tiffany ", msg)
            msg = msg.replace("两张贺卡", "贺卡").replace("两张", "")

        draft["message"] = " ".join(msg.split()).strip()


def display_result(client, result):
    print(f"\n{'='*60}")
    print(f"  {client['client_id']}  {client['name']}  ({client['persona_tag']})")
    print(f"{'='*60}")
    print(f"  Angle:      {result.get('best_angle', 'N/A')}")
    print(f"  Type:       {result.get('outreach_type', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 'N/A')}")
    print(f"  Strategy:   {result.get('angle_summary', 'N/A')}")

    for i, d in enumerate(result.get("wechat_drafts", []), 1):
        print(f"\n  --- Draft {i} [{d.get('tone', '')}] ---")
        print(f"  {d.get('message', '')}")

    flags = result.get("risk_flags", [])
    if flags:
        print(f"\n  Risks: {', '.join(flags)}")

    print(f"  Next step:  {result.get('next_step', 'N/A')}")


def print_ca_client_pool(all_clients: list) -> None:
    """产品侧：在终端展示完整客户池（带序号，便于圈选）。"""
    print("\n")
    print("  ┌─ CA 工作台 · 客户池（完整列表）─────────────────────────────")
    print(f"  │ 共 {len(all_clients)} 人 · 与下方趋势短名单一并作为本次 outreach 输入")
    print("  └──────────────────────────────────────────────────────────────")
    print()
    print(f"  {'序号':>4}  {'client_id':<14}  {'姓名':<18}  persona / VIP")
    print("  " + "-" * 74)
    for i, c in enumerate(all_clients, 1):
        pid = str(c.get("client_id", ""))
        name = str(c.get("name", ""))[:16]
        tag = str(c.get("persona_tag") or "")[:24]
        vip = str(c.get("vip_tier") or "")
        print(f"  {i:4d}  {pid:<14}  {name:<18}  {tag}  [{vip}]")
    print("  " + "-" * 74)


def resolve_ca_selection(choice: str, all_clients: list) -> tuple[list | None, str | None]:
    """
    解析 CA 输入：all 全选；或逗号分隔的「序号」(1-based) 与/或 client_id。
    返回 (clients, None) 或 (None, error_message)。
    """
    raw = choice.strip()
    if not raw:
        return None, "输入为空"
    if raw.lower() == "all":
        return list(all_clients), None
    parts = [x.strip() for x in raw.replace("，", ",").split(",") if x.strip()]
    by_id = {c["client_id"]: c for c in all_clients}
    out: list = []
    for p in parts:
        if p.isdigit():
            i = int(p)
            if i < 1 or i > len(all_clients):
                return None, f"序号 {i} 无效（有效范围 1–{len(all_clients)}）"
            out.append(all_clients[i - 1])
        else:
            if p not in by_id:
                return None, f"未找到 client_id：{p}"
            out.append(by_id[p])
    seen: set[str] = set()
    deduped: list = []
    for c in out:
        cid = c["client_id"]
        if cid not in seen:
            seen.add(cid)
            deduped.append(c)
    return deduped, None


def _memory_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        val = v.get("value")
        ev = v.get("evidence")
        parts = []
        if val not in (None, "", "N/A"):
            parts.append(str(val).strip())
        if ev not in (None, "", "N/A"):
            parts.append(f"evidence: {str(ev).strip()}")
        if parts:
            return " | ".join(parts)
        compact = {k: vv for k, vv in v.items() if vv not in (None, "", [], {}, "N/A")}
        return json.dumps(compact, ensure_ascii=False) if compact else ""
    if isinstance(v, list):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()


def _memory_priority_block(mem: dict[str, Any]) -> str:
    """
    Human-readable priority brief before raw JSON.
    This nudges the LLM toward the new M4 visit fields instead of generic check-ins.
    """
    groups: list[tuple[str, list[str]]] = [
        ("Remembered facts", ["summary", "life_event", "timeline", "visit_purpose", "mood"]),
        ("Preferences and interests", ["aesthetic_preference", "interested_items", "trend_signals"]),
        ("Constraints", ["client_constraints", "budget", "size_height", "negative_reasons"]),
        ("Buying/visit signals", ["purchase_decision_status", "positive_signals", "client_timeline"]),
        ("CA action items", ["ca_action_item", "next_step_intent", "l4_next_steps"]),
    ]
    lines = [
        "Use this brief first. The raw JSON below is the audit trail.",
        "A good draft must include at least one concrete remembered detail from this brief, not only a generic check-in.",
    ]
    for title, keys in groups:
        items = []
        for key in keys:
            val = _memory_value(mem.get(key))
            if val:
                items.append(f"- {key}: {val[:500]}")
        if items:
            lines.append(f"\n### {title}")
            lines.extend(items)
    avoid = []
    for key in ("client_constraints", "negative_reasons", "purchase_decision_status"):
        val = _memory_value(mem.get(key))
        if val:
            avoid.append(f"- {key}: {val[:400]}")
    if avoid:
        lines.append("\n### What the draft should avoid or handle carefully")
        lines.extend(avoid)
    return "\n".join(lines)


def _compact_memory_for_prompt(mem: dict[str, Any]) -> dict[str, Any]:
    """Keep auditability without flooding the LLM with the full M4 profile blob."""
    keep = (
        "client_id",
        "name",
        "persona_tag",
        "source_table",
        "module4_visit_id",
        "saved_at",
        "summary",
        "raw_voice_note",
        "life_event",
        "timeline",
        "aesthetic_preference",
        "size_height",
        "budget",
        "mood",
        "trend_signals",
        "next_step_intent",
        "target_recipients",
        "interested_items",
        "client_constraints",
        "purchase_frequency",
        "visit_purpose",
        "purchase_decision_status",
        "positive_signals",
        "negative_reasons",
        "client_timeline",
        "ca_action_item",
        "l1_client_profile",
        "l2_constraints",
        "l3_visit_funnel",
        "l4_next_steps",
    )
    out = {}
    for key in keep:
        val = mem.get(key)
        if val not in (None, "", [], {}):
            out[key] = val
    return out


def run_for_client(
    client,
    trends_data,
    system_prompt,
    retrieved_sources=None,
    m4_run_id=None,
    run_context: M5RunContext | None = None,
):
    """
    client: 轻量 picker 行（含 memory_row_id）或已是完整记忆 dict。
    若提供 m4_run_id 且 client 含 memory_row_id，则在调用模型前从 Supabase 拉取该行完整记忆。
    """
    mem = client
    if m4_run_id and client.get("memory_row_id") is not None:
        try:
            mem = fetch_m4_client_full_by_pk(m4_run_id, int(client["memory_row_id"]))
        except Exception as e:
            print(f"\n  ⚠️ 无法拉取客户完整记忆 id={client.get('memory_row_id')}: {e}")
            raise

    trend_kb = run_context.trend_kb if run_context else build_readonly_trend_kb(trends_data)
    catalog_json, catalog_meta = _brand_catalog_block(
        mem,
        trend_kb,
        catalog_rows=run_context.catalog_rows if run_context else None,
        catalog_load_meta=run_context.catalog_load_meta if run_context else None,
    )
    catalog_section = ""
    if catalog_json:
        catalog_section = f"""
## Brand product catalog (read-only, M1, RAG Top-K)
以下为根据**当前客户记忆 + 本批趋势知识库**从目录中检索出的相关 SKU（非全量表）。引用时请以块内字段为准，勿编造未出现的规格或价格。
注意：目录块只是参考，不是必须推荐清单。如果某个 SKU 不符合客户明确提到的品类、约束、预算或行动项，请不要硬塞进推荐；可以改用更宽的“方向/系列/对比图”表达。
{catalog_json}
"""
    user_prompt = f"""请为以下客户生成 **微信私聊用的 outreach 建议**（不是店内导购与顾客面对面说话的脚本）。

**场景**：CA 同时管理多位客户；下方 Client Memory 与 **Trend Shortlist（只读知识库）** 是系统里已有的「客户记忆 + 本批可参考趋势」。趋势块为**只读参考**，用于分析与引用，不可当作可编辑数据。常见用途：新品到店想轻触达、想联系一段时间未互动的客户、或需要基于记忆写一句不尴尬的开场。**消息是异步的**：客户不在店员面前，是在手机上看微信。

请按系统提示中的 OPERATING CONTEXT 与 VOICE AND TONE：草稿要像 **CA 打字发出去的短消息**，偏 conversation starter / 轻触达；需要时可点到 **可推荐的新品方向或品类**（来自趋势与记忆的合理衔接），避免写成「现场带您试穿、现在方便吗」一类当面话术。

**质量要求**：不要只写“最近有想法吗 / 随时聊聊”这类泛泛问候。每条草稿至少要使用一个 Client Memory Priority Brief 里的具体细节（如预算、场合、材质限制、尺码、感兴趣品类、比较点、CA action item），并给出一个轻量但具体的下一步（如发两三张对比图、确认材质/尺寸/工期、整理几组方向）。
如果客户说“和某材质/品牌/品类做比较”，这只是 comparison point，不等于客户偏好；草稿应写“方便做对比/我整理几组可对比方向”，不要改写成“您喜欢该材质/品牌”。
区分客户事件时间和 CA 行动截止：例如“明天下午5点前确认现货图片和价格”是 CA deadline，不等于“明天是生日/活动日”，不要改写事件日期。
保留 operational detail 的边界：不要把“贺卡”扩写成“手写贺卡”，不要新增“两张/一套”等数量，不要把“明天下午5点前”改写成“今天/稍后”，不要承诺“已确认现货/价格”。

**最终文案标准**：输出前请像资深 CA 审稿一样过滤一次：这两条微信是否可以直接复制给客户？是否有具体 remembered detail？是否有具体但轻的下一步？是否避免了库存/价格/时间的无依据承诺？如果答案是否，请重写草稿再输出 JSON。

## Context
- Brand (Maison): {BRAND}

## Client Memory Priority Brief
{_memory_priority_block(mem)}

## Client Memory
{json.dumps(_compact_memory_for_prompt(mem), ensure_ascii=False, indent=2)}

## Trend Shortlist (read-only knowledge base)
{json.dumps(trend_kb, ensure_ascii=False, indent=2)}
{catalog_section}"""
    print(f"\n  正在为 {mem['name']} ({mem['client_id']}) 调用 LLM...")
    raw_output, token_usage = call_llm(system_prompt, user_prompt)
    parsed_output = parse_agent_output(raw_output)

    if parsed_output is None:
        repair = (
            user_prompt
            + "\n\n你的上一段输出无法被解析为合法 JSON。"
            + "请严格只输出一个符合系统提示中 OUTPUT FORMAT 的 JSON 对象；"
            + "不要使用 markdown 代码块；不要添加任何 JSON 以外的文字。"
        )
        raw_output2, token_usage2 = call_llm(system_prompt, repair, temperature=min(TEMPERATURE, 0.35))
        raw_output = raw_output2
        token_usage = _merge_usage(token_usage, token_usage2)
        parsed_output = parse_agent_output(raw_output)

    if parsed_output and os.environ.get("M5_QUALITY_REPAIR", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    ):
        quality_issues = _draft_quality_issues(parsed_output, mem)
        if quality_issues:
            repair = (
                user_prompt
                + "\n\n你的上一段 JSON 可以解析，但微信草稿没有通过质量检查。"
                + "\n请保留同一客户事实，只重写输出 JSON，尤其是 wechat_drafts / risk_flags / next_step。"
                + "\n不要使用 markdown 代码块；不要添加 JSON 以外的文字。"
                + "\n\n质量问题：\n- "
                + "\n- ".join(quality_issues)
            )
            raw_output2, token_usage2 = call_llm(system_prompt, repair, temperature=min(TEMPERATURE, 0.25))
            repaired_output = parse_agent_output(raw_output2)
            if repaired_output is not None:
                raw_output = raw_output2
                parsed_output = repaired_output
                token_usage = _merge_usage(token_usage, token_usage2)

    if parsed_output:
        _sanitize_wechat_drafts(parsed_output, mem)
        display_result(mem, parsed_output)
    else:
        print(f"\n  ⚠️ {mem['name']} 的输出无法解析为 JSON（已重试一次）")

    trace_sources = list(retrieved_sources or ["module4_memory", "module2_shortlist"])
    if catalog_json:
        trace_sources.append("module1_brand_products_rag")
    return {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "timestamp": datetime.now().isoformat(),
        "model": token_usage["model"],
        "token_usage": token_usage,
        "input": {
            "client_id": mem["client_id"],
            "client_name": mem["name"],
            "trend_ids": [t["trend_id"] for t in trends_data["trends"]],
        },
        "output": {
            "raw": raw_output,
            "parsed": parsed_output,
        },
        "trace": {
            "retrieved_sources": trace_sources,
            "catalog_rag": catalog_meta or None,
            "decision_output": parsed_output.get("best_angle") if parsed_output else None,
            "evidence_used": parsed_output.get("evidence_used") if parsed_output else None,
            "confidence": parsed_output.get("confidence") if parsed_output else None,
            "next_step": parsed_output.get("next_step") if parsed_output else None,
        },
    }


def _failed_log_entry(client: dict[str, Any], error: Exception) -> dict[str, Any]:
    return {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "token_usage": {"model": MODEL, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        "input": {
            "client_id": client.get("client_id", ""),
            "client_name": client.get("name", ""),
            "trend_ids": [],
        },
        "output": {
            "raw": "",
            "parsed": {
                "best_angle": "generation_failed",
                "outreach_type": "error",
                "angle_summary": f"M5 generation failed for this client: {type(error).__name__}: {str(error)[:240]}",
                "evidence_used": [],
                "recommended_products": [],
                "wechat_drafts": [],
                "confidence": "low",
                "risk_flags": ["generation_failed"],
                "do_not_say": [],
                "next_step": "Retry this client individually after checking the LLM/API error.",
            },
        },
        "trace": {
            "retrieved_sources": [],
            "catalog_rag": None,
            "decision_output": "generation_failed",
            "evidence_used": [],
            "confidence": "low",
            "next_step": "Retry this client individually after checking the LLM/API error.",
            "error": f"{type(error).__name__}: {str(error)[:500]}",
        },
    }


def _write_run_logs_snapshot(run_logs: list[dict[str, Any]]) -> None:
    with open(RUN_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(run_logs, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Module 5 — 为所选客户生成 outreach（全选 / 圈选 / 单人交互）"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="全选：对当前加载列表中的全部客户各生成一条结果",
    )
    parser.add_argument(
        "--clients",
        default="",
        metavar="IDS",
        help="圈选：序号或 client_id，逗号分隔，例如 1,3,5 或 BENCH_001,BENCH_003",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="仅展示完整客户池（不调模型，无需 API key；体验产品侧列表）",
    )
    parser.add_argument(
        "--from-index",
        type=int,
        default=None,
        metavar="N",
        help="仅与 --all 联用：从客户池第 N 位开始（1-based，含 N）",
    )
    parser.add_argument(
        "--to-index",
        type=int,
        default=None,
        metavar="N",
        help="仅与 --all 联用：到第 N 位结束（1-based，含 N）；省略则到列表末尾",
    )
    args = parser.parse_args()
    if args.all and args.clients.strip():
        parser.error("请只使用 --all 或 --clients 之一，不要同时指定")
    if args.demo and (args.all or args.clients.strip()):
        parser.error("--demo 不能与 --all / --clients 同时使用")
    if (args.from_index is not None or args.to_index is not None) and not args.all:
        parser.error("--from-index / --to-index 只能与 --all 联用")

    print("\n🤖 Module 5 — Outreach Angle Agent MVP")
    print("=" * 60)

    system_prompt = load_system_prompt()
    bundle = load_m5_pipeline_inputs(repo_root=_REPO_ROOT)
    clients_data = bundle.clients_data
    trends_data = bundle.trends_data
    src = bundle.sources
    trend_kb = build_readonly_trend_kb(trends_data)
    catalog_rows, catalog_load_meta = _load_brand_catalog_rows()
    run_context = M5RunContext(
        trend_kb=trend_kb,
        catalog_rows=catalog_rows,
        catalog_load_meta=catalog_load_meta,
    )
    retrieved = [
        src.get("client_source_path", ""),
        src.get("trend_shortlist_path", ""),
    ]
    print("\n[输入] 数据源:")
    print(f"  趋势短名单: {src.get('trend_shortlist_path')}")
    print(f"  客户记忆:   {src.get('client_source_path')} ({src.get('client_source_kind')})")
    print(f"  M4 run_id:  {src.get('module4_run_id', '')}")
    if catalog_load_meta.get("disabled"):
        print("  商品目录:   disabled")
    elif catalog_load_meta.get("from_offline_snapshot"):
        print(f"  商品目录:   offline snapshot rows={len(catalog_rows)} (brand={BRAND})")
    else:
        print(f"  商品目录:   module1_brand_products brand={BRAND} rows={len(catalog_rows)}")

    m4_run_id = src.get("module4_run_id")
    all_clients = clients_data["clients"]

    if args.demo:
        print_ca_client_pool(all_clients)
        print(
            "  以上为当前加载的完整客户池（预览结束）。\n"
            "  若要圈选并生成 outreach：在本机终端执行\n"
            "    python3 module_5/agent.py\n"
            "  按提示输入序号、client_id 或 all；或直接使用：\n"
            "    python3 module_5/agent.py --clients 1,2,3\n"
        )
        return

    if args.all:
        clients_to_run = all_clients
        print(f"\n  全选：将为 {len(clients_to_run)} 个客户各调用一次模型并汇总结果")
    elif args.clients.strip():
        clients_to_run, err = resolve_ca_selection(args.clients, all_clients)
        if err:
            print(f"  错误：{err}")
            return
        if not clients_to_run:
            print("  错误：未选中任何客户")
            return
        print(f"\n  圈选：已选 {len(clients_to_run)} 个客户，将各调用一次模型")
    else:
        print_ca_client_pool(all_clients)
        print("  ── 请选择本次要生成 outreach 的客户 ──")
        print("    · 输入 all — 全选上面列表中的全部客户")
        print("    · 输入序号 — 一人：3  或多人：1,3,5（逗号分隔，对应上表序号）")
        print("    · 输入 client_id — 一人：BENCH_001  或多人：BENCH_001,BENCH_003")

        if sys.stdin.isatty():
            choice = input("\n  请输入（然后回车）: ").strip()
        else:
            choice = "all"
        clients_to_run, err = resolve_ca_selection(choice, all_clients)
        if err:
            print(f"  错误：{err}")
            return
        if choice.lower() == "all":
            print(f"\n  已确认全选：共 {len(clients_to_run)} 人，将各调用一次模型")
        else:
            print(f"\n  已确认圈选：共 {len(clients_to_run)} 人，将各调用一次模型")

    if args.all and (args.from_index is not None or args.to_index is not None):
        n = len(clients_to_run)
        start1 = args.from_index if args.from_index is not None else 1
        end1 = args.to_index if args.to_index is not None else n
        if start1 < 1 or end1 < 1 or start1 > n or end1 > n:
            print(f"  错误: --from-index / --to-index 超出客户池范围 1..{n}")
            return
        if end1 < start1:
            print("  错误: --to-index 不能小于 --from-index")
            return
        clients_to_run = clients_to_run[start1 - 1 : end1]
        print(
            f"  子范围(全选切片): 第 {start1}–{end1} 位，共 {len(clients_to_run)} 人，将各调用一次模型"
        )

    if src.get("input_mode") == "offline_snapshot":
        full_clients_to_run = list(clients_to_run)
        sp = src.get("snapshot_path") or ""
        print(
            f"  离线快照: 已加载完整 M4 记忆，跳过 Supabase 预取"
            + (f" ({sp})" if sp else "")
        )
    else:
        full_clients_to_run = []
        for i, client in enumerate(clients_to_run, 1):
            if m4_run_id and client.get("memory_row_id") is not None:
                try:
                    print(
                        f"  预取 M4 完整记忆 {i}/{len(clients_to_run)}: "
                        f"{client.get('name', '')} (row id={client.get('memory_row_id')})"
                    )
                    sys.stdout.flush()
                    full_clients_to_run.append(
                        fetch_m4_client_full_by_pk(m4_run_id, int(client["memory_row_id"]))
                    )
                except Exception as e:
                    print(f"\n  ⚠️ 无法预加载客户完整记忆 id={client.get('memory_row_id')}: {e}")
                    raise
            else:
                full_clients_to_run.append(client)

    run_logs = []
    for idx, client in enumerate(full_clients_to_run, 1):
        try:
            print(f"\n  [进度] {idx}/{len(full_clients_to_run)}")
            log_entry = run_for_client(
                client,
                trends_data,
                system_prompt,
                retrieved_sources=retrieved,
                m4_run_id=None,
                run_context=run_context,
            )
        except Exception as e:
            print(
                f"\n  ⚠️ {client.get('name', client.get('client_id', 'unknown'))} 生成失败，"
                f"已记录错误并继续下一个：{type(e).__name__}: {str(e)[:220]}"
            )
            log_entry = _failed_log_entry(client, e)
        run_logs.append(log_entry)
        _write_run_logs_snapshot(run_logs)

    print(f"\n✅ 全部完成。{len(run_logs)} 条 run log 已保存: {RUN_LOG_PATH}")

    # ── Supabase sync ──────────────────────────────────────────────
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).parent.parent))
        from supabase_writer import write_outreach_suggestion, write_run_log
        from supabase_client import is_configured
        if is_configured():
            from datetime import datetime as _dt
            run_id = _dt.utcnow().strftime("m5_%Y%m%d_%H%M%S")
            for log in run_logs:
                inp = log.get("input") or {}
                parsed = (log.get("output") or {}).get("parsed") or {}
                drafts = parsed.get("wechat_drafts") or []
                first_msg = drafts[0].get("message", "") if drafts else ""
                write_outreach_suggestion(run_id, {
                    "client_id":          inp.get("client_id", ""),
                    "outreach_angle":     parsed.get("best_angle", ""),
                    "wechat_draft":       first_msg,
                    "reasoning":          parsed.get("angle_summary", ""),
                    "trend_signals_used": parsed.get("evidence_used", []),
                    "client_memory_ref":  {
                        "client_id": inp.get("client_id"),
                        "trend_ids": inp.get("trend_ids", []),
                        "evidence_used": parsed.get("evidence_used"),
                    },
                    "confidence":         parsed.get("confidence", ""),
                    "model_used":         MODEL,
                })
            first_cid = (run_logs[0].get("input") or {}).get("client_id", "") if run_logs else ""
            write_run_log(run_id, first_cid, MODEL, PROMPT_VERSION, len(run_logs),
                          {"run_logs": run_logs})
            print(f"  [DB] Supabase sync complete ({len(run_logs)} suggestions)")
        else:
            print("  [DB] Supabase skipped (SUPABASE_PASSWORD not set)")
    except Exception as _e:
        print(f"  [DB WARN] Supabase sync skipped: {_e}")


if __name__ == "__main__":
    main()
