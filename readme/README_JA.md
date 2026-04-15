<p align="center">
    <h1 align="center"><img vertical-align="middle" width="400px" src="../img/logo-full-new.png" alt="A.I.G"/></h1>
</p>
<p align="center">
  <a href="https://tencent.github.io/AI-Infra-Guard/">📖 ドキュメント</a> &nbsp;|&nbsp;
  🌐 <a href="../README.md">🇬🇧 English</a> · <a href="./README_ZH.md">🇨🇳 中文</a> · <b>🇯🇵 日本語</b> · <a href="./README_ES.md">🇪🇸 Español</a> · <a href="./README_DE.md">🇩🇪 Deutsch</a> · <a href="./README_FR.md">🇫🇷 Français</a> · <a href="./README_KR.md">🇰🇷 한국어</a> · <a href="./README_PT.md">🇧🇷 Português</a> · <a href="./README_RU.md">🇷🇺 Русский</a>
</p>
<p align="center">
    <a href="https://github.com/tencent/AI-Infra-Guard/stargazers">
      <img src="https://img.shields.io/github/stars/tencent/AI-Infra-Guard?style=social" alt="GitHub stars">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="GitHub downloads" src="https://img.shields.io/github/downloads/Tencent/AI-Infra-Guard/total">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="docker pulls" src="https://img.shields.io/docker/pulls/zhuquelab/aig-server.svg?color=gold">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="Release" src="https://img.shields.io/github/v/release/Tencent/AI-Infra-Guard?color=green">
    </a>
    <a href="https://deepwiki.com/Tencent/AI-Infra-Guard">
       <img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki">
    </a>
</p>
<p align="center">
  <a href="https://trendshift.io/repositories/13637" target="_blank"><img src="https://trendshift.io/api/badge/repositories/13637" alt="Tencent%2FAI-Infra-Guard | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
  <a href="https://www.blackhat.com/eu-25/arsenal/schedule/index.html#aigai-infra-guard-48381" target="_blank"><img src="../img/blackhat.png" alt="Tencent%2FAI-Infra-Guard | blackhat" style="width: 175px; height: 55px;" width="175" height="55"/></a>
  <a href="https://github.com/deepseek-ai/awesome-deepseek-integration" target="_blank"><img src="../img/awesome-deepseek.png" alt="Tencent%2FAI-Infra-Guard | awesome-deepseek-integration" style="width: 273px; height: 55px;" width="273" height="55"/></a>
</p>

<br>

<p align="center">
    <h2 align="center">Tencent Zhuque Lab による AI レッドチーミングプラットフォーム</h2>
</p>

<b>A.I.G (AI-Infra-Guard)</b> は、ClawScan（OpenClawセキュリティスキャン）、Agent Scan、AIインフラ脆弱性スキャン、MCPサーバー＆エージェントスキルスキャン、ジェイルブレイク評価などの機能を統合し、AIセキュリティリスクの自己診断において最も包括的でインテリジェント、かつ使いやすいソリューションをユーザーに提供することを目指しています。

<p>
  私たちはA.I.G（AI-Infra-Guard）を業界をリードするAIレッドチーミングプラットフォームにすることに尽力しています。より多くのスターは、このプロジェクトをより広いユーザーに届け、より多くの開発者の貢献を促し、イテレーションと改善を加速させます。あなたのスターは私たちにとって非常に重要です！
</p>
<p align="center">
  <a href="https://github.com/Tencent/AI-Infra-Guard">
      <img src="https://img.shields.io/badge/⭐-Give%20us%20a%20Star-yellow?style=for-the-badge&logo=github" alt="Give us a Star">
  </a>
</p>

<br>

## 🚀 最新情報

- **2026-04-09** · [v4.1.3](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1.3) — 対応AIコンポーネントが55種に拡大；crewai・kubeai・lobehubを新規追加。
- **2026-04-03** · [v4.1.2](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1.2) — ClawHubに3つの新スキル（`edgeone-clawscan`・`edgeone-skill-scanner`・`aig-scanner`）を公開。タスク手動停止に対応。
- **2026-03-25** · [v4.1.1](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1.1) — ☠️ LiteLLMサプライチェーン攻撃を検出可能に（重大）；Blinko・New-APIの対応を追加。
- **2026-03-23** · [v4.1](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1) — OpenClaw脆弱性データベースに281件のCVE/GHSAエントリを追加。
- **2026-03-10** · [v4.0](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.0) — EdgeOne ClawScan（OpenClawセキュリティスキャン）とAgent-Scanフレームワークを公開。

👉 [CHANGELOG](../CHANGELOG.md) · 🩺 [EdgeOne ClawScanを試す](https://matrix.tencent.com/clawscan)


## 目次
- [クイックスタート](#-クイックスタート)
- [機能一覧](#-機能一覧)
- [スクリーンショット](#-スクリーンショット)
- [ユーザーガイド](#-ユーザーガイド)
- [APIドキュメント](#-apiドキュメント)
- [🏗️ アーキテクチャの変遷](../docs/architecture_evolution.md)
- [コントリビューションガイド](#-コントリビューションガイド)
- [謝辞](#-謝辞)
- [コミュニティに参加](#-コミュニティに参加)
- [引用](#-引用)
- [関連論文](#-関連論文)
- [ライセンスと帰属表示](#️-ライセンスと帰属表示)
<br><br>

## クイックスタート
### Dockerによるデプロイ

| Docker | RAM | ディスク容量 |
|:-------|:----|:----------|
| 20.10以上 | 4GB以上 | 10GB以上 |

```bash
# この方法はDocker Hubからビルド済みイメージを取得するため、より高速に起動できます
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
# Docker Compose V2以降では、'docker-compose' を 'docker compose' に置き換えてください
docker-compose -f docker-compose.images.yml up -d
```

サービスが起動したら、以下のURLでA.I.GのWebインターフェースにアクセスできます：
`http://localhost:8088`
<br>

### OpenClawからの使用

`aig-scanner`スキルを使用して、OpenClawチャットからA.I.Gを直接呼び出すこともできます。

```bash
clawhub install aig-scanner
```

その後、`AIG_BASE_URL`を実行中のA.I.Gサービスを指すように設定してください。

詳細については、[`aig-scanner` README](../skills/aig-scanner/README.md)を参照してください。

<details>
<summary><strong>その他のインストール方法</strong></summary>

### その他のインストール方法

**方法2: ワンクリックインストールスクリプト（推奨）**
```bash
# この方法はDockerを自動的にインストールし、1コマンドでA.I.Gを起動します
curl https://raw.githubusercontent.com/Tencent/AI-Infra-Guard/refs/heads/main/docker.sh | bash
```

**方法3: ソースからビルドして実行**
```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
# この方法はローカルソースコードからDockerイメージをビルドしてサービスを開始します
# （Docker Compose V2以降では、'docker-compose' を 'docker compose' に置き換えてください）
docker-compose up -d
```

注意: AI-Infra-Guardプロジェクトは、企業または個人の内部使用向けのAIレッドチーミングプラットフォームです。現在、認証メカニズムがないため、パブリックネットワークにデプロイすべきではありません。

詳細については、[https://tencent.github.io/AI-Infra-Guard/?menu=getting-started](https://tencent.github.io/AI-Infra-Guard/?menu=getting-started) を参照してください。

</details>

### オンラインPro版を試す
高度な機能と改善されたパフォーマンスを備えたPro版をお試しください。Pro版には招待コードが必要で、Issue、Pull Request、Discussionを提出した方、またはコミュニティの成長に積極的に貢献された方が優先されます。アクセス: [https://aigsec.ai/](https://aigsec.ai/)
<br>
<br>

## 機能一覧

| 機能 | 詳細 |
|:--------|:------------|
| **ClawScan（OpenClawセキュリティスキャン）** | OpenClawのセキュリティリスクのワンクリック評価に対応。安全でない設定、スキルリスク、CVE脆弱性、プライバシー漏洩を検出します。 |
| **Agent Scan** | 独立したマルチエージェント自動スキャンフレームワークです。AIエージェントワークフローのセキュリティを評価するために設計されています。DifyやCozeなど、さまざまなプラットフォームで動作するエージェントをシームレスにサポートします。 |
| **MCPサーバー＆エージェントスキルスキャン** | 14の主要なセキュリティリスクカテゴリを徹底的に検出します。MCPサーバーとエージェントスキルの両方に適用されます。ソースコードとリモートURLの両方からのスキャンに柔軟に対応します。 |
| **AIインフラ脆弱性スキャン** | 57以上のAIフレームワークコンポーネントを正確に識別するスキャナーです。1000以上の既知のCVE脆弱性をカバーしています。対応フレームワークにはOllama、ComfyUI、vLLM、n8n、Triton Inference Serverなどが含まれます。 |
| **ジェイルブレイク評価** | 厳選されたデータセットを使用してプロンプトのセキュリティリスクを評価します。堅牢性をテストするために複数の攻撃手法を適用します。また、詳細なモデル間比較機能も提供します。 |

<details>
<summary><strong>その他の特長</strong></summary>

- **モダンなWebインターフェース**: ワンクリックスキャンとリアルタイム進捗追跡を備えた使いやすいUI
- **完全なAPI**: 統合が容易なインターフェースドキュメントとSwagger仕様
- **多言語対応**: 中国語と英語のインターフェースおよびローカライズされたドキュメント
- **クロスプラットフォーム**: Dockerベースのデプロイメントにより、Linux、macOS、Windowsをサポート
- **無料＆オープンソース**: Apache 2.0ライセンスの下で完全無料
</details>

<br />


## スクリーンショット

### A.I.G メインインターフェース
![A.I.G メインページ](../img/aig.gif)

### プラグイン管理
![プラグイン管理](../img/plugin-gif.gif)

<br />


## 🗺️ クイック使用ガイド

> デプロイ完了後、ブラウザで `http://localhost:8088` を開いてください。

### AIインフラ脆弱性スキャン

**ターゲットURL / IPに何を入力するか？**

ターゲットは、スキャンしたい**実行中のAIサービスのネットワークアドレス**です（GitHubのURLやソースコードパスではありません）。A.I.Gはそのアドレスに接続してAIフレームワークのコンポーネントとバージョンを識別し、既知のCVE脆弱性と照合します。

| シナリオ | ターゲット例 |
|:--------|:-----------|
| ローカルで動作するvLLMインスタンス | `http://127.0.0.1:8000` |
| LAN上のOllamaサーバー | `http://192.168.1.100:11434` |
| 社内ComfyUIインスタンス | `http://10.0.0.5:8188` |
| 複数ホストの一括スキャン | `192.168.1.0/24`（CIDR）、`10.0.0.1-10.0.0.20`（IPレンジ） |

**ステップバイステップ：ローカルvLLMのスキャン**

1. 通常通りvLLMを起動（例：`python -m vllm.entrypoints.api_server --model ...`）
2. A.I.G UIで「**AIインフラ脆弱性スキャン**」をクリック
3. ターゲット欄に `http://127.0.0.1:8000`（vLLMが実際にリッスンしているIP/ポート）を入力
4. 「スキャン開始」をクリック — A.I.Gがコンポーネントバージョンを自動識別し、1000以上の既知CVEと照合
5. レポートを確認：コンポーネントバージョン、検出脆弱性、深刻度、および修復リンク

> 💡 **ヒント**：vLLMのnightlyビルドをスキャンする場合は、そのnightlyビルドを起動してアドレスを入力するだけです。スキャナーがバージョンを自動検出します。

### MCP Server & Agent Skills スキャン

ターゲット欄にリモートURL（例：`https://github.com/user/mcp-server`）を入力するか、**ローカルソースアーカイブをアップロード**してください。実行中のインスタンスは不要です。

### ジェイルブレイク評価

「**設定 → モデル設定**」でターゲットLLMのAPIエンドポイント（ベースURL＋APIキー）を設定し、データセットを選択して評価を開始してください。

---

## ユーザーガイド

オンラインドキュメントをご覧ください: [https://tencent.github.io/AI-Infra-Guard/](https://tencent.github.io/AI-Infra-Guard/)

より詳細なFAQやトラブルシューティングガイドについては、[ドキュメント](https://tencent.github.io/AI-Infra-Guard/?menu=faq)をご覧ください。
<br />
<br>

## APIドキュメント

A.I.Gは、AIインフラスキャン、MCPサーバースキャン、ジェイルブレイク評価をサポートする包括的なタスク作成APIセットを提供しています。

プロジェクト起動後、`http://localhost:8088/docs/index.html` にアクセスして完全なAPIドキュメントを閲覧できます。

詳細なAPIの使用方法、パラメータの説明、完全なサンプルコードについては、[完全なAPIドキュメント](../api_ja.md)を参照してください。
<br />
<br>

## コントリビューションガイド

拡張可能なプラグインフレームワークはA.I.Gのアーキテクチャの基盤であり、プラグインと機能の貢献を通じてコミュニティのイノベーションを促進します。

### プラグインコントリビューションルール
1. **フィンガープリントルール**: `data/fingerprints/`ディレクトリに新しいYAMLフィンガープリントファイルを追加してください。
2. **脆弱性ルール**: `data/vuln/`ディレクトリに新しい脆弱性スキャンルールを追加してください。
3. **MCPプラグイン**: `data/mcp/`ディレクトリに新しいMCPセキュリティスキャンルールを追加してください。
4. **ジェイルブレイク評価データセット**: `data/eval`ディレクトリに新しいジェイルブレイク評価データセットを追加してください。

既存のルール形式を参考にして新しいファイルを作成し、Pull Requestで提出してください。

### その他の貢献方法
- [バグを報告する](https://github.com/Tencent/AI-Infra-Guard/issues)
- [新機能を提案する](https://github.com/Tencent/AI-Infra-Guard/issues)
- [ドキュメントを改善する](https://github.com/Tencent/AI-Infra-Guard/pulls)
<br />
<br />

## 謝辞

### 学術連携

学術パートナーの皆様の優れた研究への貢献と技術サポートに心より感謝申し上げます。

#### <img src="../img/北大未来网络重点实验室2.png" height="30" align="middle"/>
<table>
  <tr>
    <td align="center" width="90">
      <a href="#">
        <img src="https://avatars.githubusercontent.com/u/0?v=4" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="#">
        <sub><b>Prof.&nbsp;hui&nbsp;Li</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/TheBinKing">
        <img src="https://avatars.githubusercontent.com/TheBinKing" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:1546697086@qq.com">
        <sub><b>Bin&nbsp;Wang</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/KPGhat">
        <img src="https://avatars.githubusercontent.com/KPGhat" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:kpghat@gmail.com">
        <sub><b>Zexin&nbsp;Liu</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/GioldDiorld">
        <img src="https://avatars.githubusercontent.com/GioldDiorld" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:g.diorld@gmail.com">
        <sub><b>Hao&nbsp;Yu</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/Jarvisni">
        <img src="https://avatars.githubusercontent.com/Jarvisni" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:719001405@qq.com">
        <sub><b>Ao&nbsp;Yang</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/Zhengxi7">
        <img src="https://avatars.githubusercontent.com/Zhengxi7" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:linzhengxi7@126.com">
        <sub><b>Zhengxi&nbsp;Lin</b></sub>
      </a>
    </td>
  </tr>
</table>

#### <img src="../img/复旦大学2.png" height="30" align="middle" style="vertical-align: middle;"/>

<table>
  <tr>
    <td align="center" width="120">
      <a href="https://yangzhemin.github.io/">
        <img src="https://avatars.githubusercontent.com/yangzhemin" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:yangzhemin@fudan.edu.cn">
        <sub><b>Prof.&nbsp;Zhemin&nbsp;Yang</b></sub>
      </a>
    </td>
    <td align="center" width="100">
      <a href="https://github.com/kangwei-zhong">
        <img src="https://avatars.githubusercontent.com/kangwei-zhong" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:kwzhong23@m.fudan.edu.cn">
        <sub><b>Kangwei&nbsp;Zhong</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/MoonBirdLin">
        <img src="https://avatars.githubusercontent.com/MoonBirdLin" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:linjp23@m.fudan.edu.cn">
        <sub><b>Jiapeng&nbsp;Lin</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://vanilla-tiramisu.github.io/">
        <img src="https://avatars.githubusercontent.com/vanilla-tiramisu" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:csheng25@m.fudan.edu.cn">
        <sub><b>Cheng&nbsp;Sheng</b></sub>
      </a>
    </td>
  </tr>
</table>
<br>

### 貢献開発者への感謝
A.I.Gプロジェクトに貢献してくださったすべての開発者に感謝いたします。皆様の貢献がA.I.Gをより堅牢で信頼性の高いAIレッドチームプラットフォームにするために不可欠でした。
<br />
<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td width="33%"><img src="../img/keen_lab_logo.svg" alt="Keen Lab" height="85%"></td>
    <td width="33%"><img src="../img/wechat_security.png" alt="WeChat Security" height="85%"></td>
    <td width="33%"><img src="../img/fit_sec_logo.png" alt="Fit Security" height="85%"></td>
  </tr>
</table>
<a href="https://github.com/Tencent/AI-Infra-Guard/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Tencent/AI-Infra-Guard" />
</a>
<br>
<br>

### ユーザーの皆様への感謝

A.I.Gをご利用いただき、信頼と貴重なフィードバックをお寄せくださった以下のチームおよび組織に深く感謝いたします。

<br>
<div align="center">
<img src="../img/tencent.png" alt="Tencent" height="30px">
<img src="../img/deepseek.png" alt="DeepSeek" height="38px">
<img src="../img/antintl.svg" alt="Antintl" height="45px">
</div>

<br>
<br>

## コミュニティに参加

### オンラインディスカッション
- **GitHub Discussions**: [コミュニティディスカッションに参加](https://github.com/Tencent/AI-Infra-Guard/discussions)
- **Issue＆バグ報告**: [Issueの報告または機能の提案](https://github.com/Tencent/AI-Infra-Guard/issues)

### ディスカッションコミュニティ
<table>
  <thead>
  <tr>
    <th>WeChatグループ</th>
    <th>Discord <a href="https://discord.gg/U9dnPnyadZ">[リンク]</a></th>
  </tr>
  </thead>
  <tbody>
  <tr>
    <td><img src="../img/wechatgroup.png" alt="WeChat Group" width="200"></td>
    <td><img src="../img/discord.png" alt="discord" width="200"></td>
  </tr>
  </tbody>
</table>

### お問い合わせ
コラボレーションのお問い合わせやフィードバックについては、以下までご連絡ください: [zhuque@tencent.com](mailto:zhuque@tencent.com)

### おすすめセキュリティツール
コードセキュリティに興味がある方は、Tencent Wukong Code Security Teamがオープンソース化した業界初のリポジトリレベルAI生成コードセキュリティ評価フレームワーク [A.S.E (AICGSecEval)](https://github.com/Tencent/AICGSecEval) をご覧ください。




<br>
<br>

## 引用

研究でA.I.Gを使用する場合は、以下を引用してください：

```bibtex
@misc{Tencent_AI-Infra-Guard_2025,
  author={{Tencent Zhuque Lab}},
  title={{AI-Infra-Guard: A Comprehensive, Intelligent, and Easy-to-Use AI Red Teaming Platform}},
  year={2025},
  howpublished={GitHub repository},
  url={https://github.com/Tencent/AI-Infra-Guard}
}
```
<br>

## 関連論文

<details>
<summary>A.I.Gを学術研究に活用し、AIセキュリティ研究の発展に貢献してくださった研究チームの皆様に深く感謝いたします。クリックして展開（17本）</summary>
<br>

1. Naen Xu, Jinghuai Zhang, Ping He et al. **"FraudShield: Knowledge Graph Empowered Defense for LLMs against Fraud Attacks."** arXiv preprint arXiv:2601.22485v1 (2026). [[pdf]](http://arxiv.org/abs/2601.22485v1)

2. Ruiqi Li, Zhiqiang Wang, Yunhao Yao et al. **"MCP-ITP: An Automated Framework for Implicit Tool Poisoning in MCP."** arXiv preprint arXiv:2601.07395v1 (2026). [[pdf]](http://arxiv.org/abs/2601.07395v1)

3. Jingxiao Yang, Ping He, Tianyu Du et al. **"HogVul: Black-box Adversarial Code Generation Framework Against LM-based Vulnerability Detectors."** arXiv preprint arXiv:2601.05587v1 (2026). [[pdf]](http://arxiv.org/abs/2601.05587v1)

4. Yunyi Zhang, Shibo Cui, Baojun Liu et al. **"Beyond Jailbreak: Unveiling Risks in LLM Applications Arising from Blurred Capability Boundaries."** arXiv preprint arXiv:2511.17874v2 (2025). [[pdf]](http://arxiv.org/abs/2511.17874v2)

5. Teofil Bodea, Masanori Misono, Julian Pritzi et al. **"Trusted AI Agents in the Cloud."** arXiv preprint arXiv:2512.05951v1 (2025). [[pdf]](http://arxiv.org/abs/2512.05951v1)

6. Christian Coleman. **"Behavioral Detection Methods for Automated MCP Server Vulnerability Assessment."** [[pdf]](https://digitalcommons.odu.edu/cgi/viewcontent.cgi?article=1138&context=covacci-undergraduateresearch)

7. Bin Wang, Zexin Liu, Hao Yu et al. **"MCPGuard: Automatically Detecting Vulnerabilities in MCP Servers."** arXiv preprint arXiv:2510.23673v1 (2025). [[pdf]](http://arxiv.org/abs/2510.23673v1)

8. Weibo Zhao, Jiahao Liu, Bonan Ruan et al. **"When MCP Servers Attack: Taxonomy, Feasibility, and Mitigation."** arXiv preprint arXiv:2509.24272v1 (2025). [[pdf]](http://arxiv.org/abs/2509.24272v1)

9. Ping He, Changjiang Li, et al. **"Automatic Red Teaming LLM-based Agents with Model Context Protocol Tools."** arXiv preprint arXiv:2509.21011 (2025). [[pdf]](https://arxiv.org/abs/2509.21011)

10. Yixuan Yang, Daoyuan Wu, Yufan Chen. **"MCPSecBench: A Systematic Security Benchmark and Playground for Testing Model Context Protocols."** arXiv preprint arXiv:2508.13220 (2025). [[pdf]](https://arxiv.org/abs/2508.13220)

11. Zexin Wang, Jingjing Li, et al. **"A Survey on AgentOps: Categorization, Challenges, and Future Directions."** arXiv preprint arXiv:2508.02121 (2025). [[pdf]](https://arxiv.org/abs/2508.02121)

12. Yongjian Guo, Puzhuo Liu, et al. **"Systematic Analysis of MCP Security."** arXiv preprint arXiv:2508.12538 (2025). [[pdf]](https://arxiv.org/abs/2508.12538)

13. Yuepeng Hu, Yuqi Jia, Mengyuan Li et al. **"MalTool: Malicious Tool Attacks on LLM Agents."** arXiv preprint arXiv:2602.12194 (2026). [[pdf]](https://arxiv.org/abs/2602.12194)

14. Yi Ting Shen, Kentaroh Toyoda, Alex Leung. **"MCP-38: A Comprehensive Threat Taxonomy for Model Context Protocol Systems (v1.0)."** arXiv preprint arXiv:2603.18063 (2026). [[pdf]](https://arxiv.org/abs/2603.18063)

15. Yiheng Huang, Zhijia Zhao, Bihuan Chen et al. **"From Component Manipulation to System Compromise: Understanding and Detecting Malicious MCP Servers."** arXiv preprint arXiv:2604.01905 (2026). [[pdf]](https://arxiv.org/abs/2604.01905)

16. Hengkai Ye, Zhechang Zhang, Jinyuan Jia et al. **"TRUSTDESC: Preventing Tool Poisoning in LLM Applications via Trusted Description Generation."** arXiv preprint arXiv:2604.07536 (2026). [[pdf]](https://arxiv.org/abs/2604.07536)

17. Zenghao Duan, Yuxin Tian, Zhiyi Yin et al. **"SkillAttack: Automated Red Teaming of Agent Skills through Attack Path Refinement."** arXiv preprint arXiv:2604.04989 (2026). [[pdf]](https://arxiv.org/abs/2604.04989)


</details>

A.I.Gを研究や製品にご使用いただいた方、または掲載漏れがございましたら、ぜひお知らせください！[こちらからご連絡ください](#-コミュニティに参加)。
<br>
<br>

## ライセンスと帰属表示

本プロジェクトは **Apache License 2.0** に基づきオープンソース化されています。コミュニティからの貢献、統合、および派生作品を歓迎しますが、以下の帰属表示要件に従う必要があります：

1. **通知の保持**: 配布物には、元のプロジェクトの`LICENSE`および`NOTICE`ファイルを保持する必要があります。
2. **製品への帰属表示**: AI-Infra-Guardのコアコード、コンポーネント、またはスキャンエンジンをオープンソースプロジェクト、商用製品、または社内プラットフォームに統合する場合、**製品ドキュメント、使用ガイド、またはUIの「About」ページ**に以下を明記する必要があります：
   > 「本プロジェクトはTencent Zhuque Labによりオープンソース化された[AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard)を統合しています。」
3. **学術・記事での引用**: 脆弱性分析レポート、セキュリティ研究記事、または学術論文でこのツールを使用する場合、「Tencent Zhuque Lab AI-Infra-Guard」を明示的に言及し、リポジトリへのリンクを含めてください。

出所を開示せずに本プロジェクトをオリジナル製品として再パッケージすることは固く禁じられています。

<div>

[![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)
</content>
</invoke>
