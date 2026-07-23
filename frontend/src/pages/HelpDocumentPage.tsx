import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { BookOpen, Bug, Key, AlertTriangle, Users, HelpCircle, ShieldCheck, Settings2, Bot, Sparkles } from 'lucide-react';
import Header from '../components/Header';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { docVariant, isDocSiteMode } from '@/config/privateModules';

// Document baseNames that support the "variant" suffix (the same doc has different versions per release)
const VARIANT_AWARE_BASENAMES = new Set([
  'index',
  'case-studies',
  'contributing',
  'prompt-eval',
  'agent-scan',
]);

// Generate the file name based on the doc variant (openSource / pro / internal, etc.) and language
const getFileName = (baseName: string, language?: string): string => {
  let suffix = '';
  if (docVariant === 'openSource') {
    suffix = '_openSource';
  } else if (docVariant === 'pro' && VARIANT_AWARE_BASENAMES.has(baseName)) {
    suffix = '_pro';
  }
  // Other variants (e.g. internal) keep no suffix and read the generic doc

  if (language === 'en') {
    suffix += '_en';
  }

  return `${baseName}${suffix}.md`;
};

// Append a language suffix to plain file names
const getLocalizedFileName = (fileName: string, language?: string): string => {
  if (language === 'en') {
    const nameWithoutExt = fileName.replace('.md', '');
    return `${nameWithoutExt}_en.md`;
  }
  return fileName;
};

interface MenuItem {
  title: string;
  file: string;
  icon: React.ReactNode;
}
interface MenuConfigItem {
  titleKey: string;
  icon: React.ComponentType<{ className?: string }>;
  getFileNameByLanguage: (language?: string) => string;
}
const menuConfigList: MenuConfigItem[] = [
  {
    titleKey: 'help.welcome',
    icon: BookOpen,
    getFileNameByLanguage: language => getFileName('index', language),
  },
  {
    titleKey: 'help.quickStart',
    icon: Settings2,
    getFileNameByLanguage: language => getLocalizedFileName('getting-started.md', language),
  },
  {
    titleKey: 'help.agentScan',
    icon: Bot,
    getFileNameByLanguage: language => getFileName('agent-scan', language),
  },
  {
    titleKey: 'help.skillScan',
    icon: Sparkles,
    getFileNameByLanguage: language => getLocalizedFileName('skill-scan.md', language),
  },
  {
    titleKey: 'help.mcpScan',
    icon: Bug,
    getFileNameByLanguage: language => getLocalizedFileName('mcp-scan.md', language),
  },
  {
    titleKey: 'help.promptEval',
    icon: Key,
    getFileNameByLanguage: language => getFileName('prompt-eval', language),
  },
  {
    titleKey: 'help.aiInfraScan',
    icon: ShieldCheck,
    getFileNameByLanguage: language => getLocalizedFileName('ai-infra-scan.md', language),
  },
  {
    titleKey: 'help.caseStudies',
    icon: AlertTriangle,
    getFileNameByLanguage: language => getFileName('case-studies', language),
  },
  {
    titleKey: 'help.contributing',
    icon: Users,
    getFileNameByLanguage: language => getFileName('contributing', language),
  },
  {
    titleKey: 'help.faq',
    icon: HelpCircle,
    getFileNameByLanguage: language => getLocalizedFileName('faq.md', language),
  },
];
const getSwitchedLanguageFileName = (fileName: string, language?: string): string => {
  if (language === 'en') {
    if (fileName.endsWith('_en.md')) {
      return fileName;
    }
    return fileName.replace('.md', '_en.md');
  }
  return fileName.replace('_en.md', '.md');
};

const HelpDocumentPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const githubRepoUrl = 'https://github.com/Tencent/AI-Infra-Guard';
  const baseUrl = import.meta.env.BASE_URL || '/';
  const docsBaseUrl = `${baseUrl.replace(/\/$/, '')}/aigdocs/docs`;
  const backButtonText = isDocSiteMode ? t('help.backToGithub') : undefined;
  const handleBackClick = () => {
    if (isDocSiteMode) {
      window.location.href = githubRepoUrl;
      return;
    }
    window.location.href = '/';
  };
  const previousLanguageRef = useRef<string>(i18n.language);
  const defaultMenuFile = menuConfigList[0].getFileNameByLanguage(i18n.language);
  const menuItems: MenuItem[] = menuConfigList.map((item) => {
    const IconComponent = item.icon;
    return {
      title: t(item.titleKey),
      file: item.getFileNameByLanguage(i18n.language),
      icon: <IconComponent className='w-4 h-4' />,
    };
  });
  const getMenuFileListByLanguage = (language?: string): string[] => {
    return menuConfigList.map(item => item.getFileNameByLanguage(language));
  };
  
  const [selectedMenu, setSelectedMenu] = useState<string>(defaultMenuFile);
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  // Get the menu identifier from URL parameters
  const getMenuFromUrl = (): string => {
    const urlParams = new URLSearchParams(window.location.search);
    const menuParam = urlParams.get('menu');
    if (menuParam) {
      // If the URL parameter has no .md suffix, append it
      const fileName = menuParam.endsWith('.md') ? menuParam : `${menuParam}.md`;

      // Check whether it is one of the menu items
      if (menuItems.some(item => item.file === fileName)) {
        return fileName;
      }

      // Support hidden attack-method pages
      const hiddenPages = [
        'agent-scan-http-config.md'
      ];
      if (hiddenPages.includes(fileName)) {
        return fileName;
      }
    }
    return defaultMenuFile;
  };

  // Update the URL parameters
  const updateUrl = (fileName: string) => {
    const url = new URL(window.location.href);
    // Strip the .md suffix before writing to the URL
    const menuKey = fileName.replace('.md', '');
    url.searchParams.set('menu', menuKey);
    window.history.pushState({}, '', url.toString());
  };

  const loadContent = async (fileName: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${docsBaseUrl}/${fileName}`);
      if (response.ok) {
        const text = await response.text();
        setContent(text);
        
        // After content loads, check whether the URL contains an anchor to jump to
        setTimeout(() => {
          const hash = window.location.hash;
          if (hash) {
            const targetId = hash.substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
              targetElement.scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
              });
            }
          }
        }, 100); // Give the DOM a moment to render
      } else {
        setContent('# 文档加载失败\n\n抱歉，无法加载该文档内容。');
      }
    } catch (error) {
      setContent('# 文档加载失败\n\n抱歉，无法加载该文档内容。');
    }
    setLoading(false);
  };

  useEffect(() => {
    const menuFromUrl = getMenuFromUrl();
    setSelectedMenu(menuFromUrl);
    loadContent(menuFromUrl);
  }, []);
  useEffect(() => {
    const previousLanguage = previousLanguageRef.current;
    if (previousLanguage === i18n.language) {
      return;
    }
    const previousFiles = getMenuFileListByLanguage(previousLanguage);
    const nextFiles = getMenuFileListByLanguage(i18n.language);
    const currentIndex = previousFiles.findIndex((file) => file === selectedMenu);
    const nextFileName = currentIndex >= 0
      ? nextFiles[currentIndex]
      : getSwitchedLanguageFileName(
          selectedMenu,
          i18n.language,
        );
    previousLanguageRef.current = i18n.language;
    setSelectedMenu(nextFileName);
    updateUrl(nextFileName);
    loadContent(nextFileName);
  }, [i18n.language]);

  // Listen for the browser's forward/back buttons
  useEffect(() => {
    const handlePopState = () => {
      const menuFromUrl = getMenuFromUrl();
      setSelectedMenu(menuFromUrl);
      loadContent(menuFromUrl);
    };

    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const handleMenuClick = (fileName: string) => {
    setSelectedMenu(fileName);
    updateUrl(fileName);
    loadContent(fileName);
  };



  return (
    <div className="min-h-screen bg-gray-50">
      <Header
        backButtonText={backButtonText}
        onBackClick={handleBackClick}
        backButtonLeftSlot={<LanguageSwitcher />}
      />

      {/* Content area */}
      <div className="w-full h-[calc(100vh-80px)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 h-full">
          <div className="flex gap-6 h-full">
            {/* Left-hand menu */}
            <div className="w-64 flex-shrink-0">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 h-fit">
                <div className="p-4">
                  <nav className="space-y-1">
                    {menuItems.map((item) => (
                      <button
                        key={item.file}
                        onClick={() => handleMenuClick(item.file)}
                        className={`w-full flex items-center px-3 py-2 text-sm rounded-md transition-colors ${
                          selectedMenu === item.file
                            ? 'bg-blue-100 text-blue-900 border border-blue-200'
                            : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                        }`}
                      >
                        <span className="mr-3">{item.icon}</span>
                        {item.title}
                      </button>
                    ))}
                  </nav>
                </div>
              </div>
            </div>

            {/* Right-hand content */}
            <div className="flex-1 overflow-y-auto scrollbar-hover">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-6">
                  {loading ? (
                    <div className="flex items-center justify-center h-64">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      <span className="ml-3 text-gray-600">加载中...</span>
                    </div>
                  ) : (
                    <div className="prose prose-gray max-w-none">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeRaw]}
                        components={{
                          h1: ({ children }) => {
                            const id = String(children).toLowerCase().replace(/\s+/g, '-').replace(/[^\w\u4e00-\u9fff\-]/g, '');
                            return (
                              <h1 id={id} className="text-3xl font-bold text-gray-900 mb-6 border-b border-gray-200 pb-4">
                                {children}
                              </h1>
                            );
                          },
                          h2: ({ children }) => {
                            const id = String(children).toLowerCase().replace(/\s+/g, '-').replace(/[^\w\u4e00-\u9fff\-]/g, '');
                            return (
                              <h2 id={id} className="text-2xl font-semibold text-gray-900 mt-8 mb-4">
                                {children}
                              </h2>
                            );
                          },
                          h3: ({ children }) => {
                            const id = String(children).toLowerCase().replace(/\s+/g, '-').replace(/[^\w\u4e00-\u9fff\-]/g, '');
                            return (
                              <h3 id={id} className="text-xl font-medium text-gray-900 mt-6 mb-3">
                                {children}
                              </h3>
                            );
                          },
                          p: ({ children }) => (
                            <p className="text-gray-700 mb-4 leading-relaxed">
                              {children}
                            </p>
                          ),
                          ul: ({ children }) => (
                            <ul className="list-disc list-inside text-gray-700 mb-4">
                              {children}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="list-decimal list-inside text-gray-700 mb-4">
                              {children}
                            </ol>
                          ),
                          li: ({ children }) => (
                            <li className="text-gray-700 [&>p]:mb-0">
                              {children}
                            </li>
                          ),
                          img: ({ src, alt, ...props }) => {
                            // Handle relative-path images
                            let imageSrc = src;
                            if (src && !src.startsWith('http') && !src.startsWith('data:')) {
                              // Convert relative paths to absolute paths
                              if (src.startsWith('./')) {
                                imageSrc = `${docsBaseUrl}${src.substring(1)}`;
                              } else if (src.startsWith('../')) {
                                imageSrc = `${docsBaseUrl}/${src.substring(3)}`;
                              } else if (!src.startsWith('/')) {
                                imageSrc = `${docsBaseUrl}/${src}`;
                              } else {
                                imageSrc = `${docsBaseUrl}${src}`;
                              }
                            }
                            
                            return (
                              <img
                                src={imageSrc}
                                alt={alt}
                                className="max-w-full h-auto rounded-lg shadow-sm border border-gray-200 my-4"
                                {...props}
                              />
                            );
                          },
                          code: ({ children, className }) => {
                            const isInline = !className;
                            if (isInline) {
                              return (
                                <code className='bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-sm font-mono'>
                                  {children}
                                </code>
                              );
                            }
                            
                            // Extract the language identifier
                            const match = /language-(\w+)/.exec(className || '');
                            const language = match ? match[1] : '';

                            // If it is a shell-related language, use bash highlighting
                            const highlightLanguage = language === 'shell' || language === 'bash' || language === 'sh' || language === 'zsh' ? 'bash' : language;
                            
                            return (
                              <SyntaxHighlighter
                                language={highlightLanguage}
                                style={tomorrow}
                                customStyle={{
                                  margin: 0,
                                  borderRadius: '0.5rem',
                                  fontSize: '0.875rem',
                                  lineHeight: '1.5',
                                }}
                                showLineNumbers={true}
                                wrapLines={true}
                              >
                                {String(children).replace(/\n$/, '')}
                              </SyntaxHighlighter>
                            );
                          },
                          blockquote: ({ children }) => (
                            <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 mb-4">
                              {children}
                            </blockquote>
                          ),
                          table: ({ children }) => (
                            <div className="overflow-x-auto mb-4 scrollbar-hover">
                              <table className="min-w-full border border-gray-300">
                                {children}
                              </table>
                            </div>
                          ),
                          th: ({ children, ...props }) => (
                            <th className="border border-gray-300 px-4 py-2 bg-gray-50 font-medium text-left" {...props}>
                              {children}
                            </th>
                          ),
                          td: ({ children, ...props }) => (
                            <td className="border border-gray-300 px-4 py-2" {...props}>
                              {children}
                            </td>
                          ),
                          a: ({ children, href }) => {
                            // Handle internal anchor links
                            if (href && href.startsWith('#')) {
                              return (
                                <a
                                  href={href}
                                  className="text-blue-600 hover:text-blue-800 underline cursor-pointer"
                                  onClick={(e) => {
                                    e.preventDefault();
                                    const targetId = href.substring(1);
                                    
                                    // Update the hash in the URL
                                    const url = new URL(window.location.href);
                                    url.hash = href;
                                    window.history.pushState({}, '', url.toString());
                                    
                                    // Function that scrolls to the target element
                                    const scrollToTarget = () => {
                                      // Decode the URL-encoded ID
                                      const decodedTargetId = decodeURIComponent(targetId);
                                      const targetElement = document.getElementById(decodedTargetId);
                                      
                                      if (targetElement) {
                                        // Locate the scrolling container
                                        const scrollContainer = document.querySelector('.overflow-y-auto');
                                        if (scrollContainer) {
                                          // Compute the target element's position relative to the scroll container
                                          const containerRect = scrollContainer.getBoundingClientRect();
                                          const targetRect = targetElement.getBoundingClientRect();
                                          const scrollTop = scrollContainer.scrollTop + (targetRect.top - containerRect.top);
                                          
                                          scrollContainer.scrollTo({
                                            top: scrollTop,
                                            behavior: 'smooth'
                                          });
                                        } else {
                                          // Fall back to the default behavior
                                          targetElement.scrollIntoView({ 
                                            behavior: 'smooth',
                                            block: 'start'
                                          });
                                        }
                                        return true;
                                      }
                                      return false;
                                    };
                                    
                                    // Try to scroll immediately
                                    if (!scrollToTarget()) {
                                      // If it cannot be found immediately, retry on the next event loop
                                      setTimeout(() => {
                                        if (!scrollToTarget()) {
                                          // If it is still not found, wait for one more event loop
                                          setTimeout(() => {
                                            scrollToTarget();
                                          }, 50);
                                        }
                                      }, 10);
                                    }
                                  }}
                                >
                                  {children}
                                </a>
                              );
                            }
                            
                            // External link
                            return (
                              <a
                                href={href}
                                className="text-blue-600 hover:text-blue-800 underline"
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {children}
                              </a>
                            );
                          },
                          strong: ({ children }) => (
                            <strong className="font-semibold text-gray-900">
                              {children}
                            </strong>
                          ),
                          em: ({ children }) => (
                            <em className="italic text-gray-700">
                              {children}
                            </em>
                          ),
                        }}
                      >
                        {content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HelpDocumentPage; 