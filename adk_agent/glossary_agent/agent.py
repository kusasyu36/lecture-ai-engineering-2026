"""第3回 宿題（発展 a）: 演習のエージェントを Google ADK で組み立て直す。

指示（INSTRUCTIONS）とツール（app/tools.py の関数）は演習と同じものを使い、
エージェントを組み立てる部分だけを ADK の書き方にする。

動かす（リポジトリの直下で）:
    PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
"""
from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS
from app.config import MODEL

root_agent = Agent(
    model=MODEL,                      # 演習と同じ gemini-3.5-flash-lite（AIE_MODEL で切り替え）
    name="glossary_agent",
    instruction=INSTRUCTIONS,         # 演習と同じ指示
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],  # 関数をそのまま渡す
)
