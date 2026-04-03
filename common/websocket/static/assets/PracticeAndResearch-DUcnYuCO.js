import{u as d,j as e}from"./main-CxUmbQGI.js";const y={practicalCases:[{id:5,title:"当Agent 开始自主行动，如何拯救这场信任危机：基于朱雀A.I.G平台落地的TME-Claw安全实践",image:"/images/practice.png",author:"derrickjhli",date:"2026-03-26",url:"https://km.woa.com/articles/show/651723"},{id:1,title:"用先进底座重构业务防线：基于朱雀A.I.G大模型安全工程化落地实践并开源",image:"/images/openai_style_light_02.png",author:"bridgecheng & leonclwu",date:"2026-01-27",url:"https://km.woa.com/articles/show/651723"}],latestResearch:[{id:4,title:"从4.8 亿下载量的 LiteLLM投毒事件，看 AI 基础设施安全攻与防",image:"/images/article-pic.jpeg",author:"simzheng & fyoungguo",date:"2025-03-25",url:"https://km.woa.com/articles/show/638079"},{id:2,title:"拥抱 Agent 时代：如何一键给你的 OpenClaw 做安全体检",image:"/images/aritcle-15.png",author:"nickyccwu",date:"2026-03-05",url:"https://km.woa.com/articles/show/653949"},{id:3,title:"Agent的技能“陷阱”：Skills安全性深度剖析",image:"/images/comfyui_vulnerability_new.png",author:"nickyccwu",date:"2026-01-14",url:"https://km.woa.com/articles/show/650837"}]};function j({title:a,showViewAll:t=!1}){const{t:s}=d();return e.jsxs("div",{className:"flex items-center justify-center mb-12 relative",children:[e.jsx("h2",{className:"text-4xl font-bold text-blue-800 text-center",children:a}),t&&e.jsxs("a",{href:"#",className:"absolute right-0 inline-flex items-center text-blue-600 hover:text-blue-700 font-medium transition-colors duration-200 hover:underline",children:[s("practiceAndResearch.viewAll"),e.jsx("svg",{className:"ml-2 h-4 w-4",fill:"none",stroke:"currentColor",viewBox:"0 0 24 24",children:e.jsx("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M9 5l7 7-7 7"})})]})]})}function w({title:a,image:t,author:s,date:r,url:i,isReversed:l=!1}){const{t:u}=d(),h=g=>{const c=new Date(g),m=c.getFullYear(),n=c.getMonth()+1,o=c.getDate();return u("practiceAndResearch.dateFormat.year")==="年"?`${m}年${n}月${o}日`:`${n}/${o}/${m}`};return e.jsx("div",{className:"border-b border-gray-100 last:border-b-0 pb-6 last:pb-0",children:e.jsx("a",{href:i,target:"_blank",className:"group block rounded-xl focus:outline-none focus:ring-0 focus:ring-offset-0",children:e.jsxs("div",{className:`flex items-center gap-10 ${l?"flex-row-reverse":"flex-row"} max-md:flex-col max-md:gap-3`,children:[e.jsx("div",{className:"flex-shrink-0 max-md:w-full",style:{width:"18rem"},children:e.jsx("div",{className:"aspect-video w-full overflow-hidden rounded-lg",children:e.jsx("img",{src:t,alt:a,className:"w-full h-full object-cover transition-transform duration-400 group-hover:scale-105",loading:"lazy"})})}),e.jsxs("div",{className:`flex-1 max-md:text-center ${l?"text-right justify-end":"text-left justify-start"}`,children:[e.jsx("h3",{className:"text-base font-semibold text-gray-700 leading-tight mb-4",children:a}),e.jsxs("div",{className:`flex items-center gap-4 text-sm text-gray-600 max-md:justify-center ${l?"justify-end":"justify-start"}`,children:[e.jsx("span",{className:"font-medium",children:s}),e.jsx("span",{className:"w-1 h-1 bg-gray-400 rounded-full"}),e.jsx("time",{className:"text-gray-400",dateTime:r,children:h(r)})]})]})]})})})}function v({title:a,image:t,author:s,date:r,url:i,height:l="medium"}){const{t:u}=d(),h=n=>{const o=new Date(n),x=o.getFullYear(),f=o.getMonth()+1,p=o.getDate();return u("practiceAndResearch.dateFormat.year")==="年"?`${x}年${f}月${p}日`:`${f}/${p}/${x}`},g=()=>{switch(l){case"short":return"h-40";case"medium":return"h-52";case"tall":return"h-64";default:return"h-52"}},c=n=>{n.currentTarget.style.transform="scale(1.03)"},m=n=>{n.currentTarget.style.transform="scale(1)"};return e.jsxs("a",{href:i,target:"_blank",className:"group block bg-white rounded-lg overflow-hidden shadow-sm focus:outline-none focus:ring-0 focus:ring-offset-0 break-inside-avoid",children:[e.jsx("div",{className:`w-full overflow-hidden ${g()}`,children:e.jsx("img",{src:t,alt:a,className:"w-full h-full object-cover transition-transform duration-400",loading:"lazy",onMouseEnter:c,onMouseLeave:m})}),e.jsxs("div",{className:"p-5",children:[e.jsx("h3",{className:"text-base font-semibold text-gray-600 leading-snug mb-2",children:a}),e.jsxs("div",{className:"flex items-center justify-between text-gray-600 mt-4",children:[e.jsx("span",{children:s}),e.jsx("time",{className:"text-gray-400",dateTime:r,children:h(r)})]})]})]})}const N=()=>{const{t:a}=d();return e.jsxs("div",{className:"bg-transparent",children:[e.jsxs("div",{className:"max-w-7xl mx-auto px-8 pb-8",children:[e.jsxs("section",{style:{marginBottom:"10rem"},children:[e.jsx(j,{title:a("practiceAndResearch.practicalCases")}),e.jsx("div",{className:"space-y-12",children:y.practicalCases.map((t,s)=>e.jsx(w,{title:t.title,image:t.image,author:t.author,date:t.date,url:t.url,isReversed:s%2===1},t.id))})]}),e.jsxs("section",{style:{marginBottom:"10rem"},children:[e.jsx(j,{title:a("practiceAndResearch.latestResearch")}),e.jsx("div",{className:"masonry-container",children:y.latestResearch.map((t,s)=>{const r=["medium","tall","short","medium","tall"],i=r[s%r.length];return e.jsx(v,{title:t.title,image:t.image,author:t.author,date:t.date,url:t.url,height:i},t.id)})}),e.jsx("div",{className:"mt-6 flex justify-center",children:e.jsxs("a",{href:"https://km.woa.com/knowledge/9932",target:"_blank",rel:"noopener noreferrer",className:"inline-flex items-center text-blue-600 hover:text-blue-700 font-medium transition-colors duration-200 hover:underline",children:["更多文章",e.jsx("svg",{className:"ml-2 h-4 w-4",fill:"none",stroke:"currentColor",viewBox:"0 0 24 24",children:e.jsx("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M9 5l7 7-7 7"})})]})})]})]}),e.jsx("style",{dangerouslySetInnerHTML:{__html:`
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
        `}})]})};export{N as default};
