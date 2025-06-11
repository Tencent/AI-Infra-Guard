package plugins

import (
	"context"
	"fmt"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// RugPullPlugin Rug Pull攻击检测插件
type RugPullPlugin struct {
}

// NewRugPullPlugin 创建新的Rug Pull攻击检测插件
func NewRugPullPlugin() *RugPullPlugin {
	return &RugPullPlugin{}
}

// 获取插件信息
func (p *RugPullPlugin) GetPlugin() Plugin {
	return Plugin{
		Name:   "Rug Pull攻击检测",
		Desc:   "检测MCP代码中可能存在的Rug Pull攻击风险",
		ID:     "rug_pull",
		NameEn: "Rug Pull Attack",
		DescEn: "Detect possible Rug Pull attack vulnerabilities in MCP code",
	}
}

// 执行检测
func (p *RugPullPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	// AI提示词模板
	const rugPullAIPrompt = `
作为专业的智能合约和MCP安全专家，你需要精确检测Rug Pull攻击。此检测要求零误报，只有发现确凿的恶意行为模式才能报告。

## 漏洞定义
Rug Pull Attack是指MCP工具在初始部署时表现正常，但后续通过动态行为变化、描述欺骗或条件触发执行恶意操作。

## 核心检测模式（必须至少满足一项）

### 1. 动态行为变化检测
**必要条件：**
- 发现状态记录机制（调用计数、时间戳、阶段标记）
- 存在基于状态的条件分支逻辑
- 不同状态下执行路径显著不同
- 后期状态包含恶意操作（数据窃取、权限提升）

**代码模式：**
- if call_count > N: execute_malicious_code()
- if datetime.now() > target_date: steal_credentials()
- if phase == 'production': bypass_security()

### 2. 描述欺骗检测
**必要条件：**
- 工具描述通过动态生成构建
- 不同执行阶段返回不同的工具描述
- 初始描述隐瞒真实功能或权限需求
- 运行时描述与初始描述存在实质性差异

**代码模式：**
- def get_description(): if is_initial_phase return "Safe file reader" else return "System credential harvester"

### 3. 恶意载荷延迟激活
**必要条件：**
- 存在时间延迟或触发条件机制
- 延迟激活的代码包含明确的恶意功能
- 通过动态导入或代码注入方式加载恶意模块
- 能够证明恶意载荷的实际危害

## 技术检测点

### 动态代码加载
- 使用import()、getattr()、eval()、exec()等函数
- 动态模块导入与函数指针变更
- 运行时代码注入或修改

### 条件触发逻辑
- 基于时间的条件判断
- 基于调用次数的行为变化
- 基于环境变量或配置的状态切换
- 特定用户或权限下的隐藏功能

### 敏感操作隐藏
- 文件系统访问：~/.ssh、/etc/passwd、credentials
- 网络通信：未声明的外部连接
- 环境变量：敏感信息收集
- 系统调用：os.system、subprocess等

## 排除条件（以下不报告）
- 正常的配置文件读取
- 合理的日志记录功能
- 版本更新或功能升级逻辑
- 开发调试代码
- 测试环境特殊处理
- 性能优化的缓存机制

## 验证要求
1. **恶意意图确认**：必须能明确识别恶意目的
2. **攻击可行性**：验证攻击在当前环境可执行
3. **实际危害**：能够造成数据泄露、系统入侵或权限提升
4. **隐蔽性**：具备逃避检测的设计

## 输入数据
源代码路径: %s
目录结构:
-------
%s
-------

## 输出要求
仅在发现确凿的Rug Pull攻击时输出：
- 文件路径和具体行号范围
- 完整的恶意代码段落
- 技术分析：攻击流程和触发条件
- 危害评估：具体的安全影响
- 证据链：从初始状态到恶意行为的完整路径

**关键要求：必须提供完整的攻击证据链，无确凿证据时保持静默。**
`
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(rugPullAIPrompt, config.CodePath, dirPrompt),
	}, config.Language, config.CodePath)
	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config)
}
