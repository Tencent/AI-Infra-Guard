// const remarkMath = require('remark-math');
// const rehypeKatex = require('rehype-katex');
const remarkMathModule = import("remark-math");
const rehypeKatexModule = import("rehype-katex");
/** @type {import('@docusaurus/types').Config} */

module.exports = {
  plugins: [
    "docusaurus-plugin-sass",
  ]
  ,

  title: "DeepTeam - The Open-Source LLM Red Teaming Framework",
  tagline: "Red Teaming Framework for LLMs",
  favicon: "img/fav.ico",

  // Set the production url of your site here
  url: "https://trydeepteam.com",
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: "/",

  onBrokenLinks: "warn",
  onBrokenMarkdownLinks: "warn",

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "@docusaurus/preset-classic",
      {
        docs: {
          path: "docs",
          editUrl:
            "https://github.com/confident-ai/deepteam/edit/main/docs/",
          showLastUpdateAuthor: true,
          showLastUpdateTime: true,
          sidebarPath: require.resolve("./sidebars.js"),
          remarkPlugins: [remarkMathModule],
          rehypePlugins: [rehypeKatexModule],
        },
        theme: {
          customCss: require.resolve("./src/css/custom.scss"),
        },
        gtag: {
          trackingID: "G-N2EGDDYG9M",
          anonymizeIP: false,
        },
      },
    ],
  ],
  scripts: [
    {
      src: "https://plausible.io/js/script.tagged-events.js",
      defer: true,
      "data-domain": "trydeepteam.com",
    },
    // {
    //   src: "https://unpkg.com/lucide@latest",
    //   async: true,
    // },
    // {
    //   src: "/js/lucide-icons.js",
    //   async: true,
    // },
  ],
  stylesheets: [
    {
      href: "https://cdn.jsdelivr.net/npm/katex@0.13.24/dist/katex.min.css",
      type: "text/css",
      integrity:
        "sha384-odtC+0UGzzFL/6PNoE8rX/SPcQDXBJ+uRepguP4QkPCm2LBxH3FA3y+fKSiJ+AmM",
      crossorigin: "anonymous",
    },
    {
      href: "https://fonts.googleapis.com/css2?family=Lexend+Deca:wght@500&display=swap",
      type: "text/css",
    },
  ],
  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: "img/social_card.png",
      navbar: {
        logo: {
          alt: "DeepTeam Logo",
          src: "icons/DeepTeam.svg",
        },
        items: [
          {
            to: "docs/getting-started",
            position: "left",
            label: "Docs",
            activeBasePath: 'docs',
          },
          {to: 'blog', label: 'Blog', position: 'left'},
          // {
          //   href: "https://confident-ai.com/book-a-demo",
          //   className: "header-confident-link",
          //   position: "right",
          //   label: 'Try DeepTeam Cloud',
          // },
          {
            href: "https://discord.gg/3SEyvpgu2f",
            className: "header-discord-link",
            position: "right",
          },
          {
            href: "https://github.com/confident-ai/deepteam",
            position: "right",
            className: "header-github-link",
          },
        ],
      },
      algolia: {
        appId: "7U9PQIW1ZA",
        apiKey: "fb799aeac8bcd0f6b9e0e233a385ad33",
        indexName: "confident-ai",
        contextualSearch: true,
      },
      colorMode: {
        defaultMode: "light",
        disableSwitch: false,
        respectPrefersColorScheme: false,
      },
      announcementBar: {
        id: "announcementBar-1",
        content:
          '⭐️ If you like DeepTeam, give it a star on <a target="_blank" rel="noopener noreferrer" href="https://github.com/confident-ai/deepteam">GitHub</a>! ⭐️',
        backgroundColor: "#ff006b",
        textColor: "#000",
      },
      footer: {
        style: "dark",
        links: [
          {
            title: "Documentation",
            items: [
              {
                label: "Introduction",
                to: "/docs/getting-started",
              },
            ],
          },
          {
            title: "Articles You Must Read",
            items: [
              {
                label: "How to jailbreak LLMs",
                to: "https://www.confident-ai.com/blog/how-to-jailbreak-llms-one-step-at-a-time",
              },
              {label: "OWASP Top 10 for LLMs", to: "https://www.confident-ai.com/blog/owasp-top-10-2025-for-llm-applications-risks-and-mitigation-techniques"},
              {label: "The comprehensive LLM safety guide", to: "https://www.confident-ai.com/blog/the-comprehensive-llm-safety-guide-navigate-ai-regulations-and-best-practices-for-llm-safety"},
              {label: "LLM evaluation metrics", to: "https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation"},
            ],
          },
          {
            title: "Red Teaming Community",
            items: [
              {
                label: "GitHub",
                to: "https://github.com/confident-ai/deepteam",
              },
              {
                label: "Discord",
                to: "https://discord.gg/a3K9c8GRGt",
              },
              {
                label: "Newsletter",
                to: "https://confident-ai.com/blog",
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Confident AI Inc. Built with ❤️ and confidence.`,
      },
      prism: {
        theme: require("prism-react-renderer/themes/nightOwl"),
        additionalLanguages: ["python"],
        magicComments: [
          {
            className: "theme-code-block-highlighted-line",
            line: "highlight-next-line",
            block: { start: "highlight-start", end: "highlight-end" },
          },
          {
            className: "code-block-error-message",
            line: "highlight-next-line-error-message",
          },
          {
            className: "code-block-info-line",
            line: "highlight-next-line-info",
            block: {
              start: "highlight-info-start",
              end: "highlight-info-end",
            },
          },
        ],
      },
    }),
};
