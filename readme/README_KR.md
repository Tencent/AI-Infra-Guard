<p align="center">
    <h1 align="center"><img vertical-align="middle" width="400px" src="../img/logo-full-new.png" alt="A.I.G"/></h1>
</p>
<h4 align="center">
    <p>
        <a href="https://tencent.github.io/AI-Infra-Guard/">문서</a> |
        <a href="../README.md">English</a> |
        <a href="./README_ZH.md">中文</a> |
        <a href="./README_JA.md">日本語</a> |
        <a href="./README_ES.md">Español</a> |
        <a href="./README_DE.md">Deutsch</a> |
        <a href="./README_FR.md">Français</a> |
        <a href="./README_PT.md">Português</a> |
        <a href="./README_RU.md">Русский</a>
    <p>
</h4>
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
    <h2 align="center">🚀 Tencent Zhuque Lab의 AI 레드팀 플랫폼</h2>
</p>

**A.I.G (AI-Infra-Guard)**는 ClawScan(OpenClaw Security Scan), Agent Scan, AI 인프라 취약점 scan, MCP Server & Agent Skills scan, Jailbreak Evaluation 등의 기능을 통합하여, 사용자에게 가장 포괄적이고 지능적이며 사용하기 편리한 AI 보안 위험 자가 점검 솔루션을 제공하는 것을 목표로 합니다.

<p>
  저희는 A.I.G(AI-Infra-Guard)를 업계 선도적인 AI 레드팀 플랫폼으로 만들기 위해 노력하고 있습니다. 더 많은 스타는 이 프로젝트가 더 넓은 범위의 사용자에게 도달하도록 도와주며, 더 많은 개발자들이 기여하도록 유도하여 반복 개선을 가속화합니다. 여러분의 스타는 저희에게 매우 소중합니다!
</p>
<p align="center">
  <a href="https://github.com/Tencent/AI-Infra-Guard">
      <img src="https://img.shields.io/badge/⭐-Give%20us%20a%20Star-yellow?style=for-the-badge&logo=github" alt="Give us a Star">
  </a>
</p>

<br>

## 🚀 새로운 소식

- **2026-04-09** · [v4.1.3](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1.3) — AI 컴포넌트 커버리지가 55개로 확장되었습니다. crewai, kubeai, lobehub가 추가되었습니다.
- **2026-04-03** · [v4.1.2](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1.2) — ClawHub에 3개의 신규 skill 추가(`edgeone-clawscan`, `edgeone-skill-scanner`, `aig-scanner`) 및 수동 작업 중지 기능이 추가되었습니다.
- **2026-03-25** · [v4.1.1](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1.1) — ☠️ LiteLLM 공급망 공격(CRITICAL) 탐지 기능 추가; Blinko 및 New-API 커버리지가 추가되었습니다.
- **2026-03-23** · [v4.1](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1) — OpenClaw 취약점 데이터베이스에 281개의 신규 CVE/GHSA 항목이 추가되어 확장되었습니다.
- **2026-03-10** · [v4.0](https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.0) — EdgeOne ClawScan(OpenClaw Security Scan) 및 Agent-Scan 프레임워크가 출시되었습니다.

👉 [CHANGELOG](../CHANGELOG.md) · 🩺 [EdgeOne ClawScan 체험하기](https://matrix.tencent.com/clawscan)


## 목차
- [🚀 빠른 시작](#-빠른-시작)
- [✨ 주요 기능](#-주요-기능)
- [🖼️ 스크린샷](#-스크린샷)
- [📖 사용자 가이드](#-사용자-가이드)
- [🔧 API 문서](#-api-문서)
- [📝 기여 가이드](#-기여-가이드)
- [🙏 감사의 말씀](#-감사의-말씀)
- [💬 커뮤니티 참여](#-커뮤니티-참여)
- [📖 인용](#-인용)
- [📚 관련 논문](#-관련-논문)
- [📄 라이선스](#-라이선스)
- [⚖️ 라이선스 및 저작권 표시](#️-라이선스-및-저작권-표시)
<br><br>
## 🚀 빠른 시작
### Docker를 이용한 배포

| Docker | RAM | 디스크 공간 |
|:-------|:----|:----------|
| 20.10 이상 | 4GB 이상 | 10GB 이상 |

```bash
# 이 방법은 Docker Hub에서 사전 빌드된 이미지를 가져와 빠르게 시작합니다
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
# Docker Compose V2 이상의 경우 'docker-compose'를 'docker compose'로 교체하세요
docker-compose -f docker-compose.images.yml up -d
```

서비스가 실행되면 다음 주소에서 A.I.G 웹 인터페이스에 접속할 수 있습니다:
`http://localhost:8088`
<br>

### OpenClaw에서 사용하기

OpenClaw 채팅에서 `aig-scanner` skill을 통해 A.I.G를 직접 호출할 수도 있습니다.

```bash
clawhub install aig-scanner
```

그런 다음 `AIG_BASE_URL`을 실행 중인 A.I.G 서비스 주소로 설정하세요.

자세한 내용은 [`aig-scanner` README](../skills/aig-scanner/README.md)를 참조하세요.

<details>
<summary><strong>📦 추가 설치 옵션</strong></summary>

### 기타 설치 방법

**방법 2: 원클릭 설치 스크립트（권장）**
```bash
# 이 방법은 Docker를 자동으로 설치하고 A.I.G를 한 번의 명령으로 실행합니다  
curl https://raw.githubusercontent.com/Tencent/AI-Infra-Guard/refs/heads/main/docker.sh | bash
```

**방법 3: 소스 코드로 빌드 및 실행**
```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
# 이 방법은 로컬 소스 코드에서 Docker 이미지를 빌드하고 서비스를 시작합니다
# (Docker Compose V2 이상의 경우 'docker-compose'를 'docker compose'로 교체하세요)
docker-compose up -d
```

참고: AI-Infra-Guard 프로젝트는 기업 또는 개인의 내부 사용을 위한 AI 레드팀 플랫폼으로 포지셔닝되어 있습니다. 현재 인증 메커니즘이 없으므로 공개 네트워크에 배포해서는 안 됩니다.

자세한 내용은 다음을 참조하세요: [https://tencent.github.io/AI-Infra-Guard/?menu=getting-started](https://tencent.github.io/AI-Infra-Guard/?menu=getting-started)

</details>

### 온라인 Pro 버전 체험하기
고급 기능과 향상된 성능을 갖춘 Pro 버전을 경험해 보세요. Pro 버전은 초대 코드가 필요하며, 이슈·풀 리퀘스트·토론을 제출했거나 커뮤니티 성장에 적극적으로 기여한 분들을 우선적으로 제공합니다. 방문: [https://aigsec.ai/](https://aigsec.ai/).
<br>
<br>

## ✨ 주요 기능

| 기능 | 상세 정보 |
|:--------|:------------|
| **ClawScan(OpenClaw&nbsp;Security&nbsp;Scan)** | OpenClaw 보안 위험에 대한 원클릭 평가를 지원합니다. 안전하지 않은 설정, Skill 위험, CVE 취약점 및 개인정보 유출을 탐지합니다. |
| **Agent&nbsp;Scan** | AI Agent 워크플로우의 보안을 평가하도록 설계된 독립적인 다중 Agent 자동화 scan 프레임워크입니다. Dify 및 Coze를 포함한 다양한 플랫폼에서 실행되는 Agent를 원활하게 지원합니다. |
| **MCP&nbsp;Server&nbsp;&&nbsp;Agent&nbsp;Skills&nbsp;scan** | 14가지 주요 보안 위험 카테고리를 철저히 탐지합니다. MCP Server와 Agent Skills 모두에 적용됩니다. 소스 코드와 원격 URL 모두에서 유연하게 scan을 지원합니다. |
| **AI&nbsp;인프라&nbsp;취약점&nbsp;scan** | 55개 이상의 AI 프레임워크 컴포넌트를 정확하게 식별합니다. 1,000개 이상의 알려진 CVE 취약점을 커버합니다. Ollama, ComfyUI, vLLM, n8n, Triton Inference Server 등의 프레임워크를 지원합니다. |
| **Jailbreak&nbsp;Evaluation** | 엄선된 데이터셋을 사용하여 prompt 보안 위험을 평가합니다. 다양한 공격 방법을 적용하여 견고성을 테스트합니다. 상세한 모델 간 비교 기능도 제공합니다. |

<details>
<summary><strong>💎 추가 혜택</strong></summary>

- 🖥️ **현대적인 웹 인터페이스**: 원클릭 scan 및 실시간 진행 상황 추적이 가능한 사용자 친화적 UI
- 🔌 **완전한 API**: 쉬운 통합을 위한 전체 인터페이스 문서 및 Swagger 사양
- 🌐 **다국어 지원**: 현지화된 문서와 함께 중국어 및 영어 인터페이스 제공
- 🐳 **크로스 플랫폼**: Docker 기반 배포로 Linux, macOS 및 Windows 지원
- 🆓 **무료 오픈소스**: Apache 2.0 라이선스 하에 완전 무료
</details>

<br />


## 🖼️ 스크린샷

### A.I.G 메인 인터페이스
![A.I.G Main Page](../img/aig.gif)

### 플러그인 관리
![Plugin Management](../img/plugin-gif.gif)

<br />


## 🗺️ 빠른 사용 가이드

> 배포 후 브라우저에서 `http://localhost:8088`을 엽니다.

### AI 인프라 취약점 Scan

**대상 URL / IP에 무엇을 입력해야 하나요?**

대상은 GitHub URL이나 소스 코드 경로가 아니라, scan하려는 **실행 중인 AI 서비스의 네트워크 주소**입니다. A.I.G는 라이브 서비스에 연결하여 알려진 CVE 취약점에 대한 지문을 채취합니다.

| 시나리오 | 예시 대상 |
|:---------|:--------------|
| 로컬에서 실행 중인 vLLM 인스턴스 | `http://127.0.0.1:8000` |
| LAN의 Ollama 서버 | `http://192.168.1.100:11434` |
| 내부적으로 노출된 ComfyUI 인스턴스 | `http://10.0.0.5:8188` |
| 여러 호스트 (한 줄에 하나씩) | `192.168.1.0/24` (CIDR), `10.0.0.1-10.0.0.20` (범위) |

**단계별 가이드: 로컬 vLLM 인스턴스 Scan**

1. vLLM을 정상적으로 시작합니다 (예: `python -m vllm.entrypoints.api_server --model meta-llama/...`)
2. A.I.G 웹 UI에서 **"AI基础设施安全扫描 / AI Infra Scan"**을 클릭합니다.
3. `http://127.0.0.1:8000`을 입력합니다 (또는 vLLM이 수신 대기 중인 IP/포트)
4. **Start Scan**을 클릭합니다 — A.I.G가 서비스의 지문을 채취하여 1,000개 이상의 알려진 CVE와 매칭합니다.
5. 보고서를 확인합니다: 컴포넌트 버전, 매칭된 취약점, 심각도 및 수정 링크

> 💡 **팁**: 특별히 vLLM의 *nightly* 빌드를 scan하려면 해당 nightly 빌드를 실행하고 A.I.G가 그 주소를 가리키도록 하세요. scanner가 버전을 자동으로 탐지합니다.

### MCP Server & Agent Skills Scan

**원격 URL** (예: `https://github.com/user/mcp-server`)을 입력하거나 **로컬 소스 아카이브를 업로드**하세요 — 실행 중인 인스턴스가 필요 없습니다.

### Jailbreak Evaluation

**설정 → 모델 설정**에서 대상 LLM의 API 엔드포인트(기본 URL + API 키)를 구성한 다음, 데이터셋을 선택하고 평가를 시작합니다.

---

## 📖 사용자 가이드

온라인 문서를 방문하세요: [https://tencent.github.io/AI-Infra-Guard/](https://tencent.github.io/AI-Infra-Guard/)

더 자세한 FAQ 및 문제 해결 가이드는 [문서](https://tencent.github.io/AI-Infra-Guard/?menu=faq)를 방문하세요.
<br />
<br>

## 🔧 API 문서

A.I.G는 AI 인프라 scan, MCP Server Scan 및 Jailbreak Evaluation 기능을 지원하는 포괄적인 작업 생성 API 세트를 제공합니다.

프로젝트 실행 후 `http://localhost:8088/docs/index.html`을 방문하여 전체 API 문서를 확인하세요.

자세한 API 사용 지침, 파라미터 설명 및 전체 예제 코드는 [전체 API 문서](../api.md)를 참조하세요.
<br />
<br>

## 📝 기여 가이드

확장 가능한 플러그인 프레임워크는 A.I.G의 아키텍처 핵심으로, 플러그인 및 기능 기여를 통한 커뮤니티 혁신을 환영합니다.

### 플러그인 기여 규칙
1.  **지문 규칙**: `data/fingerprints/` 디렉토리에 새로운 YAML 지문 파일을 추가하세요.
2.  **취약점 규칙**: `data/vuln/` 디렉토리에 새로운 취약점 scan 규칙을 추가하세요.
3.  **MCP 플러그인**: `data/mcp/` 디렉토리에 새로운 MCP 보안 scan 규칙을 추가하세요.
4.  **Jailbreak Evaluation 데이터셋**: `data/eval` 디렉토리에 새로운 Jailbreak 평가 데이터셋을 추가하세요.

기존 규칙 형식을 참고하여 새 파일을 만들고 Pull Request를 통해 제출해 주세요.

### 기타 기여 방법
- 🐛 [버그 신고](https://github.com/Tencent/AI-Infra-Guard/issues)
- 💡 [새로운 기능 제안](https://github.com/Tencent/AI-Infra-Guard/issues)
- ⭐ [문서 개선](https://github.com/Tencent/AI-Infra-Guard/pulls)
<br />
<br />

## 🙏 감사의 말씀

### 🎓 학술 협력

탁월한 연구 기여와 기술 지원을 제공해 주신 학술 파트너들에게 진심으로 감사드립니다.

#### <img src="../img/북대미래네트워크중점실험실2.png" height="30" align="middle"/>
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

#### <img src="../img/복단대학2.png" height="30" align="middle" style="vertical-align: middle;"/>

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

### 👥 기여해 주신 개발자분들께 감사드립니다
A.I.G 프로젝트에 기여해 주신 모든 개발자분들께 감사드립니다. 여러분의 기여는 A.I.G를 더욱 견고하고 신뢰할 수 있는 AI 레드팀 플랫폼으로 만드는 데 핵심적인 역할을 해왔습니다.
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

### 🤝 사용자 여러분께 감사드립니다

A.I.G를 사용하고 신뢰해 주시며 소중한 피드백을 제공해 주신 다음 팀과 조직에 깊이 감사드립니다.

<br>
<div align="center">
<img src="../img/tencent.png" alt="Tencent" height="30px">
<img src="../img/deepseek.png" alt="DeepSeek" height="38px">
<img src="../img/antintl.svg" alt="Antintl" height="45px">
</div>

<br>
<br>

## 💬 커뮤니티 참여

### 🌐 온라인 토론
- **GitHub Discussions**: [커뮤니티 토론에 참여하기](https://github.com/Tencent/AI-Infra-Guard/discussions)
- **이슈 및 버그 신고**: [이슈 신고 또는 기능 제안](https://github.com/Tencent/AI-Infra-Guard/issues)

### 📱 토론 커뮤니티
<table>
  <thead>
  <tr>
    <th>WeChat 그룹</th>
    <th>Discord <a href="https://discord.gg/U9dnPnyadZ">[링크]</a></th>
  </tr>
  </thead>
  <tbody>
  <tr>
    <td><img src="../img/wechatgroup.png" alt="WeChat Group" width="200"></td>
    <td><img src="../img/discord.png" alt="discord" width="200"></td>
  </tr>
  </tbody>
</table>

### 📧 문의하기
협력 문의 또는 피드백은 다음 이메일로 연락해 주세요: [zhuque@tencent.com](mailto:zhuque@tencent.com)

### 🔗 추천 보안 도구
코드 보안에 관심이 있으시다면 [A.S.E (AICGSecEval)](https://github.com/Tencent/AICGSecEval)을 확인해 보세요. 이는 Tencent 悟空 코드 보안 팀이 오픈소스로 공개한 업계 최초의 저장소 수준 AI 생성 코드 보안 평가 프레임워크입니다.




<br>
<br>

## 📖 인용

연구에서 A.I.G를 사용하신 경우 다음과 같이 인용해 주세요:

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

## 📚 관련 논문

학술 연구에서 A.I.G를 사용하여 AI 보안 연구 발전에 기여해 주신 연구팀들에게 깊이 감사드립니다:

[1] Naen Xu, Jinghuai Zhang, Ping He et al. **"FraudShield: Knowledge Graph Empowered Defense for LLMs against Fraud Attacks."** arXiv preprint arXiv:2601.22485v1 (2026). [[pdf]](http://arxiv.org/abs/2601.22485v1)  
[2] Ruiqi Li, Zhiqiang Wang, Yunhao Yao et al. **"MCP-ITP: An Automated Framework for Implicit Tool Poisoning in MCP."** arXiv preprint arXiv:2601.07395v1 (2026). [[pdf]](http://arxiv.org/abs/2601.07395v1)  
[3] Jingxiao Yang, Ping He, Tianyu Du et al. **"HogVul: Black-box Adversarial Code Generation Framework Against LM-based Vulnerability Detectors."** arXiv preprint arXiv:2601.05587v1 (2026). [[pdf]](http://arxiv.org/abs/2601.05587v1)  
[4] Yunyi Zhang, Shibo Cui, Baojun Liu et al. **"Beyond Jailbreak: Unveiling Risks in LLM Applications Arising from Blurred Capability Boundaries."** arXiv preprint arXiv:2511.17874v2 (2025). [[pdf]](http://arxiv.org/abs/2511.17874v2)  
[5] Teofil Bodea, Masanori Misono, Julian Pritzi et al. **"Trusted AI Agents in the Cloud."** arXiv preprint arXiv:2512.05951v1 (2025). [[pdf]](http://arxiv.org/abs/2512.05951v1)  
[6] Christian Coleman. **"Behavioral Detection Methods for Automated MCP Server Vulnerability Assessment."** [[pdf]](https://digitalcommons.odu.edu/cgi/viewcontent.cgi?article=1138&context=covacci-undergraduateresearch)  
[7] Bin Wang, Zexin Liu, Hao Yu et al. **"MCPGuard : Automatically Detecting Vulnerabilities in MCP Servers."** arXiv preprint arXiv:22510.23673v1 (2025). [[pdf]](http://arxiv.org/abs/2510.23673v1)  
[8] Weibo Zhao, Jiahao Liu, Bonan Ruan et al. **"When MCP Servers Attack: Taxonomy, Feasibility, and Mitigation."** arXiv preprint arXiv:2509.24272v1 (2025). [[pdf]](http://arxiv.org/abs/2509.24272v1)  
[9] Ping He, Changjiang Li, et al. **"Automatic Red Teaming LLM-based Agents with Model Context Protocol Tools."** arXiv preprint arXiv:2509.21011 (2025). [[pdf]](https://arxiv.org/abs/2509.21011)  
[10] Yixuan Yang, Daoyuan Wu, Yufan Chen. **"MCPSecBench: A Systematic Security Benchmark and Playground for Testing Model Context Protocols."** arXiv preprint arXiv:2508.13220 (2025). [[pdf]](https://arxiv.org/abs/2508.13220)  
[11] Zexin Wang, Jingjing Li, et al. **"A Survey on AgentOps: Categorization, Challenges, and Future Directions."** arXiv preprint arXiv:2508.02121 (2025). [[pdf]](https://arxiv.org/abs/2508.02121)  
[12] Yongjian Guo, Puzhuo Liu, et al. **"Systematic Analysis of MCP Security."** arXiv preprint arXiv:2508.12538 (2025). [[pdf]](https://arxiv.org/abs/2508.12538)  

📧 연구나 제품에서 A.I.G를 사용하셨거나, 저희가 실수로 귀하의 출판물을 누락했다면 연락 주시기 바랍니다! [문의하기](#-커뮤니티-참여).
<br>
<br>

## 📄 라이선스

이 프로젝트는 **Apache License 2.0** 하에 라이선스가 부여됩니다. 자세한 내용은 [LICENSE](../LICENSE) 파일을 참조하세요.

## ⚖️ 라이선스 및 저작권 표시

이 프로젝트는 **Apache License 2.0** 하에 오픈소스로 공개됩니다. 다음 저작권 표시 요건에 따라 커뮤니티 기여, 통합 및 파생 작업을 적극 환영합니다:

1. **고지 사항 유지**: 배포 시 원본 프로젝트의 `LICENSE` 및 `NOTICE` 파일을 반드시 유지해야 합니다.
2. **제품 저작권 표시**: AI-Infra-Guard의 핵심 코드, 컴포넌트 또는 scan 엔진을 오픈소스 프로젝트, 상업용 제품 또는 내부 플랫폼에 통합하는 경우, **제품 문서, 사용 가이드 또는 UI "정보" 페이지**에 다음을 명확히 기재해야 합니다:
   > "This project integrates [AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard), open-sourced by Tencent Zhuque Lab."
3. **학술 및 기사 인용**: 취약점 분석 보고서, 보안 연구 기사 또는 학술 논문에서 이 도구를 사용하는 경우 "Tencent Zhuque Lab AI-Infra-Guard"를 명시적으로 언급하고 저장소 링크를 포함해 주세요.

출처를 밝히지 않고 이 프로젝트를 독자적인 제품으로 재포장하는 것은 엄격히 금지됩니다.

<div>

[![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)
</div>
