// Package parser 实现AST语法解析
package parser

import (
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"

	vv "github.com/hashicorp/go-version"
)

// Pre-compiled regexes for version checking - avoids repeated compilation overhead
var (
	letterRegex    = regexp.MustCompile(`[A-Za-z]+`)
	dotLetterRegex = regexp.MustCompile(`\.[A-Za-z]+`)
)

// Exp 定义了表达式接口
// 所有表达式类型都需要实现 Name() 方法
type Exp interface {
	Name() string
}

// Rule 表示一个规则，包含多个表达式
type Rule struct {
	root Exp
}

type dslExp struct {
	op        string
	left      string
	right     string
	cacheRegx *regexp.Regexp
}

func (d dslExp) Name() string {
	return "dslExp"
}

type logicExp struct {
	op    string
	left  Exp
	right Exp
}

func (l logicExp) Name() string {
	return "logicExp"
}

type bracketExp struct {
	inner Exp
}

func (b bracketExp) Name() string {
	return "bracketExp"
}

// TransFormExp 将token序列转换为表达式规则
// 输入tokens切片，返回Rule对象和error
// 主要功能：解析tokens并构建DSL表达式、逻辑表达式和括号表达式
func TransFormExp(tokens []Token) (*Rule, error) {
	stream := newTokenStream(tokens)
	root, err := parseExpr(stream)
	if err != nil {
		return nil, err
	}

	if stream.hasNext() {
		return nil, errors.New("unexpected tokens after expression")
	}

	return &Rule{root: root}, nil
}

// parseExpr 解析表达式
func parseExpr(stream *tokenStream) (Exp, error) {
	expr, err := parsePrimaryExpr(stream)
	if err != nil {
		return nil, err
	}

	for stream.hasNext() {
		token, err := stream.next()
		if err != nil {
			return nil, err
		}
		if token.name == tokenAnd || token.name == tokenOr {
			right, err := parsePrimaryExpr(stream)
			if err != nil {
				return nil, err
			}
			// 提高括号表达式的优先级
			if _, ok := right.(*bracketExp); ok {
				expr = &logicExp{op: token.content, left: right, right: expr}
			} else {
				expr = &logicExp{op: token.content, left: expr, right: right}
			}
		} else {
			stream.rewind()
			break
		}
	}
	return expr, nil
}

// parsePrimary 解析括号语句和基础表达式
func parsePrimaryExpr(stream *tokenStream) (Exp, error) {
	tmpToken, err := stream.next()
	if err != nil {
		return nil, err
	}

	switch tmpToken.name {
	case tokenBody, tokenHeader, tokenIcon, tokenHash, tokenVersion, tokenIsInternal:
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
		if p3.name != tokenText {
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
			dsl = dslExp{left: tmpToken.content, op: p2.content, cacheRegx: compile}
		} else {
			dsl = dslExp{left: tmpToken.content, op: p2.content, right: p3.content}
		}
		return &dsl, nil
	case tokenLeftBracket:
		inner, err := parseExpr(stream)
		if err != nil {
			return nil, err
		}
		closingToken, err := stream.next()
		if err != nil || closingToken.name != tokenRightBracket {
			return nil, errors.New("missing or invalid closing bracket")
		}
		return &bracketExp{inner: inner}, nil
	default:
		return nil, errors.New("unexpected token: " + tmpToken.content)
	}
}

// PrintAST 递归打印表达式
func (r *Rule) PrintAST() {
	if r.root == nil {
		return
	}

	var printExpr func(expr Exp, level int)
	printExpr = func(expr Exp, level int) {
		indent := strings.Repeat("  ", level)

		switch e := expr.(type) {
		case *dslExp:
			if e.cacheRegx != nil {
				fmt.Printf("%s    dslExp: %s %s regex('%s')\n", indent, e.left, e.op, e.cacheRegx.String())
			} else {
				fmt.Printf("%s    dslExp: %s %s '%s'\n", indent, e.left, e.op, e.right)
			}

		case *logicExp:
			fmt.Printf("%s logicExp: %s\n", indent, e.op)
			fmt.Printf("%s  - left:\n", indent)
			printExpr(e.left, level+1)
			fmt.Printf("%s  - right:\n", indent)
			printExpr(e.right, level+1)

		case *bracketExp:
			fmt.Printf("%s bracketExp:\n", indent)
			printExpr(e.inner, level+1)

		default:
			fmt.Printf("%s Unknown expression type\n", indent)
		}
	}

	printExpr(r.root, 0)
}

// Eval 评估规则是否匹配
// 输入配置对象，返回布尔值表示是否匹配
// 使用栈实现后缀表达式求值
func (r *Rule) Eval(config *Config) bool {
	var evalExpr func(expr Exp, config *Config) bool

	evalExpr = func(expr Exp, config *Config) bool {
		switch next := expr.(type) {
		case *dslExp:
			var s1 string
			switch next.left {
			case tokenBody:
				s1 = config.Body
			case tokenHeader:
				s1 = config.Header
			case tokenIcon:
				s1 = strconv.Itoa(int(config.Icon))
			case tokenHash:
				s1 = config.Hash
			default:
				panic("unknown left token")
			}
			s1 = strings.ToLower(s1)
			text := strings.ToLower(next.right)
			var r bool
			switch next.op {
			case tokenFullEqual:
				r = text == s1
			case tokenContains:
				r = strings.Contains(s1, text)
			case tokenNotEqual:
				r = !strings.Contains(s1, text)
			case tokenRegexEqual:
				r = next.cacheRegx.MatchString(s1)
			default:
				panic("unknown op token")
			}
			return r
		case *logicExp:
			switch next.op {
			case tokenAnd:
				leftVal := evalExpr(next.left, config)
				if !leftVal { // short-circuit evaluation
					return false
				}
				return evalExpr(next.right, config)
			case tokenOr:
				leftVal := evalExpr(next.left, config)
				if leftVal { // short-circuit evaluation
					return true
				}
				return evalExpr(next.right, config)
			default:
				panic("unknown logic type")
			}
		case *bracketExp:
			return evalExpr(next.inner, config)
		default:
			panic("error eval")
		}
	}

	if r.root == nil {
		return false
	}
	return evalExpr(r.root, config)
}

// versionCheck 版本号格式标准化处理
// 输入版本号字符串，返回处理后的版本号字符串
// 去除版本号中的字母并进行格式统一化
// 优化: 使用预编译的正则表达式，避免重复编译开销
func versionCheck(version string) string {
	version = strings.TrimPrefix(version, "v")
	if version == "latest" {
		return "999"
	}
	// 使用预编译的正则替换所有单词
	if letterRegex.MatchString(version) {
		newVersion := dotLetterRegex.ReplaceAllString(version, ".0")
		newVersion = letterRegex.ReplaceAllString(newVersion, "")
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
	var err error
	var evalExpr func(expr Exp, config *AdvisoryConfig) bool
	evalExpr = func(expr Exp, config *AdvisoryConfig) bool {
		switch next := expr.(type) {
		case *dslExp:
			var s1 string
			var v1 *vv.Version
			var text string
			var r bool
			switch next.left {
			case tokenVersion:
				s1 = versionCheck(config.Version)
				v1, err = vv.NewVersion(s1)
				if err != nil {
					gologger.Debugf("无法解析版本号:%s=>%s", config.Version, "0.0.0")
					v1, _ = vv.NewVersion("0.0.0")
				}
				text = versionCheck(next.right)
				switch next.op {
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
					panic("unknown op token")
				}
			case tokenIsInternal:
				r = config.IsInternal
			default:
				panic("unknown left token")
			}
			return r
		case *logicExp:
			switch next.op {
			case tokenAnd:
				leftVal := evalExpr(next.left, config)
				if !leftVal { // short-circuit evaluation
					return false
				}
				return evalExpr(next.right, config)
			case tokenOr:
				leftVal := evalExpr(next.left, config)
				if leftVal { // short-circuit evaluation
					return true
				}
				return evalExpr(next.right, config)
			default:
				panic("unknown logic type")
			}
		case *bracketExp:
			return evalExpr(next.inner, config)
		default:
			panic("error eval")
		}
	}

	if r.root == nil {
		return false
	}
	return evalExpr(r.root, config)
}

// hashUsage returns whether a Rule references the hash keyword and whether it is hash-only.
func (r *Rule) hashUsage() (usesHash bool, hashOnly bool) {
	if r == nil || r.root == nil {
		return false, false
	}
	hashOnly = true
	var visit func(expr Exp)
	visit = func(expr Exp) {
		if expr == nil {
			return
		}
		switch next := expr.(type) {
		case *dslExp:
			if next.left == tokenHash {
				usesHash = true
			} else {
				hashOnly = false
			}
		case *logicExp:
			visit(next.left)
			visit(next.right)
		case *bracketExp:
			visit(next.inner)
		}
	}
	visit(r.root)
	if !usesHash {
		hashOnly = false
	}
	return
}
