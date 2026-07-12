"""
子だくさんナース 返信ジェネレーター
@papa_mikaiketsu のキャラクターに合わせたX返信を生成するStreamlitアプリ。

機能1: 投稿文から返信を作る(既存)
機能2: 相手アカウントを調査して、共感ポイントを踏まえた返信を作る(新規)
"""

from __future__ import annotations

import streamlit as st

from api_client import ReplyGenerationError, generate_replies, research_account
from persona_engine import (
    build_account_reply_prompt,
    build_account_research_prompt,
    build_system_prompt,
    build_user_prompt,
)
from storage import append_history, clear_history, load_history, load_settings, save_settings

st.set_page_config(
    page_title="子だくさんナース 返信ジェネレーター",
    page_icon="🩺",
    layout="wide",
)

FREE_LIMIT = 280


def char_len(text: str) -> int:
    return len(text)


def get_secret_api_key() -> str:
    """Streamlit CloudのSecretsに ANTHROPIC_API_KEY があれば取得する。
    ローカル実行などでsecrets.tomlが無い場合は空文字を返す(エラーにしない)。
    """
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


# ------------------------------------------------------------------
# 初期化
# ------------------------------------------------------------------
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()
if "api_key" not in st.session_state:
    # Secretsに設定されていれば自動で使う。無ければ空欄(手入力を促す)
    st.session_state.api_key = get_secret_api_key()
if "post_results" not in st.session_state:
    st.session_state.post_results = None
if "account_research" not in st.session_state:
    st.session_state.account_research = None
if "account_results" not in st.session_state:
    st.session_state.account_results = None


def render_reply_cards(results: list[dict], mode: str, key_prefix: str) -> None:
    """返信案カードの共通描画(投稿文タブ・アカウントタブの両方から使う)"""
    for i, variant in enumerate(results, start=1):
        reply = variant.get("reply", "")
        reason = variant.get("reason", "")
        length = char_len(reply)

        with st.container(border=True):
            top_col1, top_col2 = st.columns([4, 1])
            with top_col1:
                st.markdown(f"**案 {i}**")
            with top_col2:
                if mode == "free":
                    st.markdown(f"✅ {length}文字" if length <= FREE_LIMIT else f"⚠️ {length}文字(超過)")
                else:
                    st.markdown(f"📝 {length}文字")

            st.code(reply, language=None)

            if reason:
                st.caption(f"💡 {reason}")


# ------------------------------------------------------------------
# サイドバー: APIキー・自分の過去ポスト管理・履歴
# ------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 設定")

    _using_secret_key = bool(get_secret_api_key()) and st.session_state.api_key == get_secret_api_key()
    if _using_secret_key:
        st.success("✅ APIキーはSecretsから自動設定済みです", icon="✅")
        with st.expander("別のAPIキーに切り替える"):
            override = st.text_input(
                "Anthropic APIキー(上書き)",
                value="",
                type="password",
                placeholder="別のキーを使う場合のみ入力",
            )
            if override:
                st.session_state.api_key = override
    else:
        st.session_state.api_key = st.text_input(
            "Anthropic APIキー",
            value=st.session_state.api_key,
            type="password",
            help="このセッション内のみ保持されます。ファイルには保存されません。",
        )

    st.divider()
    st.subheader("📝 自分(子だくさんナース)の過去の投稿")
    st.caption("トーンの一貫性を保つための参考データです。複数貼り付けOK(空行区切り)。")

    past_posts_text = st.text_area(
        "過去ポスト履歴",
        value="\n".join(st.session_state.settings.get("past_posts", [])),
        height=180,
        placeholder="例:\n無理に笑わなくていい日も、あると思う。心はちゃんと、サインを出してるだけだから。\n\n(次の投稿をここに貼り付け...)",
        label_visibility="collapsed",
    )

    if st.button("💾 過去ポストを保存", use_container_width=True):
        posts = [p.strip() for p in past_posts_text.split("\n\n") if p.strip()]
        if len(posts) <= 1:
            posts = [p.strip() for p in past_posts_text.split("\n") if p.strip()]
        st.session_state.settings["past_posts"] = posts
        save_settings(st.session_state.settings)
        st.success(f"{len(posts)}件の過去ポストを保存しました")

    st.divider()
    st.subheader("🕘 生成履歴")
    history = load_history()
    if history:
        for h in history[:10]:
            label = h.get("target_post") or h.get("target_account_url") or ""
            with st.expander(f"{h.get('timestamp', '')} ({h.get('mode', '')})"):
                st.caption(h.get("kind", "post"))
                st.text(label[:100])
                for v in h.get("results", []):
                    st.markdown(f"- {v.get('reply', '')[:60]}...")
        if st.button("🗑️ 履歴を全削除", use_container_width=True):
            clear_history()
            st.rerun()
    else:
        st.caption("まだ履歴がありません")

# ------------------------------------------------------------------
# メイン画面
# ------------------------------------------------------------------
st.title("🩺 子だくさんナース 返信ジェネレーター")
st.caption("@papa_mikaiketsu のキャラクターに合わせた返信リプライを生成します")

tab_post, tab_account = st.tabs(["📩 投稿文から返信を作る", "🔎 アカウントから探す"])

# ==================== タブ1: 投稿文から返信を作る(既存機能) ====================
with tab_post:
    col_left, col_right = st.columns([3, 2])

    with col_left:
        target_post = st.text_area(
            "📩 対象ポスト本文",
            height=150,
            placeholder="返信したい相手の投稿をここに貼り付けてください",
            key="post_target",
        )
        additional_instruction_post = st.text_input(
            "➕ 追加指示(任意)",
            placeholder="例:もっと優しく / 少し踏み込んだアドバイスを入れて",
            key="post_extra",
        )

    with col_right:
        mode_label_post = st.radio(
            "📏 返信長モード",
            options=["Free(280文字以内)", "Premium(長文・深い寄り添い)"],
            index=0 if st.session_state.settings.get("default_mode", "free") == "free" else 1,
            key="post_mode",
        )
        mode_post = "free" if mode_label_post.startswith("Free") else "premium"
        num_variants_post = st.slider("生成する案の数", min_value=2, max_value=3, value=3, key="post_num")

        st.session_state.settings["default_mode"] = mode_post
        st.session_state.settings["num_variants"] = num_variants_post

    st.divider()
    generate_post_clicked = st.button("✨ この投稿への返信を生成する", type="primary", use_container_width=True)

    if generate_post_clicked:
        if not target_post.strip():
            st.error("対象ポスト本文を入力してください。")
        elif not st.session_state.api_key:
            st.error("サイドバーからAnthropic APIキーを入力してください。")
        else:
            with st.spinner("子だくさんナースとして返信を考えています…"):
                try:
                    system_prompt = build_system_prompt(mode_post, additional_instruction_post)
                    user_prompt = build_user_prompt(
                        target_post, st.session_state.settings.get("past_posts", []), num_variants_post
                    )
                    results = generate_replies(st.session_state.api_key, system_prompt, user_prompt)
                    st.session_state.post_results = results
                    st.session_state.post_mode_used = mode_post
                    append_history(
                        {
                            "kind": "post",
                            "target_post": target_post,
                            "mode": mode_post,
                            "additional_instruction": additional_instruction_post,
                            "results": results,
                        }
                    )
                except ReplyGenerationError as e:
                    st.error(str(e))
                    st.session_state.post_results = None

    if st.session_state.post_results:
        st.subheader("💬 生成された返信案")
        render_reply_cards(st.session_state.post_results, st.session_state.get("post_mode_used", "free"), "post")
        if st.button("結果をクリア", key="clear_post"):
            st.session_state.post_results = None
            st.rerun()

# ==================== タブ2: アカウントから探す(新機能) ====================
with tab_account:
    st.info(
        "相手のプロフィールURLを入力すると、プロフィールや投稿傾向を調べて共感ポイントを探し、"
        "「はじめてのリプライ」を作ります。特定の1投稿への返信ではなく、"
        "そのアカウント全体への語りかけです。\n\n"
        "⚠️ X(旧Twitter)は外部からの閲覧に制限があるため、自動調査で取得できる情報は"
        "限定的な場合があります。精度を上げたい場合は、下の「相手の投稿を手動で追加」欄に"
        "いくつか投稿を貼り付けてください。",
        icon="ℹ️",
    )

    account_url = st.text_input(
        "🔗 相手アカウントのURL",
        placeholder="例: https://x.com/username",
        key="account_url",
    )

    manual_posts = st.text_area(
        "✍️ 相手の投稿を手動で追加(任意・精度向上用)",
        height=120,
        placeholder="自動調査だけでは情報が足りない場合、相手の投稿をここに貼り付けると精度が上がります",
        key="account_manual_posts",
    )

    research_clicked = st.button("🔍 アカウントを調査する", use_container_width=True)

    if research_clicked:
        if not account_url.strip():
            st.error("相手アカウントのURLを入力してください。")
        elif not st.session_state.api_key:
            st.error("サイドバーからAnthropic APIキーを入力してください。")
        else:
            with st.spinner("アカウントを調べています…(Web検索を行うため少し時間がかかります)"):
                try:
                    research_prompt = build_account_research_prompt(account_url)
                    result = research_account(st.session_state.api_key, research_prompt)
                    st.session_state.account_research = result
                    st.session_state.account_url_used = account_url
                except ReplyGenerationError as e:
                    st.error(str(e))
                    st.session_state.account_research = None

    if st.session_state.account_research:
        research = st.session_state.account_research
        confidence = research.get("research_confidence", "不明")
        confidence_badge = {"high": "🟢 高", "medium": "🟡 中", "low": "🔴 低"}.get(confidence, confidence)

        with st.container(border=True):
            st.markdown(f"**調査結果**(情報充実度: {confidence_badge})")
            st.write(research.get("profile_summary", ""))

            themes = research.get("recurring_themes", [])
            if themes:
                st.markdown("**よく見られる話題**")
                st.markdown("\n".join(f"- {t}" for t in themes))

            empathy = research.get("empathy_points", [])
            if empathy:
                st.markdown("**共感できそうなポイント**")
                st.markdown("\n".join(f"- {e}" for e in empathy))

            if research.get("tone_notes"):
                st.caption(f"トーン: {research['tone_notes']}")

        st.divider()

        col_left2, col_right2 = st.columns([3, 2])
        with col_left2:
            additional_instruction_acc = st.text_input(
                "➕ 追加指示(任意)",
                placeholder="例:子育ての話に寄せて / もっと控えめに",
                key="account_extra",
            )
        with col_right2:
            mode_label_acc = st.radio(
                "📏 返信長モード",
                options=["Free(280文字以内)", "Premium(長文・深い寄り添い)"],
                key="account_mode",
            )
            mode_acc = "free" if mode_label_acc.startswith("Free") else "premium"
            num_variants_acc = st.slider("生成する案の数", min_value=2, max_value=3, value=3, key="account_num")

        generate_account_clicked = st.button(
            "✨ このアカウント向けに返信を作る", type="primary", use_container_width=True
        )

        if generate_account_clicked:
            if not st.session_state.api_key:
                st.error("サイドバーからAnthropic APIキーを入力してください。")
            else:
                with st.spinner("共感ポイントをもとに返信を考えています…"):
                    try:
                        system_prompt = build_system_prompt(mode_acc, additional_instruction_acc)
                        user_prompt = build_account_reply_prompt(
                            research,
                            manual_posts,
                            st.session_state.settings.get("past_posts", []),
                            num_variants_acc,
                        )
                        results = generate_replies(st.session_state.api_key, system_prompt, user_prompt)
                        st.session_state.account_results = results
                        st.session_state.account_mode_used = mode_acc
                        append_history(
                            {
                                "kind": "account",
                                "target_account_url": st.session_state.get("account_url_used", ""),
                                "mode": mode_acc,
                                "additional_instruction": additional_instruction_acc,
                                "results": results,
                            }
                        )
                    except ReplyGenerationError as e:
                        st.error(str(e))
                        st.session_state.account_results = None

    if st.session_state.account_results:
        st.subheader("💬 生成された返信案")
        render_reply_cards(
            st.session_state.account_results, st.session_state.get("account_mode_used", "free"), "account"
        )
        if st.button("結果をクリア", key="clear_account"):
            st.session_state.account_results = None
            st.rerun()
