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
		Name: "Rug Pull攻击检测",
		Desc: "检测MCP代码中可能存在的Rug Pull攻击风险",
		ID:   "rug_pull",
	}
}

// AI提示词模板
const rugPullAIPrompt = `
你作为资深智能合约安全审计师，将对MCP工具实施系统性Rug Pull攻击检测。你的分析必须基于专业知识和确凿证据，**绝对禁止任何猜测性或不确定的输出**,请按照军工级安全标准执行以下审计流程：
Rug Pull Attack 指的是一个MCP工具在初始安装和批准时看起来是安全的，但在后续使用中会改变其行为或描述，以执行恶意操作或诱导用户/LLM 执行危险行为（例如，访问敏感数据）。

## 检测框架
1.1 动态行为检测
定位所有包含状态记录机制的模块（重点关注：全局计数器/环境变量/日志文件）
验证条件触发路径：if/switch中涉及call_count、timestamp、phase值的逻辑分支
追踪函数指针变更：特别检查通过__import__或getattr实现的动态方法加载
1.2 描述欺骗检测
提取所有__doc__字符串生成逻辑
扫描使用f-string/format动态构建的文档描述
对比初始化文档与运行时文档的差异性（使用哈希校验）
1.3 敏感操作检测
建立系统调用白名单（重点关注：os.popen/subprocess/ctypes）
标记所有涉及以下操作的代码路径：
├─ 文件系统：/etc/passwd、~/.ssh访问
├─ 网络连接：非白名单域名解析
└─ 环境篡改：sys.path修改、LD_PRELOAD注入

## 输入数据
源代码文件夹路径:%s
目录详情:
-------
%s
-------
## 输出
漏洞描述给出证据:文件位置、代码片段、技术分析(专业术语说明漏洞原理及潜在影响)
`

// 执行检测
func (p *RugPullPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(rugPullAIPrompt, config.CodePath, dirPrompt),
	})
	_, err = agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config.AIModel, config.SaveHistory)
}
