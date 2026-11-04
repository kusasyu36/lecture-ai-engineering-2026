"""演習（Pydantic AI）と ADK に同じ質問を投げ、ツール呼び出し・LLM呼び出し回数・回答を並べて表示する。

使い方（リポジトリの直下で）:
    PYTHONPATH=. uv run --with google-adk python adk_agent/compare.py
"""
import asyncio
import json
import sys
import time

from google.genai import types
from google.adk.runners import InMemoryRunner

from app.agent import agent as pyd_agent, build_model
from adk_agent.glossary_agent.agent import root_agent
from pydantic_ai.messages import ToolCallPart

QUESTIONS = [
    "AIE2026の講座の宿題にある「3レベル」とは何ですか？",
    "LoRAとQLoRAの違いは？",
    "第2回の内容から確認問題を1問出して",
    "量子アニーリングとは何ですか？",
]


async def run_pydantic(q):
    r = await pyd_agent.run(q, model=build_model())
    calls = [f"{p.tool_name}({json.dumps(p.args, ensure_ascii=False) if isinstance(p.args, dict) else p.args})"
             for m in r.all_messages() for p in m.parts if isinstance(p, ToolCallPart)]
    usage = r.usage() if callable(r.usage) else r.usage   # 版によってメソッドか属性
    return {"calls": calls, "llm_requests": usage.requests, "answer": r.output}


async def run_adk(runner, q):
    session = await runner.session_service.create_session(app_name=runner.app_name, user_id="u")
    calls, llm_events, answer = [], 0, ""
    async for ev in runner.run_async(user_id="u", session_id=session.id,
                                     new_message=types.Content(role="user", parts=[types.Part(text=q)])):
        # モデルの応答1回分（ツール呼び出しか回答）を数える。ツールの戻り値のイベントは数えない
        if ev.author == root_agent.name and ev.content and not ev.get_function_responses():
            llm_events += 1
        for fc in ev.get_function_calls() or []:
            calls.append(f"{fc.name}({json.dumps(dict(fc.args or {}), ensure_ascii=False)})")
        if ev.is_final_response() and ev.content and ev.content.parts:
            answer = "".join(p.text or "" for p in ev.content.parts)
    return {"calls": calls, "llm_requests": llm_events, "answer": answer}


async def main():
    runner = InMemoryRunner(agent=root_agent, app_name="glossary")
    out = []
    for q in QUESTIONS:
        row = {"question": q}
        for name in ["pydantic_ai", "adk"]:
            t0 = time.time()
            for attempt in range(4):   # 混雑（503）やレート制限（429）は待って再試行する
                try:
                    row[name] = await (run_pydantic(q) if name == "pydantic_ai" else run_adk(runner, q))
                    row[name]["attempts"] = attempt + 1
                    break
                except Exception as e:
                    row[name] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                    if not any(c in str(e) for c in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                        break
                    await asyncio.sleep(20)
            row[name]["seconds"] = round(time.time() - t0, 1)
            await asyncio.sleep(6)   # 無料枠のレート制限（毎分15回）を避ける
        out.append(row)
        print(json.dumps(row, ensure_ascii=False, indent=1), flush=True)
    json.dump(out, open("adk_agent/compare_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    asyncio.run(main())
