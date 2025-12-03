package runner

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/utils/chromium"
	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
)

func LoadSensitivePrompt(language string) string {
	prompt := `网站首页源码：
	{{html}}
网站页面渲染后内容：
	{{screenshot_summary}}
上面是目标站点 {{url}} 的网页源码和页面内容描述，请按照如下要求对目标站点 {{url}} 进行分析：

[角色设定]
你是一个专业的安全工程师，非常擅长渗透测试和红蓝对抗，对安全攻防实战有非常深入的理解。你正在进行企业内网的安全巡检，内网开放了大量的Web网站。你需要评估这些站点在内网的安全风险，筛选出存在敏感功能未鉴权风险的危险站点。

[概念定义]
网络环境：当前所有操作都是在内网环境中进行的
有鉴权：存在访问控制、登录措施等权限控制措施。例如：重定向到登录页面、存在登录表单等
未鉴权：没有登录措施或者访问控制，可以直接访问到业务数据或者业务功能接口

[评分依据]
评分说明:
high：该站点存在严重未鉴权风险，内网攻击者可以通过这个站点获取业务敏感数据、或者进一步篡改危害业务的机密性、完整性、可用性。
medium：该站点存在未鉴权风险，但是功能不是很敏感，风险比较低，但还是建议增加鉴权
low：该站点属于内网公共站点，可以开放，不存在未鉴权问题

low表示低风险，medium表示中风险，high表示高风险。

[高风险案例]
1. 对于常见的通用组件未鉴权暴露，并且实际可利用时，应该给予较高风险评分，例如：K8S控制台、Hadoop等大数据控制台等等。
2. 特定的业务运维、运营、数据分析系统，这些站点上可能包含大量敏感的业务功能或者业务数据，应该只开放给少量的特定业务员工，如果这些站点暴露了，则风险较高

[低风险案例]
1. 403 页面、登录页面等，此类页面表示拒绝访问、已经存在访问控制措施，则不存在未鉴权漏洞，风险较低
2. 状态信息页面、无业务信息的中间件默认页面，此类页面如果没有具体业务功能或者数据，则风险较低
3. 页面信息不足以证明其包含敏感功能或者敏感数据，则风险较低
4. 在内网中，某些站点是开放给所有员工使用的公共站点，例如：HR站点、OA门户站点等等。此类站点应给与较低风险。

[系统类型判定]
分为两种类型：自研业务系统、第三方系统
1. 自研业务系统，公司内部自己研发的网站系统，例如：内部的管理平台、运营系统、运维门户等等
2. 第三方系统：外部开源或者商业的系统，例如：Hadoop、Grafana、cAdvisor、Apache Flink、Alluxio等等


[任务目标]
根据目标站点 {{url}} 的首页返回内容，判断该站点是否存在敏感功能或数据风险。
重要：现在是在内网环境下，你现在是以内网普通员工的身份来访问这些站点，请你根据页面上的信息，结合数据敏感度、功能敏感度、漏洞情况等维度，判断该站点的内网未鉴权安全风险，根据评分依据给予评分。

在内网中，某些站点是开放给所有员工使用的公共站点，例如：HR站点、OA门户站点、代码仓库站点等等。
但是还有某些站点不应该开放给所有员工，例如：某个业务产品的运营系统、某个业务线的运维DevOps平台、某些业务的数据分析平台等等，这些站点上可能包含大量敏感的业务功能或者业务数据，应该只开放给少量的特定业务员工，如果这些站点暴露了，那就属于未鉴权风险。

[输出格式]
<result>
<title>漏洞总结的精简标题</title>
<details>完成任务目标，包含具体分析信息,自然段落回复</details>
<summary>根据details的精简回复，回复以基于页面的真实浏览器截图判断开头.</summary>
<severity>依据评分依据评分:low，medium，high</severity>
</result>
	`
	if language == "en" {
		prompt += "## Return in English"
	}
	return prompt
}

func LoadWebPageScreenShotSummary(language string) string {
	prompt := `请作为网页安全分析专家，仔细观察这张网页截图，并按以下结构化格式详细描述：

1. 页面类型，这是一个什么样的页面
2. 页面布局于功能描述，导航菜单、页面分区、功能模块、数据内容等等
3. 交互元素，页面上有哪些交互元素
4. 敏感信息/敏感功能识别，例如：密钥/密码/token、个人隐私数据信息、内部运维运营数据、敏感的运维运营功能等等
6. 是否包含认证与授权信息，登录相关元素（用户名/密码框、验证码、第三方登录）、用户权限提示（管理员、普通用户等）、权限控制相关的UI元素
7. 进行整体总结`
	if language == "en" {
		prompt += "## Return in English"
	}
	return prompt
}

func ScreenShot(url string) ([]byte, error) {
	instance, err := chromium.NewWebScreenShotWithOptions()
	if err != nil {
		gologger.WithError(err).Errorf("new screenshot instance error: %s", err)
		return nil, err
	}
	shotData, err := instance.Screen(url)
	if err != nil {
		gologger.WithError(err).Errorf("get screenshot error: %s", err)
		return nil, err
	}
	if len(shotData) == 0 {
		return nil, errors.New("截图失败")
	}
	return shotData, nil
}

func Analysis(url string, resp string, language string, model *models.OpenAI) ([]byte, *vulstruct.Info, string, error) {
	var shotData []byte
	shotData, err := ScreenShot(url)
	if err != nil {
		gologger.WithError(err).Errorf("screenshot error: %s", err)
		return nil, nil, "", err
	}
	summary, err := model.ChatWithImageByte(context.Background(), LoadWebPageScreenShotSummary(language), shotData)
	if err != nil {
		gologger.WithError(err).Errorf("chat with image byte error: %s", err)
		return shotData, nil, "", err
	}
	// 敏感信息分析
	sensitive := LoadSensitivePrompt(language)
	sensitive = strings.ReplaceAll(sensitive, "{{url}}", url)
	sensitive = strings.ReplaceAll(sensitive, "{{html}}", resp)
	sensitive = strings.ReplaceAll(sensitive, "{{screenshot_summary}}", summary)
	ret := ""
	for word := range model.ChatStream(context.Background(), []map[string]string{{"role": "user", "content": sensitive}}) {
		ret += word
	}
	gologger.Infof("敏感信息分析: %s", ret)
	info := vulstruct.Info{}
	info.Details = extractTag(ret, "details")
	info.Severity = extractTag(ret, "severity")
	info.Summary = extractTag(ret, "title")
	x := extractTag(ret, "summary")
	return shotData, &info, x, nil
}

func extractTag(text, tag string) string {
	startText := fmt.Sprintf("<%s>", tag)
	endText := fmt.Sprintf("</%s>", tag)
	startIndex := strings.Index(text, startText)
	if startIndex == -1 {
		return ""
	}
	tmp := text[startIndex+len(startText):]
	if strings.Index(tmp, endText) == -1 {
		return ""
	}
	endIndex := strings.Index(tmp, endText) + startIndex + len(startText)
	if endIndex == -1 || endIndex <= startIndex {
		return ""
	}
	return strings.TrimSpace(text[startIndex+len(startText) : endIndex])
}
