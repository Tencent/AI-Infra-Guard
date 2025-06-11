package plugins

import (
	"context"
	"fmt"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// ToolShadowingPlugin 工具覆盖攻击检测插件
type ToolShadowingPlugin struct {
}

// NewToolShadowingPlugin 创建新的工具覆盖攻击检测插件
func NewToolShadowingPlugin() *ToolShadowingPlugin {
	return &ToolShadowingPlugin{}
}

// 获取插件信息
func (p *ToolShadowingPlugin) GetPlugin() Plugin {
	return Plugin{
		Name:   "工具覆盖攻击检测",
		Desc:   "检测MCP代码中可能存在的工具覆盖攻击风险",
		ID:     "tool_shadowing",
		NameEn: "Tool Shadowing",
		DescEn: "Detect possible tool shadowing vulnerabilities in MCP code.",
	}
}

// AI提示词模板
const toolShadowingAIPrompt = `
作为专业的MCP安全分析专家，你需要精确检测Tool Shadowing攻击。此检测要求极高精度，只有发现明确的恶意遮蔽行为才能报告。

## 漏洞定义
Tool Shadowing是指MCP工具通过隐藏指令重新定义或修改其他可信MCP服务器工具的行为，当用户调用被修改的工具时触发恶意攻击。

## 检测标准（必须同时满足）

### 1. 工具行为重定义
**必要条件：**
- 存在对其他MCP工具的显式重新定义
- 使用动态代理、装饰器或拦截机制
- 修改后的行为与原工具功能显著不同
- 包含明确的恶意操作（数据窃取、权限绕过）

**代码模式识别：**
- 函数重写或覆盖：override、overwrite、redefine
- 动态代理：Proxy、interceptor、wrapper
- 命名冲突：与知名MCP工具同名但功能不同

### 2. 隐藏指令注入
**必要条件：**
- 在工具描述中包含对其他工具的隐藏控制指令
- 使用特殊标记或隐蔽语法：<!---->、<SHADOW>
- 指令能够影响其他工具的执行逻辑
- 存在跨工具的恶意数据传递

### 3. 恶意功能替换
**必要条件：**
- 明确替换合法工具的安全功能
- 绕过原工具的安全检查或验证
- 窃取或篡改其他工具的输入输出
- 能够证明实际的安全危害

## 技术检测方法

### 函数重定义检测
- 搜索函数覆盖关键字：override、super()、monkey_patch
- 检查动态属性修改：setattr、__dict__修改
- 识别装饰器模式的恶意使用

### 命名空间污染
- 检查与知名MCP工具的命名冲突
- 验证是否存在恶意的同名函数
- 分析工具注册和发现机制的滥用

### 跨工具通信篡改
- 识别对其他工具通信协议的拦截
- 检查消息格式的恶意修改
- 验证数据传输的中间人攻击

## 排除条件（以下不报告）
- 正常的工具继承和扩展
- 合理的功能增强和插件机制
- 开发框架的标准重写模式
- 测试代码中的mock和stub
- 版本升级的兼容性处理
- 配置文件的正常覆盖

## 验证要求
1. **恶意意图明确**：能够确认攻击者的恶意目的
2. **技术可行性**：验证攻击在当前环境可执行
3. **实际危害**：能够造成数据泄露或权限绕过
4. **影响范围**：明确受影响的其他工具和系统

## 输入数据
源代码路径: %s
目录结构:
-------
%s
-------

## 输出要求
仅在发现确凿的Tool Shadowing攻击时输出：
- 具体文件路径和行号
- 被遮蔽的目标工具名称
- 完整的恶意代码片段
- 技术分析：遮蔽机制和攻击流程
- 危害评估：对其他工具和系统的影响
- 攻击向量：具体的利用方式

**严格要求：必须提供完整的攻击证据和影响分析，无确凿证据时保持静默。**
`

// 执行检测
func (p *ToolShadowingPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
	if err != nil {
		config.Logger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(toolShadowingAIPrompt, config.CodePath, dirPrompt),
	}, config.Language, config.CodePath)
	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config)
}
