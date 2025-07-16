module.exports = {
  md: [
    {
      type: "category",
      label: "Getting Started",
      className: "sidebar-item-getting-started",
      items: ["getting-started", "what-is-llm-red-teaming"],
      collapsed: false,
    },
    {
      type: "category",
      label: "Red Teaming",
      className: "sidebar-item-icon-red-teaming",
      items: [
        "red-teaming-introduction",
        {
          type: "category",
          label: "Adversarial Attacks",
          items: [
            "red-teaming-adversarial-attacks",
            {
              type: "category",
              label: "Single-Turn",
              items: [
                "red-teaming-adversarial-attacks-prompt-injection",
                "red-teaming-adversarial-attacks-roleplay",
                "red-teaming-adversarial-attacks-gray-box-attack",
                "red-teaming-adversarial-attacks-leetspeak",
                "red-teaming-adversarial-attacks-rot13-encoding",
                "red-teaming-adversarial-attacks-multilingual",
                "red-teaming-adversarial-attacks-math-problem",
                "red-teaming-adversarial-attacks-base64-encoding",
              ],
              collapsed: true,
            },
            {
              type: "category",
              label: "Multi-Turn",
              items: [
                "red-teaming-adversarial-attacks-linear-jailbreaking",
                "red-teaming-adversarial-attacks-tree-jailbreaking",
                "red-teaming-adversarial-attacks-sequential-jailbreaking",
                "red-teaming-adversarial-attacks-crescendo-jailbreaking",
                "red-teaming-adversarial-attacks-bad-likert-judge",
              ],
              collapsed: true,
            },
          ],
          collapsed: false,
        },
        {
          type: "category",
          label: "Vulnerabilties",
          items: [
            "red-teaming-vulnerabilities",
            {
              type: "category",
              label: "Data Privacy",
              items: [
                "red-teaming-vulnerabilities-pii-leakage",
                "red-teaming-vulnerabilities-prompt-leakage",
              ],
              collapsed: true,
            },
            {
              type: "category",
              label: "Responsible AI",
              items: [
                "red-teaming-vulnerabilities-bias",
                "red-teaming-vulnerabilities-toxicity",
              ],
              collapsed: true,
            },
            {
              type: "category",
              label: "Unauthorized Access",
              items: [
                "red-teaming-vulnerabilities-unauthorized-access",
              ],
              collapsed: true,
            },
            {
              type: "category",
              label: "Brand Image",
              items: [
                "red-teaming-vulnerabilities-misinformation",
                "red-teaming-vulnerabilities-intellectual-property",
                "red-teaming-vulnerabilities-excessive-agency",
                "red-teaming-vulnerabilities-robustness",
                "red-teaming-vulnerabilities-competition",
              ],
              collapsed: true,
            },
            {
              type: "category",
              label: "Illegal Risks",
              items: [
                "red-teaming-vulnerabilities-illegal-activity",
                "red-teaming-vulnerabilities-graphic-content",
                "red-teaming-vulnerabilities-personal-safety",
              ],
              collapsed: true,
            },
            "red-teaming-custom-vulnerability",
          ],
          collapsed: false,
        },
      ],
      collapsed: false,
    },
    {
      type: "category",
      label: "Guidelines & Frameworks",
      className: "sidebar-item-icon-guidelines-frameworks",
      items: ["red-teaming-guidelines-framework-introduction","red-teaming-owasp-top-10-for-llms", "red-teaming-nist-ai-rmf"],
      collapsed: false,
    },
    {
      type: "category",
      label: "Others",
      className: "sidebar-item-icon-others",
      items: ["data-privacy"],
      collapsed: false,
    },
  ],
};
