package parser

import "testing"

func TestTransFormExp(t *testing.T) {
	s := "header=\"realm=\\\"Comtrend Gigabit 802.11n Router\" || header=\"Comtrend Gigabit 802.11n Router\""
	tokens, err := ParseTokens(s)
	if err != nil {
		t.Fatal(err)
	}
	exp, err := TransFormExp(tokens)
	if err != nil {
		t.Fatal(err)
	}

	exp.PrintAST()
}

func TestTransFormExp2(t *testing.T) {
	for _, s := range []string{
		`body="nginx" || header="nginx"`,
		`body="nginx" || header="nginx" && header="Server: nginx"`,
		`body="nginx" && header="nginx" || header="Server: nginx"`,
		`(body="nginx" || header="nginx") && header="Server: nginx"`,
		`body="nginx" || (header="nginx" && header="Server: nginx")`,
	} {
		tokens, err := ParseTokens(s)
		if err != nil {
			t.Fatal(err)
		}

		if exp, err := TransFormExp(tokens); err != nil {
			t.Fatal(err)
		} else {
			exp.PrintAST()
		}
	}
}

func TestEval(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Fatal(r)
		}
	}()

	rules := []struct {
		Rule   string
		Config *Config
		Ret    bool
	}{
		{
			Rule: `header="nginx" || body="nginx"`,
			Config: &Config{
				Header: "nginx123",
			},
			Ret: true,
		},
		{
			Rule: `header="nginx" || body="nginx"`,
			Config: &Config{
				Body: "nginxabc",
			},
			Ret: true,
		},
		{
			Rule: `body="nginx" || header="nginx" && icon="123"`,
			Config: &Config{
				Body:   "nginxabc",
				Header: "server:none",
				Icon:   123,
			},
			Ret: true,
		},
		{
			Rule: `body="nginx" || header="nginx" && icon="123"`,
			Config: &Config{
				Body:   "abc",
				Header: "nginx",
				Icon:   123,
			},
			Ret: true,
		},
		{
			Rule: `body="nginx" || header="nginx" && icon="123"`,
			Config: &Config{
				Body:   "nginx",
				Header: "nginx",
				Icon:   456,
			},
			Ret: false,
		},
		{
			Rule: `body="nginx" && (icon=="123" || header="nginx")`,
			Config: &Config{
				Body:   "nginx",
				Header: "server:none",
				Icon:   123,
			},
			Ret: true,
		}, {
			Rule: `body="nginx" && (icon=="123" || header="nginx")`,
			Config: &Config{
				Body:   "nginxabc",
				Header: "server:none",
				Icon:   456,
			},
			Ret: false,
		},
		{
			Rule: `body="nginx" || (icon=="123" && header="nginx")`,
			Config: &Config{
				Body:   "none",
				Header: "nginx",
				Icon:   123,
			},
			Ret: true,
		},
	}

	for _, r := range rules {
		tokens, err := ParseTokens(r.Rule)
		if err != nil {
			t.Fatal(err)
		}
		exp, err := TransFormExp(tokens)
		if err != nil {
			t.Fatal(err)
		}
		if ret := exp.Eval(r.Config); ret != r.Ret {
			t.Fatalf("eval: %s ret: %v", r.Rule, ret)
		}
	}
}
