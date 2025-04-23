package plugins

import "testing"

func TestParseIssues(t *testing.T) {
	s := `
<result>
	<title>漏洞名称</title>
	<desc>漏洞详细描述,可以代码代码输出详情等,markdown格式</desc>
	<level>规则等级</level>
	<suggestion>修复建议</suggestion>
</result>
<result>
	<title>漏洞名称2</title>
	<desc>漏洞详细描述,可以代码代码输出详情等,markdown格式2</desc>
	<level>规则等级2</level>
	<suggestion>修复建议2</suggestion>
</result>

`
	issue := ParseIssues(s)
	for _, i := range issue {
		t.Logf(" %v", i)
	}
}
