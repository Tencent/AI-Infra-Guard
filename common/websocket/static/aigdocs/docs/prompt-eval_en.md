# Jailbreak Evaluation

## Introduction

Jailbreak Evaluation provides simple, easy-to-use, efficient, and comprehensive security risk detection for large language models. Users can identify security issues with one click, helping developers efficiently recognize and fix security risks.

The platform includes typical risk prompts curated by Tencent Zhuque Lab through large-scale data cleaning, synthesis, generalization, and semantic deduplication. It supports over a hundred attack methods to dynamically enhance risk prompts. Developers can either use the built-in 'Jailbreak Evaluation' to evaluate models or utilize the custom evaluation set feature to further generalize and enhance internal risk prompt cases using the attack methods provided by Zhuque.

## Quick Start

### Three Steps to Complete
![Jailbreak Evaluation Main Interface](./assets/image-prompt-eval-pro_en.png)
1. **Select Task Type**: Click "Jailbreak Evaluation" below the dialog box.
2. **Configure Model, Dataset, and Attack Methods**:
   - Select/configure the model to be tested (see [Model Configuration](#1-model-configuration)).
   - Choose built-in datasets (see [Dataset Selection](#2-dataset-selection)) or upload custom datasets (see [Custom Dataset Management](#3-custom-dataset-management)).
   - Select attack methods (see [Attack Methods Introduction](#4-attack-methods-introduction)) or test with original prompts only.
3. **Start Task and View Report**: Click the button, wait for task completion, and view detailed results report.

## Detailed Configuration Introduction

### 1. Model Configuration

- **Supported Model Types**: Models compatible with OpenAI API format
- **Configuration Parameters**:
  - Model name, e.g.: `openai/gpt-4o`
  - API base URL, e.g.: `https://openrouter.ai/api/v1`
  - API key

### 2. Dataset Selection
- Built-in curated security test datasets covering important security scenarios;
- Support for using custom datasets (see [Custom Dataset Management](#3-custom-dataset-management));
- Automatic task execution time estimation for better test planning;

![Dataset Selection](./assets/img-prompt-select-dataset-v1.0_en.png)

**Health Check Execution:**
- Support for single-model or multi-model health checks
- Automatic generation of detailed security scores and risk reports
- Provides cross-model security performance comparative analysis

**Report Display:**
- Visual presentation of health check results, including success/failure rates, risk analysis, etc.
- Model security rating: High, Medium, Low
- Support for full data result export

![Model Health Check Detailed Report](./assets/image-prompt-eval-report-case_en.png)


### 3. Custom Dataset Management

The system supports two ways to use custom datasets:

**Temporary Upload:**
- Temporarily upload during health check task execution, not saved after task completion
- Compatible with mainstream formats (CSV, JSON, JSONL, Excel, Parquet, TXT)
- Automatic recognition of common prompt column names (such as prompt, question, query, text, content, etc.)

> Note: Future versions will support user-defined column name configuration

**Dataset Management:**
- Permanently saved to the system through management page, supporting reuse and sharing
- Requires standard JSON format to ensure data quality and consistency

![Dataset Management Interface](./assets/image-prompt-eval-datasets_en.png)

> Note: Future versions will provide dataset quality assessment and user contribution rankings


### 4. Attack Methods Introduction

The system includes a rich library of attack methods that support dynamic enhancement of risk prompts, helping developers comprehensively test model security protection capabilities. The current version provides two major categories of attack strategies, totaling over a hundred specific attack methods.

- **[Encoding Attacks](/help?menu=prompt-eval_method_Encoding_en)**: Encoding attack strategies encrypt risk prompts through various encoding and obfuscation methods to bypass model safety guardrails.
- **[Behavioral Control Attacks](/help?menu=prompt-eval_methpd_BehavioralControl_en)**: Behavioral control attack strategies control model behavior through context guidance, redirection, or deception to bypass security restrictions.

![Operator Configuration Interface](./assets/image-prompt-eval-attack-method_en.png)

> These attack methods can be used individually or in combination, providing developers with comprehensive model security testing capabilities. The platform will continuously update and expand the attack method library to address evolving security threats.

## 🙏 Acknowledgements

The development of this project relies on the following excellent open-source projects, for which we express our gratitude.

### Framework Support
This project is built and deeply customized based on the **[DeepTeam](https://github.com/DeepTeam/DeepTeam)** project from the **[Confident AI](http://www.confident-ai.com)** team.
- **Original Repository**: [https://github.com/DeepTeam/DeepTeam](https://github.com/DeepTeam/DeepTeam)
- **Original Project License**: Please refer to the `LICENSE` file in their repository.
- **Note**: We sincerely thank the Confident AI team for providing an excellent foundational framework. To better adapt and serve our own business architecture and specific requirements, we have made extensive modifications, extensions, and refactoring to achieve specialized adaptation and integration with the **[AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard)** ecosystem, enabling seamless out-of-the-box integration.

### Attack Operator Contributions
We express our sincere gratitude to the research teams and communities that contributed to the development of various attack techniques and operators used in this project:

| Operator Name | Source Team | Link |
|---------|--------|------|
| Some single-round and multi-round operators | Confident AI Inc. | [Github](https://github.com/DeepTeam/DeepTeam) |
| SequentialBreak | Saiem et al. | [Paper](https://arxiv.org/abs/2411.06426) |
| Best of N | Hughes et al. | [Paper](https://arxiv.org/abs/2412.03556) |
| ICRT Jailbreak | Yang et al. | [Paper](https://arxiv.org/abs/2505.02862) |
| Strata-Sword | Alibaba AAIG | [Paper](https://arxiv.org/abs/2509.01444) |
| PROMISQROUTE | Adversa AI | [Blog](https://adversa.ai/blog/promisqroute-gpt-5-ai-router-novel-vulnerability-class/) |

### Dataset Contributions
We express our sincere gratitude to the research teams and communities that contributed to the various datasets used in this project:
| Dataset Name | Source Team | Link |
|-----------|---------|-----|
| JailBench | STAIR | [Github](https://github.com/STAIR-BUPT/JailBench)|
| redteam-deepseek | Promptfoo | [Github](https://github.com/promptfoo/promptfoo/blob/main/examples/redteam-deepseek/tests.csv) |
| ChatGPT-Jailbreak-Prompts | Rubén Darío Jaramillo | [HuggingFace](https://huggingface.co/datasets/rubend18/ChatGPT-Jailbreak-Prompts) |
| JBB-Behaviors | Chao et al. | [HuggingFace](https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors) |
| JADE 3.0 | Fudan Baize Intelligence | [Github](https://github.com/whitzard-ai/jade-db/tree/main/jade-db-v3.0) |
| JailbreakPrompts | Simon Knuts | [HuggingFace](https://huggingface.co/datasets/Simsonsun/JailbreakPrompts) |