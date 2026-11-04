# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：同じ質問「AIE2026の講座の宿題にある「3レベル」とは何ですか？」に、第1回の `app.ask` は「具体的なカリキュラムは確認できないが、一般的には…」と前置きして、レベル1〜3を推測で長く説明した（内容は講座の定義と違う）。エージェントは先に用語集を検索し、「基礎・実装・発展の3段階で、どれか1つに取り組めば完了」と講座の定義どおりに答え、最後に「第1回」と関係する回を付けた
- `--trace` で見えたツール呼び出し（ツール名と引数）：
  - 「3レベル」の質問：`search_glossary({'query': '3レベル'})`
  - 「LoRAとQLoRAの違いは？」：`search_glossary({'query': 'LoRA'})` と `search_glossary({'query': 'QLoRA'})`。docstring の「query には調べたい用語を1つだけ入れる」のとおり、用語を1つずつ検索した
- 1つの質問での LLM 呼び出し回数（`requests`）：どちらも 2 回。LoRA の質問はツールを2回呼んだが、2つの検索を1回の応答でまとめて頼んでいたので、requests は増えなかった（1回目でツール呼び出し、2回目で回答）
- 追加したツールと、docstring に書いた説明：`make_quiz(lecture: int)`。docstring は「指定した回の用語から確認問題を1問作り、問題と答えを返す。『第2回の確認問題を出して』のように回を指定して頼まれたときに使う。返ってきた answer は、利用者が答えるまで見せずに、まず question だけを出題すること」。用語がない回（例: 第0回）は、用語がある回の一覧を返す。`--list-tools` に3つ目のツールとして出ることと、「第2回の内容から確認問題を1問出して」で `make_quiz({'lecture': 2})` が呼ばれ、答えを伏せて出題することを確かめた。`uv run pytest -q` は 11 件すべて通った

## 宿題

- 取り組んだレベル：発展（a：Google の ADK で組み立て直す）
- やったこと：
  - `adk_agent/glossary_agent/agent.py` を作り、演習と同じ `INSTRUCTIONS` と、`app/tools.py` の `search_glossary`・`get_lecture_summary`・`make_quiz` をそのまま ADK の `Agent` に渡した（モデルも同じ gemini-3.5-flash-lite）。`app/` のファイルは make_quiz の追加以外は変えていない
  - `PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent` で動かし、「3レベル」の質問に演習と同じ内容で答えることを確かめた
  - 比べやすくするため、`adk_agent/compare.py` で同じ4問を両方に投げ、ツール呼び出し・LLM の呼び出し回数・回答を並べた（ADK 側は `InMemoryRunner` のイベントを数えた）。結果は `lectures/03/compare_result.json`
- 結果：

| 質問 | 呼ばれたツール（両方とも同じ） | LLM 呼び出し（Pydantic AI / ADK） | 回答の違い |
|---|---|---|---|
| 3レベルとは？ | `search_glossary("3レベル")` | 2 / 2 | 内容は同じ。どちらも最後に「第1回」 |
| LoRAとQLoRAの違い | `search_glossary("LoRA")`、`search_glossary("QLoRA")` | 2 / 2 | 内容は同じ。ADK は「（関連する回：第2回）」を付けたが、Pydantic AI 版は付けなかった |
| 第2回の確認問題 | `make_quiz(lecture=2)` | 2 / 2 | どちらも「事前学習の意味は？」を、答えを伏せて出題 |
| 量子アニーリング（用語集にない語） | `search_glossary("量子アニーリング")` | 2 / 2 | どちらも「用語集にはない」と答え、推測で説明しなかった |

  - 書き方の違い：
    - Pydantic AI は `Agent(instructions=...)` を作ってから `agent.tool_plain(関数)` で1つずつ登録し、モデルは実行時（`run_sync(..., model=...)`）に渡す。テストで API を呼ばない `TestModel` に差し替えられるのはこのため
    - ADK は `Agent(model=..., name=..., instruction=..., tools=[関数, ...])` に全部まとめて渡す。モデルは定義のときに決まる。`adk run` が `root_agent` という名前の変数を探すので、名前の決まりがある
    - どちらも関数の docstring と型ヒントがそのままツールの説明になるので、ツールのコードは1行も変えずに使えた
    - 呼び出しの記録は、Pydantic AI は `result.all_messages()` と `usage.requests` で直接読めるが、ADK はイベントの流れ（ツール呼び出し・ツールの戻り値・回答が別々のイベント）を自分で数える必要があった。最初はツールの戻り値のイベントも数えてしまい、LLM 呼び出しを3回と数え間違えた
- 気づき・疑問：
  - 指示とツールが同じなら、フレームワークを替えてもツールの呼び方と回答の中身はほぼ変わらなかった。ふるまいを決めているのは、フレームワークよりも INSTRUCTIONS と docstring だと分かった
  - 「回答の最後に関係する回を示す」は、同じ指示でも守られない回があった（LoRA の質問の Pydantic AI 版）。指示を書いただけでは毎回は守られないので、出力の形を検査するなら、テストか出力の型で縛る必要がある
  - 実行時間は 17〜53 秒とばらつき、途中で 503（混雑）も出た。サーバーの混み具合の影響が大きいので、今回の時間はフレームワークの速さの比較には使えない
  - ADK は環境変数 `GOOGLE_API_KEY` を読み、`GEMINI_API_KEY` と両方あると前者を使うと警告が出た。キーの読み方がフレームワークで違うのは、設定ミスの原因になりそう
  - 疑問：ADK の `adk web` や複数エージェントの機能を使うと、演習の CLI（`--trace`）にあたる情報をどこまで自動で見られるか
