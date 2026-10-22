"""第1回 宿題（発展）: 応答時間とトークン数を、モデル × 質問ごとに計測する。

使い方:
    uv run python -m scripts.measure_latency                       # 既定のモデル・回数
    uv run python -m scripts.measure_latency --models gemini-3.5-flash-lite --repeats 5

結果:
    lectures/01/measurements.csv   1回の呼び出しが1行（時刻・モデル・質問・状態・秒数・トークン数）
    lectures/01/responses.jsonl    回答の本文（答えの揺れを見比べる用）

無料枠のレート制限（1分あたりの回数）を超えないよう、モデルごとに呼び出しの間隔をあける。
429（レート制限）や 503（混雑）が返っても止めずに記録する。それも考察の材料にする。
"""

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import errors

from app.config import get_api_key

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "lectures" / "01"

# 形の違う3つの質問: 短い一般用語 / 講座に固有のこと / 長い入力の要約
LONG_TEXT = (ROOT / "lectures" / "01" / "problem.md").read_text(encoding="utf-8")
QUESTIONS = {
    "short_general": "LoRAとは何ですか？",
    "course_specific": "AIE2026の講座の宿題にある「3レベル」とは何ですか？",
    "long_input": "次の文書を3行で要約してください。\n\n" + LONG_TEXT,
}

# 無料枠の 1 分あたりの上限（講座の実測）から決めた呼び出し間隔（秒）
INTERVAL = {
    "gemini-3.5-flash-lite": 5,  # 毎分 15 回 → 4 秒に 1 回。余裕をみて 5 秒
    "gemini-3.8-flash": 14,  # 毎分 5 回 → 12 秒に 1 回。余裕をみて 14 秒
}
DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

FIELDS = [
    "timestamp", "model", "question_id", "repeat", "status", "latency_s",
    "prompt_tokens", "output_tokens", "thoughts_tokens", "total_tokens", "error",
]


def call_once(client: genai.Client, model: str, question: str) -> tuple[dict, str]:
    """1回呼び出して、計測値と回答本文を返す。エラーも記録用の行にする。"""
    row = {"timestamp": datetime.now().isoformat(timespec="seconds"), "model": model}
    start = time.perf_counter()
    try:
        response = client.models.generate_content(model=model, contents=question)
    except errors.APIError as e:
        row.update(status=e.code, latency_s=round(time.perf_counter() - start, 3),
                   error=(e.message or "")[:200])
        return row, ""
    row["latency_s"] = round(time.perf_counter() - start, 3)
    row["status"] = "ok"
    usage = response.usage_metadata
    if usage is not None:
        row.update(
            prompt_tokens=usage.prompt_token_count,
            output_tokens=usage.candidates_token_count,
            thoughts_tokens=usage.thoughts_token_count or 0,
            total_tokens=usage.total_token_count,
        )
    return row, response.text or ""


def main() -> None:
    parser = argparse.ArgumentParser(description="応答時間とトークン数を計測する")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--questions", nargs="+", default=list(QUESTIONS))
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    client = genai.Client(api_key=get_api_key())
    csv_path = OUT_DIR / "measurements.csv"
    new_file = not csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as f_csv, \
            open(OUT_DIR / "responses.jsonl", "a", encoding="utf-8") as f_txt:
        writer = csv.DictWriter(f_csv, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for model in args.models:
            wait = INTERVAL.get(model, 14)
            for rep in range(1, args.repeats + 1):
                for qid in args.questions:
                    row, text = call_once(client, model, QUESTIONS[qid])
                    row.update(question_id=qid, repeat=rep)
                    writer.writerow(row)
                    f_csv.flush()
                    f_txt.write(json.dumps({**row, "answer": text}, ensure_ascii=False) + "\n")
                    f_txt.flush()
                    print(f"{row['timestamp']} {model} {qid} #{rep}: {row['status']} "
                          f"{row['latency_s']}s out={row.get('output_tokens')} "
                          f"think={row.get('thoughts_tokens')}")
                    time.sleep(wait)


if __name__ == "__main__":
    main()
