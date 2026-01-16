import{u as d,j as e}from"./main-CmD5MGGY.js";const y={practicalCases:[{id:13,title:"Agent的技能“陷阱”：Skills安全性深度剖析",image:"/images/comfyui_vulnerability_new.png",author:"nickyccwu",date:"2026-01-14",url:"https://km.woa.com/articles/show/650837"},{id:12,title:"能力越强越安全？Gemini 3.0 Pro 安全性全网首测",image:"/images/practice.png",author:"robertzyang",date:"2025-11-20",url:"https://km.woa.com/articles/show/642703"},{id:11,title:"企业MCP安全风险地图：5大高频安全风险场景",image:"/images/article-pic.jpeg",author:"fyoungguo",date:"2025-10-13",url:"https://km.woa.com/articles/show/638079"},{id:10,title:"当越狱成为常态：如何为大模型一键安全体检？",image:"/images/vllm_security_research.png",author:"roninhuang",date:"2025-08-21",url:"https://km.woa.com/articles/show/635560"},{id:1,title:"当ChatGPT接入MCP，你的数据是如何被泄露的？",image:"/images/chatgpt_mcp_security_new.png",author:"nickyccwu",date:"2025-06-27",url:"https://km.woa.com/knowledge/9932/node/2"},{id:2,title:"为了检测MCP安全风险，我们开发了一个AI Agent",image:"/images/vllm_vulnerability_circles.png",author:"nickyccwu",date:"2025-04-28",url:"https://km.woa.com/knowledge/9932/node/3"},{id:5,title:"DeepSeek本地化部署有风险！快来看看你中招了吗？",image:"/images/deepseek_deployment_squares.png",author:"pythoncheng",date:"2025-02-13",url:"https://km.woa.com/knowledge/9932/node/14"}],latestResearch:[{id:9,title:"AI Agent安全最佳实践 | AI+安全课程",image:"/images/mcp_security_agent_clean copy.png",author:"nickyccwu",date:"2025-07-31",url:"https://km.woa.com/articles/show/634236"},{id:3,title:"朱雀实验室协助vLLM修复CVSS 9.8分严重漏洞",image:"/images/pytorch_framework_security_clean.png",author:"kikayli",date:"2025-05-21",url:"https://km.woa.com/knowledge/9932/node/19"},{id:4,title:"如何避免AI Agent被劫持：深入剖析MCP+A2A安全性",image:"/images/ai_agent_protection_new copy.png",author:"nickyccwu",date:"2025-04-11",url:"https://km.woa.com/knowledge/9932/node/4"},{id:8,title:"爆红黑悟空AI暗藏风险，ComfyUI惊现数据泄露严重漏洞，鹅厂亦中招",image:"/images/option4_light_peach_tea.png",author:"leojyang",date:"2024-08-30",url:"https://km.woa.com/knowledge/9932/node/9"},{id:7,title:"大模型基础设施安全：PyTorch 分布式框架安全风险剖析",image:"/images/comfyui_vulnerability_new copy.png",author:"alienli",date:"2024-05-30",url:"https://km.woa.com/knowledge/9932/node/6"},{id:6,title:"鹅厂获英伟达致谢，发现高危安全漏洞可能导致2万+企业AI模型数据泄露",image:"/images/nvidia_security_discovery_new.png",author:"leojyang",date:"2024-02-23",url:"https://km.woa.com/knowledge/9932/node/10"}]};function w({title:a,showViewAll:t=!1}){const{t:s}=d();return e.jsxs("div",{className:"flex items-center justify-between mb-6",children:[e.jsx("h2",{className:"text-2xl font-semibold text-gray-900",children:a}),t&&e.jsxs("a",{href:"#",className:"inline-flex items-center text-blue-600 hover:text-blue-700 font-medium transition-colors duration-200 hover:underline",children:[s("practiceAndResearch.viewAll"),e.jsx("svg",{className:"ml-2 h-4 w-4",fill:"none",stroke:"currentColor",viewBox:"0 0 24 24",children:e.jsx("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M9 5l7 7-7 7"})})]})]})}function j({title:a,image:t,author:s,date:n,url:i,isReversed:l=!1}){const{t:u}=d(),h=g=>{const c=new Date(g),m=c.getFullYear(),r=c.getMonth()+1,o=c.getDate();return u("practiceAndResearch.dateFormat.year")==="年"?`${m}年${r}月${o}日`:`${r}/${o}/${m}`};return e.jsx("div",{className:"border-b border-gray-100 last:border-b-0 pb-6 last:pb-0",children:e.jsx("a",{href:i,target:"_blank",className:"group block rounded-xl focus:outline-none focus:ring-0 focus:ring-offset-0",children:e.jsxs("div",{className:`flex items-center gap-10 ${l?"flex-row-reverse":"flex-row"} max-md:flex-col max-md:gap-3`,children:[e.jsx("div",{className:"flex-shrink-0 max-md:w-full",style:{width:"18rem"},children:e.jsx("div",{className:"aspect-video w-full overflow-hidden rounded-lg",children:e.jsx("img",{src:t,alt:a,className:"w-full h-full object-cover transition-transform duration-400 group-hover:scale-105",loading:"lazy"})})}),e.jsxs("div",{className:`flex-1 max-md:text-center ${l?"text-right justify-end":"text-left justify-start"}`,children:[e.jsx("h3",{className:"text-base font-semibold text-gray-700 leading-tight mb-4",children:a}),e.jsxs("div",{className:`flex items-center gap-4 text-sm text-gray-600 max-md:justify-center ${l?"justify-end":"justify-start"}`,children:[e.jsx("span",{className:"font-medium",children:s}),e.jsx("span",{className:"w-1 h-1 bg-gray-400 rounded-full"}),e.jsx("time",{className:"text-gray-400",dateTime:n,children:h(n)})]})]})]})})})}function b({title:a,image:t,author:s,date:n,url:i,height:l="medium"}){const{t:u}=d(),h=r=>{const o=new Date(r),x=o.getFullYear(),p=o.getMonth()+1,f=o.getDate();return u("practiceAndResearch.dateFormat.year")==="年"?`${x}年${p}月${f}日`:`${p}/${f}/${x}`},g=()=>{switch(l){case"short":return"h-40";case"medium":return"h-52";case"tall":return"h-64";default:return"h-52"}},c=r=>{r.currentTarget.style.transform="scale(1.03)"},m=r=>{r.currentTarget.style.transform="scale(1)"};return e.jsxs("a",{href:i,target:"_blank",className:"group block bg-white rounded-lg overflow-hidden shadow-sm focus:outline-none focus:ring-0 focus:ring-offset-0 break-inside-avoid",children:[e.jsx("div",{className:`w-full overflow-hidden ${g()}`,children:e.jsx("img",{src:t,alt:a,className:"w-full h-full object-cover transition-transform duration-400",loading:"lazy",onMouseEnter:c,onMouseLeave:m})}),e.jsxs("div",{className:"p-5",children:[e.jsx("h3",{className:"text-base font-semibold text-gray-600 leading-snug mb-2",children:a}),e.jsxs("div",{className:"flex items-center justify-between text-gray-600 mt-4",children:[e.jsx("span",{children:s}),e.jsx("time",{className:"text-gray-400",dateTime:n,children:h(n)})]})]})]})}const k=()=>{const{t:a}=d();return e.jsxs("div",{className:"bg-transparent",children:[e.jsxs("div",{className:"max-w-7xl mx-auto px-8 pb-8",children:[e.jsxs("section",{style:{marginBottom:"10rem"},children:[e.jsx(w,{title:a("practiceAndResearch.practicalCases")}),e.jsx("div",{className:"space-y-6",children:y.practicalCases.map((t,s)=>e.jsx(j,{title:t.title,image:t.image,author:t.author,date:t.date,url:t.url,isReversed:s%2===1},t.id))})]}),e.jsxs("section",{style:{marginBottom:"10rem"},children:[e.jsx(w,{title:a("practiceAndResearch.latestResearch")}),e.jsx("div",{className:"masonry-container",children:y.latestResearch.map((t,s)=>{const n=["medium","tall","short","medium","tall"],i=n[s%n.length];return e.jsx(b,{title:t.title,image:t.image,author:t.author,date:t.date,url:t.url,height:i},t.id)})})]})]}),e.jsx("section",{className:"pb-16 relative",children:e.jsxs("div",{className:" px-8 pb-16",children:[e.jsxs("div",{className:"mb-6 text-center",children:[e.jsx("h2",{className:"text-4xl font-bold bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-800 bg-clip-text text-transparent mb-4",children:a("practiceAndResearch.contributors")}),e.jsx("p",{className:"text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed",children:a("practiceAndResearch.contributorsDescription")})]}),e.jsxs("div",{className:"flex justify-center items-center gap-10 max-w-[1000px] mx-auto mt-10",children:[e.jsx("div",{className:"bg-white rounded-2xl p-10 shadow-md hover:shadow-lg transition-shadow duration-300 flex-1 flex items-center justify-center",children:e.jsx("img",{src:"/images/keen_lab_logo.svg",alt:"Keen Security Lab",className:"h-12 w-auto object-contain"})}),e.jsx("div",{className:"bg-white rounded-2xl p-10 shadow-md hover:shadow-lg transition-shadow duration-300 flex-1 flex items-center justify-center",children:e.jsx("img",{src:"/images/wechat_security.png",alt:"WeChat Security",className:"h-12 w-auto object-contain"})}),e.jsx("div",{className:"bg-white rounded-2xl p-10 shadow-md hover:shadow-lg transition-shadow duration-300 flex-1 flex items-center justify-center",children:e.jsx("img",{src:"/images/fit_security_logo.png",alt:"Fit Security",className:"h-12 w-auto object-contain"})})]})]})}),e.jsx("style",{dangerouslySetInnerHTML:{__html:`
                  /* Masonry Layout Styles */
        .masonry-container {
          column-count: 3;
          column-gap: 1.6rem;
          column-fill: balance;
        }

        .masonry-container > * {
          break-inside: avoid;
          margin-bottom: 1.6rem;
          width: 100%;
        }

        /* Responsive masonry */
        @media (max-width: 1280px) {
          .masonry-container {
            column-count: 2;
          }
        }

        @media (max-width: 1024px) {
          .masonry-container {
            column-count: 2;
          }
        }

        @media (max-width: 640px) {
          .masonry-container {
            column-count: 1;
            column-gap: 0;
          }
        }

        /* Remove focus borders completely */
        a:focus {
          outline: none !important;
          box-shadow: none !important;
        }
        
        a:focus-visible {
          outline: none !important;
          box-shadow: none !important;
        }

        /* Ensure hover effects work in masonry layout */
        .masonry-container a:hover img {
          transform: scale(1.03) !important;
          transition: transform 0.4s ease !important;
        }
        
        /* Force hover effect for all masonry images */
        .masonry-container .group:hover img {
          transform: scale(1.03) !important;
          transition: transform 0.4s ease !important;
        }
        
        /* Direct targeting of masonry images */
        .masonry-container .masonry-image:hover {
          transform: scale(1.03) !important;
          transition: transform 0.4s ease !important;
        }
        
        .masonry-container a:hover .masonry-image {
          transform: scale(1.03) !important;
          transition: transform 0.4s ease !important;
        }
        `}})]})};export{k as default};
