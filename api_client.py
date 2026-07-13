"""Anthropic API (Claude) 呼び出しラッパー。"""

from __future__ import annotations

import json
import re

import anthropic

# 使用モデル。コスト最優先で最安クラスのHaikuを使用。
# 品質に不満が出た場合は "claude-sonnet-5" に変更可能。
MODEL_NAME = "claude-haiku-4-5-20251001"


class ReplyGenerationError(Exception):
    pass


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _extract_json_array(text: str) -> list:
    """モデル出力からJSON配列を頑健に取り出す。"""
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # JSON配列部分だけを正規表現で抜き出すフォールバック
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ReplyGenerationError("モデルの出力からJSONを解析できませんでした。")


def _extract_json_object(text: str) -> dict:
    """モデル出力からJSONオブジェクト({...})を頑健に取り出す。"""
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ReplyGenerationError("調査結果からJSONを解析できませんでした。")


def research_account(api_key: str, research_prompt: str, max_tokens: int = 2000) -> dict:
    if not api_key:
        raise ReplyGenerationError("APIキーが設定されていません。サイドバーから入力してください。")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": research_prompt}],
        )
    except anthropic.APIError as e:
        raise ReplyGenerationError(f"アカウント調査中にAPI呼び出しが失敗しました: {e}") from e

    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )

    try:
        result = _extract_json_object(raw_text)
    except ReplyGenerationError:
        result = {
            "profile_summary": raw_text.strip() or "(情報を取得できませんでした。手動で投稿を追加してみてください)",
            "recurring_themes": [],
            "empathy_points": [],
            "tone_notes": "",
            "research_confidence": "low",
        }

    return result


def generate_replies(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4000,
) -> list[dict]:
    """
    Claude APIを呼び出し、[{"reply": ..., "reason": ...}, ...] を返す。
    失敗時は ReplyGenerationError を送出。
    """
    if not api_key:
        raise ReplyGenerationError("APIキーが設定されていません。サイドバーから入力してください。")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        raise ReplyGenerationError(f"API呼び出しに失敗しました: {e}") from e

    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )

    try:
        variants = _extract_json_array(raw_text)
    except ReplyGenerationError:
        # 解析失敗時は生テキストをそのまま1案として返す(アプリを落とさない)
        variants = [
            {
                "reply": raw_text.strip(),
                "reason": "⚠️JSON解析に失敗したため、生の出力をそのまま表示しています",
            }
        ]

    # 最低限のバリデーション
    normalized = []
    for v in variants:
        if isinstance(v, dict) and "reply" in v:
            normalized.append(
                {"reply": str(v.get("reply", "")).strip(), "reason": str(v.get("reason", "")).strip()}
            )
    if not normalized:
        raise ReplyGenerationError("有効な返信案が生成されませんでした。もう一度お試しください。")

    return normalized
