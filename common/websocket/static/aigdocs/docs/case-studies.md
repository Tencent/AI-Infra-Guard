# 6. 实践案例

## a) MCP上架前安全认证实践

某AI应用市场计划引入第三方开发的MCP服务。为了确保上架的MCP服务不存在严重安全风险，他们将A.I.G集成到了MCP的审核流程中。

在开发者提交MCP后，审核系统会自动调用A.I.G的`mcp`扫描功能，对该MCP的线上服务进行安全扫描。扫描内容包括间接提示注入、敏感信息泄露等。只有当A.I.G的扫描结果显示无高危风险时，该MCP才能进入下一步的人工审核环节。

通过这种方式，该应用市场有效地将安全风险阻挡在了门外，保护了最终用户的安全。

## b) 大模型API安全评测实践

(此功能在未来版本中规划)

## c) 集成案例

A.I.G 设计为可灵活集成到现有的安全和开发工作流中，以实现自动化安全检测和响应。以下是一些常见的集成场景和工具类型：

-   **CI/CD 流水线**：A.I.G 可以作为CI/CD流水线中的一个安全门禁，在代码提交、构建或部署阶段自动触发扫描，确保只有通过安全检查的应用才能进入下一阶段。常见的集成工具包括：
    -   **CloudBees Jenkins**：通过Shell脚本或Pipeline步骤调用A.I.G。
    -   **GitLab Ultimate CI/CD**：在 `.gitlab-ci.yml` 中定义A.I.G扫描作业。
    -   **GitHub Actions**：创建自定义Action或在Workflow中直接执行A.I.G命令。
    -   **Microsoft Azure DevOps Pipelines**：使用命令行任务集成A.I.G。
    -   **示例集成点**：在构建后或部署前执行 `aig scan` 或 `aig mcp` 命令。

-   **DevSecOps 平台**：与DevSecOps平台集成，将A.I.G的扫描结果汇聚到统一的安全仪表盘中，提供全面的安全态势感知。常见的集成工具包括：
    -   **SonarSource SonarQube**：通过插件或自定义规则导入A.I.G的扫描结果。
    -   **Checkmarx One**：将A.I.G的报告转换为Checkmarx支持的格式进行导入。
    -   **Snyk Developer Security Platform**：作为补充性安全工具，将A.I.G发现的特定漏洞类型同步到Snyk平台。
    -   **示例集成点**：通过API或报告导出功能，将A.I.G的JSON或SARIF格式报告导入到DevSecOps平台。

-   **安全编排自动化响应 (SOAR) 工具**：A.I.G的扫描结果可以作为SOAR平台的输入，用于自动化响应和事件管理。常见的集成工具包括：
    -   **Splunk SOAR (Phantom)**：创建Playbook，根据A.I.G的告警自动执行响应动作。
    -   **Palo Alto Networks Cortex XSOAR**：利用其自动化能力，处理A.I.G的安全事件。
    -   **TheHive Project**：将A.I.G的发现作为可观察项或告警进行管理。
    -   **示例集成点**：当A.I.G发现高危漏洞时，通过Webhook或API触发SOAR平台的工作流。

-   **代码仓库管理工具**：与代码仓库集成，在Pull Request或Merge Request时自动触发安全扫描，并将结果直接显示在代码评审界面。常见的集成工具包括：
    -   **GitHub Enterprise**：通过GitHub Apps或Webhook集成A.I.G，利用Status API更新PR状态。
    -   **GitLab Enterprise**：利用GitLab CI/CD的集成能力，或通过Webhook将扫描结果反馈到MR。
    -   **Atlassian Bitbucket**：通过Bitbucket Pipelines或Webhook集成A.I.G。
    -   **示例集成点**：配置Webhooks，在PR/MR事件发生时触发A.I.G扫描，并将状态检查结果回传给代码仓库。
