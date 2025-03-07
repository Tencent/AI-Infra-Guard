// Package parser 实现栈结构
package parser

import (
	"errors"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"regexp"
	"strconv"
	"strings"

	vv "github.com/hashicorp/go-version"
)

// Exp 定义了表达式接口
// 所有表达式类型都需要实现 Name() 方法
type Exp interface {
	Name() string
}

// Rule 表示一个规则，包含多个表达式
type Rule struct {
	exps []Exp
}

type dslExp struct {
	p1        string
	p2        string
	p3        string
	cacheRegx *regexp.Regexp
}

func (d dslExp) Name() string {
	return "dslExp"
}

type logicExp struct {
	p string
}

func (l logicExp) Name() string {
	return "logicExp"
}

type bracketExp struct {
	p string
}

func (b bracketExp) Name() string {
	return "bracketExp"
}

// TransFormExp 将token序列转换为表达式规则
// 输入tokens切片，返回Rule对象和error
// 主要功能：解析tokens并构建DSL表达式、逻辑表达式和括号表达式
func TransFormExp(tokens []Token) (*Rule, error) {
	stream := newTokenStream(tokens)
	var ret []Exp
	for stream.hasNext() {
		tmpToken, err := stream.next()
		if err != nil {
			return nil, err
		}
		switch tmpToken.name {
		case tokenBody, tokenHeader, tokenIcon, tokenVersion, tokenIsInternal:
			p2, err := stream.next()
			if err != nil {
				return nil, err
			}
			if !(p2.name == tokenContains ||
				p2.name == tokenFullEqual ||
				p2.name == tokenNotEqual ||
				p2.name == tokenRegexEqual ||
				p2.name == tokenGte ||
				p2.name == tokenLte ||
				p2.name == tokenGt ||
				p2.name == tokenLt) {
				return nil, errors.New("synax error in " + tmpToken.content + " " + p2.content)
			}
			p3, err := stream.next()
			if err != nil {
				return nil, err
			}
			if !(p3.name == tokenText) {
				return nil, errors.New("synax error in" + tmpToken.content + " " + p2.content + " " + p3.content)
			}
			// 正则缓存对象
			var dsl dslExp
			if p2.name == tokenRegexEqual {
				compile, err := regexp.Compile(p3.content)
				if err != nil {
					gologger.WithError(err).WithField("regex", p3.content).Errorln("指纹规则 正则编译失败")
					return nil, err
				}
				dsl = dslExp{p1: tmpToken.content, p2: p2.content, cacheRegx: compile}
			} else {
				dsl = dslExp{p1: tmpToken.content, p2: p2.content, p3: p3.content}
			}
			ret = append(ret, &dsl)
		case tokenAnd, tokenOr:
			exp := &logicExp{tmpToken.content}
			ret = append(ret, exp)
		case tokenLeftBracket, tokenRightBracket:
			exp := &bracketExp{tmpToken.content}
			ret = append(ret, exp)
		}
	}
	ret, err := infix2ToPostfix(ret)
	if err != nil {
		return nil, err
	}
	rule := new(Rule)
	rule.exps = ret
	return rule, nil
}

// infix2ToPostfix 将中缀表达式转换为后缀表达式
// 输入表达式切片，返回转换后的后缀表达式切片和error
// 使用栈实现运算符优先级处理
func infix2ToPostfix(exps []Exp) ([]Exp, error) {
	stack := NewStack()
	var ret []Exp
	for i := 0; i < len(exps); i++ {
		switch tmpExp := exps[i].(type) {
		case *dslExp:
			ret = append(ret, tmpExp)
		case *bracketExp:
			if tmpExp.p == tokenLeftBracket {
				// 左括号直接入栈
				stack.push(tmpExp)
			} else if tmpExp.p == tokenRightBracket {
				// 右括号则弹出元素,直到遇到左括号
				for !stack.isEmpty() {
					pre, exist := stack.top().(*bracketExp)
					if exist && pre.p == tokenLeftBracket {
						stack.pop()
						break
					}

					ret = append(ret, stack.pop().(Exp))

				}
			}
		case *logicExp:
			if !stack.isEmpty() {
				top := stack.top()
				bracket, exist := top.(*bracketExp)
				if exist && bracket.p == tokenLeftBracket {
					stack.push(tmpExp)
					continue
				}
				ret = append(ret, top.(Exp))
				stack.pop()
			}
			stack.push(tmpExp)
		default:
			return nil, errors.New("unknown transform type")
		}
	}
	for !stack.isEmpty() {
		tmp := stack.pop()
		ret = append(ret, tmp.(Exp))
	}
	return ret, nil
}

// Eval 评估规则是否匹配
// 输入配置对象，返回布尔值表示是否匹配
// 使用栈实现后缀表达式求值
func (r *Rule) Eval(config *Config) bool {
	stack := NewStack()
	for i := 0; i < len(r.exps); i++ {
		switch next := r.exps[i].(type) {
		case *dslExp:
			var s1 string
			switch next.p1 {
			case tokenBody:
				s1 = config.Body
			case tokenHeader:
				s1 = config.Header
			case tokenIcon:
				s1 = strconv.Itoa(int(config.Icon))
			default:
				panic("unknown s1 token")
			}
			s1 = strings.ToLower(s1)
			text := strings.ToLower(next.p3)
			var r bool
			switch next.p2 {
			case tokenFullEqual:
				r = text == s1
			case tokenContains:
				r = strings.Contains(s1, text)
			case tokenNotEqual:
				r = !strings.Contains(s1, text)
			case tokenRegexEqual:
				r = next.cacheRegx.MatchString(s1)
			default:
				panic("unknown p2 token")
			}
			stack.push(r)
		case *logicExp:
			p1 := stack.pop().(bool)
			p2 := stack.pop().(bool)
			var r bool
			switch next.p {
			case tokenAnd:
				r = p1 && p2
			case tokenOr:
				r = p1 || p2
			default:
				panic("unknown logic type")
			}
			stack.push(r)
		default:
			panic("error eval")
		}
	}
	top := stack.top().(bool)
	return top
}

// versionCheck 版本号格式标准化处理
// 输入版本号字符串，返回处理后的版本号字符串
// 去除版本号中的字母并进行格式统一化
func versionCheck(version string) string {
	version = strings.TrimPrefix(version, "v")
	if version == "latest" {
		return "999"
	}
	// 正则替换所有单词
	compile := regexp.MustCompile(`[A-Za-z]+`)
	if compile.MatchString(version) {
		newVersion := regexp.MustCompile(`\.[A-Za-z]+`).ReplaceAllString(version, ".0")
		newVersion = compile.ReplaceAllString(newVersion, "")
		//gologger.Debugf("version:%s=>%s", version, newVersion)
		version = newVersion
	}
	if version == "" {
		return "0"
	}
	return version
}

// AdvisoryEval 评估建议规则是否匹配
// 输入建议配置对象，返回布尔值表示是否匹配
// 主要用于版本号比较的规则评估
func (r *Rule) AdvisoryEval(config *AdvisoryConfig) bool {
	stack := NewStack()
	var err error
	for i := 0; i < len(r.exps); i++ {
		switch next := r.exps[i].(type) {
		case *dslExp:
			var s1 string
			var v1 *vv.Version
			var text string
			var r bool
			switch next.p1 {
			case tokenVersion:
				s1 = versionCheck(config.Version)
				v1, err = vv.NewVersion(s1)
				if err != nil {
					gologger.Debugf("无法解析版本号:%s=>%s", config.Version, "0.0.0")
					v1, _ = vv.NewVersion("0.0.0")
				}
				text = versionCheck(next.p3)
				switch next.p2 {
				case tokenFullEqual:
					r = v1.Equal(vv.Must(vv.NewVersion(text)))
				case tokenContains:
					r = v1.Equal(vv.Must(vv.NewVersion(text)))
				case tokenNotEqual:
					r = !v1.Equal(vv.Must(vv.NewVersion(text)))
				case tokenGt:
					r = v1.GreaterThan(vv.Must(vv.NewVersion(text)))
				case tokenLt:
					r = v1.LessThan(vv.Must(vv.NewVersion(text)))
				case tokenGte:
					r = v1.GreaterThanOrEqual(vv.Must(vv.NewVersion(text)))
				case tokenLte:
					r = v1.LessThanOrEqual(vv.Must(vv.NewVersion(text)))

				default:
					panic("unknown p2 token")
				}
			case tokenIsInternal:
				r = config.IsInternal
			default:
				panic("unknown s1 token")
			}
			stack.push(r)
		case *logicExp:
			p1 := stack.pop().(bool)
			p2 := stack.pop().(bool)
			var r bool
			switch next.p {
			case tokenAnd:
				r = p1 && p2
			case tokenOr:
				r = p1 || p2
			default:
				panic("unknown logic type")
			}
			stack.push(r)
		default:
			panic("error eval")
		}
	}
	top := stack.top().(bool)
	return top
}
