# 子だくさんナース 返信ジェネレーター

@papa_mikaiketsu(子だくさんナース)のキャラクターに完全に合わせた
X返信リプライを生成するStreamlitアプリです。

## ✨ 機能

- 対象ポスト本文 + 過去ポスト履歴(一貫性の参照データ)から返信案を2〜3パターン生成
- Free(280文字厳守)/ Premium(長文・深い寄り添い)の切り替え
- 各案に文字数・適合理由を表示
- ワンクリックでコピー可能なコードブロック表示
- 過去ポストの保存(JSON)、生成履歴の自動記録

## 📁 構成

```
papa_mikaiketsu_reply_generator/
├── app.py              # UI本体
├── persona_engine.py   # キャラ設定・プロンプト生成(ここが一貫性の核)
├── api_client.py       # Claude API呼び出し
├── storage.py          # 設定・履歴のJSON保存
├── requirements.txt
└── data/                # 実行時に自動生成される保存先
    ├── settings.json    # 過去ポストなどの設定
    └── history.json     # 生成履歴
```

## 🚀 セットアップ

### ローカル(PCがある場合)

```bash
pip install -r requirements.txt
streamlit run app.py
```

ブラウザが自動で開きます。サイドバーにAnthropic APIキーを入力してください。
(APIキーはファイルに保存されず、セッション内のみで保持されます)

### iPad/iPhoneのみで使いたい場合(PCなし環境向け)

ローカル実行にはPCのターミナル環境が必要なため、**Streamlit Community Cloud**
へのデプロイをおすすめします。

1. このフォルダをGitHubリポジトリにアップロード(いつものiPad→GitHub編集の流れでOK)
2. https://streamlit.io/cloud にアクセスし、GitHubアカウントで連携
3. リポジトリを選択して「Deploy」
4. デプロイ後の設定画面(Settings > Secrets)で以下を追加:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   ※ Secretsに設定した場合は `app.py` のAPIキー入力欄が空でも動くよう、
   将来的に `st.secrets` を読む一行を追加すると自動入力できます
5. 発行されたURLをiPadのSafariでブックマークすればアプリ化できます

## 🧠 キャラクター一貫性の仕組み

`persona_engine.py` の `BASE_PERSONA` に、トーン・語尾・NG事項をすべて
ハードコードしています。Free/Premiumで変わるのは文字数ルールのみで、
キャラの核(共感→気づき→希望の3段階、上から目線を避ける姿勢など)は
共通です。

過去ポストはサイドバーに貼り付けて「💾 過去ポストを保存」を押すと
`data/settings.json` に保存され、次回起動時も引き継がれます。生成のたびに
これらがプロンプトへ「トーンの正解データ」として渡されるため、投稿を
重ねるほど一貫性が保たれやすくなります。

## 🔎 アカウントから探す機能について

相手アカウントのURLを入力すると、Claude APIのWeb検索ツールを使って
プロフィールや投稿傾向を調べ、共感ポイントを抽出したうえで「はじめての
リプライ」を生成します。投稿文への返信機能とは別物ですが、同じ画面
(タブ切り替え)で使えます。

**制限事項**: X(旧Twitter)は外部からの自動アクセスに強い制限をかけているため、
Web検索経由で取得できる情報は不完全・断片的になることがあります。
調査結果には `research_confidence`(high/medium/low)が付き、情報が薄い場合は
無理に具体的な内容に踏み込まず一般的なトーンで返信を作るよう指示しています。
精度を上げたい場合は、「相手の投稿を手動で追加」欄に実際の投稿をいくつか
貼り付けてください。

## 📤 GitHubへの反映(いつもの流れ)

まだこのプロジェクトのリポジトリを作っていない場合:

1. `houmonkangoyoshiyuki-hub` 組織で新規リポジトリを作成
   (例: `papa-mikaiketsu-reply-generator`)
2. リポジトリ内で以下のファイルを1つずつ作成し、`for_github_copy_paste/`
   フォルダ内の対応する `.txt` ファイルの中身をそのまま貼り付けてコミット

   | GitHub上のファイル名 | 貼り付け元(.txt) |
   |---|---|
   | `app.py` | `app.py.txt` |
   | `persona_engine.py` | `persona_engine.py.txt` |
   | `api_client.py` | `api_client.py.txt` |
   | `storage.py` | `storage.py.txt` |
   | `requirements.txt` | `requirements.txt.txt` |
   | `README.md` | `README.md.txt` |
   | `.streamlit/config.toml` | `streamlit_config.toml.txt` |

3. リポジトリ作成後は、Streamlit Community Cloud (https://streamlit.io/cloud)
   でこのリポジトリを選択してデプロイすれば、iPadのSafariからそのまま使えます

すでにリポジトリがある場合は、上記の対応表どおりに各ファイルへ
上書きコミットしてください。

## ⚠️ 注意事項

- 精神科ナースという専門性を踏まえ、断定的な医学的アドバイスに踏み込みすぎない
  ようプロンプト側で制御していますが、生成結果は必ず投稿前に人の目で確認してください
- Free モードの280文字は目安として厳守指示していますが、日本語のカウントは
  Xの仕様(全角/半角の重み付け)と完全一致しない場合があるため、投稿前に
  X側の文字数表示も確認することをおすすめします
- アカウント調査機能はWeb検索を使うぶん、投稿文からの返信生成よりAPIコストが
  やや高くなります
