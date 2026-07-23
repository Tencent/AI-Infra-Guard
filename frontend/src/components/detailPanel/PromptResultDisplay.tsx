import React, { useState, useEffect, useLayoutEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { 
  AlertTriangle,
  FileText,
  BookOpen,
  Shield,
  Info,
  Copy,
  MessageSquare,
  Download,
  ArrowUp
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '../ui/tooltip';
import CodeHighlight from './CodeHighlight';
import RadarChartComponent from './RadarChart';

// Add CSS animation styles
const headerStyles = `
  @keyframes pulse {
    0%, 100% { opacity: 0.3; transform: scale(1); }
    50% { opacity: 0.1; transform: scale(1.1); }
  }
`;

interface ResultItem {
  modelName?: string;
  status?: string;
  vulnerability?: string;
  attackMethod?: string;
  input?: string;
  originalInput?: string;
  output?: string;
  reason?: string;
}

interface ResultDisplayProps {
  title: string;
  titleIcon: React.ReactNode;
  content: any;
  msgType?: string;
  onDownload?: (fileUrl: string) => void;
  sessionId?: string;
  isFullscreen?: boolean;
}

const ResultDisplay: React.FC<ResultDisplayProps> = ({
  title,
  titleIcon,
  content,
  msgType,
  onDownload,
  sessionId,
  isFullscreen = false
}) => {
  const { t } = useTranslation();
  // Add CSS styles into <head>
  React.useEffect(() => {
    const styleElement = document.createElement('style');
    styleElement.textContent = headerStyles;
    document.head.appendChild(styleElement);
    
    return () => {
      document.head.removeChild(styleElement);
    };
  }, []);
  const [copied, setCopied] = useState<string>('');
  const [showScrollTop, setShowScrollTop] = useState<boolean>(false);

    // Listen to scroll events - only on the parent container
  useLayoutEffect(() => {
    let ticking = false;
    let scrollableParent: HTMLElement | null = null;
    
    const findScrollableParent = () => {
      const currentElement = document.querySelector('[data-testid="result-display"]') || 
                            document.querySelector('.result-display') ||
                            document.querySelector('[class*="detail-panel"]') ||
                            document.querySelector('[class*="scroll"]');
      
      if (currentElement) {
        let parent = currentElement.parentElement;
        
        while (parent && parent !== document.body) {
          const style = window.getComputedStyle(parent);
          const overflow = style.overflow + style.overflowY + style.overflowX;
          
          if (overflow.includes('scroll') || overflow.includes('auto')) {
            return parent as HTMLElement;
          }
          parent = parent.parentElement;
        }
      }
      return null;
    };
    
    const updateScrollPosition = () => {
      let scrollTop = 0;
      
      if (scrollableParent) {
        scrollTop = scrollableParent.scrollTop;
      } else {
        scrollTop = window.pageYOffset || document.documentElement.scrollTop || 0;
      }
      
      const shouldShow = scrollTop > 30;
      setShowScrollTop(shouldShow);
      ticking = false;
    };
    
    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(updateScrollPosition);
        ticking = true;
      }
    };
    
    // Find the scrollable parent element
    scrollableParent = findScrollableParent();
    
    // Initial check
    updateScrollPosition();
    
    // Add the event listener
    if (scrollableParent) {
      scrollableParent.addEventListener('scroll', handleScroll, { passive: true });
    } else {
      window.addEventListener('scroll', handleScroll, { passive: true });
    }
    
    return () => {
      if (scrollableParent) {
        scrollableParent.removeEventListener('scroll', handleScroll);
      } else {
        window.removeEventListener('scroll', handleScroll);
      }
    };
  }, []);



  // Scroll-to-top function
  const scrollToTop = () => {
    console.log('Scroll to top clicked');
    
    // Find the ResultDisplay's parent and scroll it to the top
    const currentElement = document.querySelector('[data-testid="result-display"]') || 
                          document.querySelector('.result-display') ||
                          document.querySelector('[class*="detail-panel"]') ||
                          document.querySelector('[class*="scroll"]');
    
    if (currentElement) {
      let scrollableParent = currentElement.parentElement;
      
      // Walk up to find the scrollable parent element
      while (scrollableParent && scrollableParent !== document.body) {
        const style = window.getComputedStyle(scrollableParent);
        const overflow = style.overflow + style.overflowY + style.overflowX;
        
        if ((overflow.includes('scroll') || overflow.includes('auto')) && scrollableParent.scrollTop > 0) {
          console.log('Scrolling parent element to top:', scrollableParent.className, scrollableParent.scrollTop);
          scrollableParent.scrollTo({
            top: 0,
            behavior: 'smooth'
          });
          return;
        }
        scrollableParent = scrollableParent.parentElement;
      }
    }
    
    // If no scrollable parent is found, scroll the window
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };

  // Common helper: determine the safety level from a score
  const getSecurityLevel = (score: number) => {
    if (score < 60) return t('redteam.lowRisk');
    if (score <= 80) return t('redteam.mediumRisk');
    return t('redteam.highRisk');
  };

  // Common helper: determine the safety-level color from a score
  const getSecurityLevelColor = (score: number) => {
    if (score < 60) return 'text-red-600';
    if (score <= 80) return 'text-orange-600';
    return 'text-green-600';
  };

  const handleCopy = async (text: string, key: string) => {
    if (!text) {
      toast.error(t('redteam.copyEmptyError'));
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(''), 1200);
    } catch (e) {
      try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        setCopied(key);
        setTimeout(() => setCopied(''), 1200);
      } catch (err) {
        toast.error(t('redteam.copyFailedError'));
      }
    }
  };

  const handleDownload = async (fileUrl: string) => {
    if (!fileUrl) {
      toast.error(t('redteam.downloadEmptyError'));
      return;
    }
    
    try {
      const response = await fetch(
        sessionId 
          ? `/api/v1/app/tasks/${sessionId}/downloadFile`
          : '/api/v1/app/tasks/downloadFile',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            fileUrl,
          }),
        },
      );
      if (!response.ok) {
        throw new Error(t('redteam.downloadFailedError'));
      }
      const disposition = response.headers.get('Content-Disposition');
      let filename = 'downloaded_file';
      if (disposition) {
        const match = disposition.match(/filename="?([^";]+)"?/);
        if (match && match[1]) {
          filename = decodeURIComponent(match[1]);
        }
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (e) {
              toast.error(t('redteam.fileDownloadFailedError'));
    }
  };

  if (msgType === 'markdown') {
    return (
      <div className="p-4" data-testid="result-display">
        <Card className="border-none shadow-none">
          <CardContent className="p-0">
            <div className="prose prose-sm max-w-none [&_table_td]:align-top">
              <CodeHighlight>
                {typeof content === 'string' ? content : ''}
              </CodeHighlight>
            </div>
          </CardContent>
        </Card>
        
        {/* Back-to-top button */}
        {showScrollTop && (
          <button
            onClick={scrollToTop}
            className="fixed bottom-6 right-6 z-[9999] w-10 h-10 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-xl transition-all duration-300 hover:scale-110 flex items-center justify-center border-2 border-white"
            title={t('redteam.backToTop')}
            style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  if (msgType === 'json') {
    // Handle the case where content is an array
    const contentArray = Array.isArray(content) ? content : [content];
    
    if (!contentArray || contentArray.length === 0) {
      return (
        <div className="p-4">
          <div className="text-sm text-gray-500">{t('redteam.noData')}</div>
        </div>
      );
    }

    // Extract data for all models for the table display
    const allModels = contentArray.flatMap(content => 
      content.results ? content.results.map((item: ResultItem) => ({
        modelName: item.modelName || '-',
        score: content.score || 0,
        total: content.total || 0,
        jailbreakCount: content.jailbreak || 0,
        securityLevel: getSecurityLevel(content.score || 0),
        securityLevelColor: getSecurityLevelColor(content.score || 0)
      })) : []
    );

    // Deduplicate and sort by score
    const uniqueModels = allModels.reduce((acc, model) => {
      const existing = acc.find(m => m.modelName === model.modelName);
      if (!existing) {
        acc.push(model);
      }
      return acc;
    }, [] as typeof allModels).sort((a, b) => b.score - a.score);

    // Reorder contentArray according to the order of uniqueModels
    const sortedContentArray = contentArray.sort((a, b) => {
      const aModelName = a.results?.[0]?.modelName || '';
      const bModelName = b.results?.[0]?.modelName || '';
      const aIndex = uniqueModels.findIndex(model => model.modelName === aModelName);
      const bIndex = uniqueModels.findIndex(model => model.modelName === bModelName);
      return aIndex - bIndex;
    });

    return (
      <div className={`p-4 ${isFullscreen ? 'mt-4' : ''}`} data-testid="result-display">
        <Card className="border-none shadow-none">
          <CardContent className="p-0">
            <h2 className='text-lg font-bold text-center mt-4'>{t('redteam.reportSummary')}</h2>
            <div className="max-w-none [&_table_td]:align-middle">
              {/* Model comparison table */}
              {uniqueModels.length > 0 && (
                <div className="mb-6">
                  <div className="relative">
                    <div className="p-1 sm:p-2 pb-6 -mx-1 sm:mx-0">
                    </div>
                    <table className="w-full border-collapse border-spacing-0 bg-white rounded-2xl overflow-hidden shadow-lg border border-gray-200 [&_td]:border-none [&_th]:border-none [&_td]:align-middle [&_th]:align-middle">
                      <thead>
                        <tr className="text-white border-b border-gray-200" style={{
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                        }}>
                          <th className="px-1 py-4 text-center font-semibold text-xs sm:text-sm whitespace-nowrap" style={{ background: 'transparent' }}>{t('redteam.ranking')}</th>
                          <th className="px-1 py-2 text-left font-semibold text-xs sm:text-sm whitespace-nowrap" style={{ background: 'transparent' }}>{t('redteam.modelName')}</th>
                          <th className="px-1 py-2 text-left font-semibold text-xs sm:text-sm whitespace-nowrap" style={{ background: 'transparent' }}>{t('redteam.securityLevel')}</th>
                          <th className="px-1 py-2 text-left font-semibold text-xs sm:text-sm whitespace-nowrap" style={{ background: 'transparent' }}>{t('redteam.score')}</th>
                          <th className="px-1 py-2 text-left font-semibold text-xs sm:text-sm whitespace-nowrap" style={{ background: 'transparent' }}>{t('redteam.jailbreakSuccessRate')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {uniqueModels.map((model, index) => (
                          <tr key={model.modelName} className="transition-all duration-300 hover:bg-gray-50">
                            <td className="px-1 py-2 text-xs sm:text-sm text-gray-700">
                              <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full text-white flex items-center justify-center font-bold mx-auto text-xs sm:text-sm" style={{
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                        }}>
                                {index + 1}
                              </div>
                            </td>
                            <td className="px-1 py-2 text-xs sm:text-sm font-semibold text-gray-800">
                              <div 
                                className="max-w-full break-words cursor-pointer hover:text-blue-600 transition-colors" 
                                title={model.modelName}
                                onClick={() => {
                                  const targetElement = document.getElementById(`model-detail-${model.modelName}`);
                                  if (targetElement) {
                                    targetElement.scrollIntoView({ 
                                      behavior: 'smooth',
                                      block: 'start'
                                    });
                                  }
                                }}
                              >
                                {model.modelName}
                              </div>
                            </td>
                            <td className="px-1 py-2 text-xs sm:text-sm">
                              <span className={`inline-flex items-center gap-1 sm:gap-2 px-1 sm:px-2 md:px-3 py-1 sm:py-1.5 rounded-full text-xs font-medium ${
                                model.securityLevel === t('redteam.highRisk')
                                  ? 'bg-green-100 text-green-800' 
                                  : model.securityLevel === t('redteam.mediumRisk')
                                    ? 'bg-orange-100 text-orange-800' 
                                    : 'bg-red-100 text-red-800'
                              }`}>
                                <span className={`w-3 h-3 sm:w-4 sm:h-4 rounded-full text-white flex items-center justify-center text-xs ${
                                  model.securityLevel === t('redteam.highRisk')
                                    ? 'bg-green-500' 
                                    : model.securityLevel === t('redteam.mediumRisk')
                                      ? 'bg-orange-500' 
                                      : 'bg-red-500'
                                }`}>
                                  {model.securityLevel === t('redteam.highRisk') ? '✓' : model.securityLevel === t('redteam.mediumRisk') ? '!' : '✗'}
                                </span>
                                <span className="hidden sm:inline">{model.securityLevel}</span>
                                <span className="sm:hidden">{model.securityLevel === t('redteam.highRisk') ? t('redteam.highRisk') : model.securityLevel === t('redteam.mediumRisk') ? t('redteam.mediumRisk') : t('redteam.lowRisk')}</span>
                              </span>
                            </td>
                            <td className="px-1 py-2 text-xs sm:text-sm">
                              <div className="flex items-center gap-2 sm:gap-3">
                                <div className="w-12 sm:w-16 md:w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div 
                                    className={`h-full rounded-full transition-all duration-500 ${
                                      model.securityLevel === t('redteam.highRisk')
                                        ? 'bg-green-500' 
                                        : model.securityLevel === t('redteam.mediumRisk')
                                          ? 'bg-orange-500' 
                                          : 'bg-red-500'
                                    }`}
                                    style={{
                                      width: `${(model.score / 100) * 100}%`
                                    }}
                                  />
                                </div>
                                <div className={`font-bold text-xs sm:text-sm ${
                                  model.securityLevel === t('redteam.highRisk')
                                    ? 'text-green-600' 
                                    : model.securityLevel === t('redteam.mediumRisk')
                                      ? 'text-orange-600' 
                                      : 'text-red-600'
                                }`}>
                                  {model.score}
                                </div>
                              </div>
                            </td>
                            <td className="px-1 py-2 text-xs sm:text-sm">
                              <span className={`inline-flex items-center justify-center px-1 sm:px-2 md:px-3 py-1 sm:py-1.5 rounded-full text-xs font-medium min-w-[28px] sm:min-w-[32px] md:min-w-[40px] text-center ${
                                model.jailbreakCount === 0 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {Math.round(model.jailbreakCount / model.total * 100)}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
               <div className={`text-sm text-gray-400 text-center flex items-center justify-center gap-1 ${uniqueModels.length > 0 ? '-mt-1' : 'mt-4'}`}>
                 <Info className='w-3 h-3' />
                 {uniqueModels.length > 0 ? t('redteam.aiGeneratedNotice') : t('redteam.noValidModelsMessage')}
               </div>

              <div className='flex items-center justify-center mt-10'>
                <h2 className='text-lg font-bold text-center'>{t('redteam.reportDetails')}</h2>
              </div>
              
              <div className='space-y-8'>
                {sortedContentArray.map((jsonContent, contentIdx) => (
                  <div 
                    key={contentIdx} 
                    id={`model-detail-${jsonContent.modelName || jsonContent.results?.[0]?.modelName || contentIdx}`}
                    className='space-y-4 bg-white rounded-2xl shadow-lg border border-gray-100 mt-6'
                  >
                    
                    <div className='flex justify-center w-full'>
                      <div className='flex flex-col w-full'>
                        <div className='relative overflow-hidden rounded-t-2xl mb-6 w-full' style={{
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          padding: '12px',
                          textAlign: 'center',
                          color: 'white'
                        }}>
                          <div className='absolute top-[-50%] left-[-50%] w-[200%] h-[200%] opacity-30' style={{
                            background: 'radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%)',
                            animation: 'pulse 6s ease-in-out infinite'
                          }}></div>
                          <p className='text-xl opacity-90 relative z-10' style={{ fontSize: '1.1rem;font-weight:700' }}>
                            {jsonContent.modelName || jsonContent.results[0].modelName}
                          </p>
                        </div>
                        {(jsonContent.total > 0 || jsonContent.score > 0) && (<div className={`grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 lg:gap-4 mb-0 mt-6 pb-4 ${
                          isFullscreen ? 'px-10 py-2' : 'px-2 sm:px-4'
                        }`}>
                          <div className='bg-white p-2 sm:p-3 md:p-4 rounded-xl text-center shadow-lg border border-gray-100 transition-all duration-300 hover:transform hover:-translate-y-1 hover:shadow-xl min-w-0'>
                            <div className={`text-lg sm:text-xl md:text-2xl font-bold mb-1 sm:mb-2 truncate ${getSecurityLevelColor(jsonContent.score)}`}>
                              {getSecurityLevel(jsonContent.score)}
                            </div>
                            <div className='text-sm text-gray-500 truncate'>{t('redteam.securityLevel')}</div>
                          </div>
                          <div className='bg-white p-2 sm:p-3 md:p-4 rounded-xl text-center shadow-lg border border-gray-100 transition-all duration-300 hover:transform hover:-translate-y-1 hover:shadow-xl min-w-0'>
                            <div className={`text-lg sm:text-xl md:text-2xl font-bold mb-1 sm:mb-2 truncate ${getSecurityLevelColor(jsonContent.score)}`}>
                              {jsonContent.score}
                            </div>
                            <div className='text-sm text-gray-500 truncate'>{t('redteam.score')}</div>
                          </div>
                          <div className='bg-white p-2 sm:p-3 md:p-4 rounded-xl text-center shadow-lg border border-gray-100 transition-all duration-300 hover:transform hover:-translate-y-1 hover:shadow-xl min-w-0'>
                            <div className={`text-lg sm:text-xl md:text-2xl font-bold mb-1 sm:mb-2 truncate ${
                              (jsonContent.jailbreak || 0) === 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {Math.round((jsonContent.jailbreak || 0) / jsonContent.total * 100)}%
                            </div>
                            <div className='text-sm text-gray-500 truncate'>{t('redteam.jailbreakSuccessRate')}</div>
                          </div>
                          <div className='bg-white p-2 sm:p-3 md:p-4 rounded-xl text-center shadow-lg border border-gray-100 transition-all duration-300 hover:transform hover:-translate-y-1 hover:shadow-xl min-w-0'>
                            <div className='text-lg sm:text-xl md:text-2xl font-bold text-blue-600 mb-1 sm:mb-2 truncate'>
                              {jsonContent.total}
                            </div>
                            <div className='text-sm text-gray-500 truncate'>{t('redteam.evaluationTotal')}</div>
                          </div>
                        </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Radar chart area */}
                    {jsonContent.extraBody && (jsonContent.extraBody.vulnerabilityResults?.length > 0 || jsonContent.extraBody.attackMethodResults?.length > 0) && (
                      <div className={`${isFullscreen ? 'px-10 py-4' : 'px-4 py-2'}`}>
                        {/* Check whether the radar chart should be shown */}
                        {((jsonContent.extraBody.vulnerabilityResults && 
                           jsonContent.extraBody.vulnerabilityResults.length > 1) ||
                          (jsonContent.extraBody.attackMethodResults && 
                           jsonContent.extraBody.attackMethodResults.length > 1)) && (
                          <div className={`grid gap-6 ${
                            ((jsonContent.extraBody.vulnerabilityResults && 
                              jsonContent.extraBody.vulnerabilityResults.length > 1) &&
                             (jsonContent.extraBody.attackMethodResults && 
                              jsonContent.extraBody.attackMethodResults.length > 1))
                              ? 'grid-cols-1 lg:grid-cols-2'
                              : 'grid-cols-1'
                          }`}>
                            {/* Jailbreak scenario performance radar chart */}
                            {jsonContent.extraBody.vulnerabilityResults && 
                             jsonContent.extraBody.vulnerabilityResults.length > 1 && (
                              <RadarChartComponent
                                data={(() => {
                                  const mappedData = jsonContent.extraBody.vulnerabilityResults.map((item: any) => ({
                                    subject: item.vulnerability || 'Unknown',
                                    score: item.asr || 0,
                                    fullMark: 1,
                                  }));
                                  
                                  // When there are more than 3 dimensions, merge items whose asr is 0 into "Others"
                                  if (mappedData.length > 3) {
                                    const nonZeroData = mappedData.filter(item => item.score > 0);
                                    const zeroData = mappedData.filter(item => item.score === 0);
                                    
                                    if (zeroData.length > 0) {
                                      nonZeroData.push({
                                        subject: t('mcp.other'),
                                        score: 0,
                                        fullMark: 1,
                                      });
                                    }
                                    
                                    return nonZeroData;
                                  }
                                  return mappedData;
                                })()}
                                title={t('redteam.vulnerabilityRadarChart')}
                                height={300}
                              />
                            )}
                            
                            {/* Attack-method jailbreak performance radar chart */}
                            {jsonContent.extraBody.attackMethodResults && 
                             jsonContent.extraBody.attackMethodResults.length > 1 && (
                              <RadarChartComponent
                                data={(() => {
                                  const mappedData = jsonContent.extraBody.attackMethodResults.map((item: any) => {
                                    const mappedItem = {
                                      subject: item.attackMethod || 'Unknown',
                                      score: item.asr || 0,
                                      fullMark: 1,
                                    };
                                    return mappedItem;
                                  });
                                  
                                  // When there are more than 3 dimensions, merge items whose asr is 0 into "Others"
                                  if (mappedData.length > 3) {
                                    const nonZeroData = mappedData.filter(item => item.score > 0);
                                    const zeroData = mappedData.filter(item => item.score === 0);
                                    
                                    if (zeroData.length > 0) {
                                      nonZeroData.push({
                                        subject: t('mcp.other'),
                                        score: 0,
                                        fullMark: 1,
                                      });
                                    }
                                    
                                    return nonZeroData;
                                  }
                                  return mappedData;
                                })()}
                                title={t('redteam.attackMethodRadarChart')}
                                height={300}
                              />
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    <div className={`space-y-4 ${isFullscreen ? 'p-10' : 'p-4'}`}>
                      {jsonContent.results && jsonContent.results.length > 0 ? (
                        jsonContent.results.map((item: ResultItem, idx: number) => (
                      <div key={idx} className='rounded-2xl overflow-hidden shadow-lg border border-gray-100 p-4 relative'>
                        <div className='absolute top-4 right-4'>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${
                              item.status === 'Jailbreak' 
                                ? 'bg-red-100 text-red-800 border-red-200' 
                                : item.status === 'Warning' 
                                  ? 'bg-orange-100 text-orange-800 border-orange-200' 
                                  : 'bg-green-100 text-green-800 border-green-200'
                            }`}
                          >
                            {item.status === 'Jailbreak' ? (
                              <span className='inline-flex items-center'>
                                <AlertTriangle className='w-3 h-3 mr-1' />
                                {t('redteam.jailbreakSuccess')}
                              </span>
                            ) : (
                              <span className='inline-flex items-center'>
                                <AlertTriangle className='w-3 h-3 mr-1' />
                                {t('redteam.jailbreakFailed')}
                              </span>
                            )}
                          </Badge>
                        </div>
                        <div className='mb-4'>
                          <div className='text-sm text-gray-700 mb-1 flex items-center'>
                            <Shield className='w-3 h-3 mr-1' />
                            {t('jailbreak.testScenario')}
                          </div>
                          <div className='flex items-center'>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Badge variant='secondary' className='truncate bg-orange-100 text-orange-800 border-orange-200 hover:bg-orange-200 dark:bg-orange-900 dark:text-orange-200 dark:border-orange-700'>{item.vulnerability}</Badge>
                              </TooltipTrigger>
                              <TooltipContent className='max-w-[80vw] whitespace-pre-line break-words'>
                                <span>{item.vulnerability}</span>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </div>
                        <div className='mb-4'>
                          <div className='text-sm text-gray-700 mb-1 flex items-center'>
                            <BookOpen className='w-3 h-3 mr-1' />
                            {t('jailbreak.jailbreakMethod')}
                          </div>
                          <div className='flex items-center'>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Badge variant='secondary' className='truncate bg-blue-100 text-blue-800 border-blue-200 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200 dark:border-blue-700'>{item.attackMethod}</Badge>
                              </TooltipTrigger>
                              <TooltipContent className='max-w-[80vw] whitespace-pre-line break-words'>
                                <span>{item.attackMethod}</span>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </div>
                        {item.originalInput && (
                          <div className='mb-4'>
                            <div className='text-sm text-gray-700 mb-1 flex items-center'>
                              <FileText className='w-3 h-3 mr-1' />
                              {t('redteam.originalInput')}
                            </div>
                            <div className='flex items-start'>
                              <div className='flex-1'>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className='block overflow-hidden text-ellipsis' style={{
                                      display: '-webkit-box',
                                      WebkitLineClamp: 3,
                                      WebkitBoxOrient: 'vertical',
                                      lineHeight: '1.4em',
                                      maxHeight: '4.2em'
                                    }}>{item.originalInput}</span>
                                  </TooltipTrigger>
                                  <TooltipContent className='max-w-[80vw] whitespace-pre-line break-words'>
                                    <span>{item.originalInput}</span>
                                  </TooltipContent>
                                </Tooltip>
                              </div>
                              <button
                                className='ml-2 p-1 rounded hover:bg-gray-100 inline-flex items-center flex-shrink-0'
                                onClick={() => handleCopy(item.originalInput!, `originalInput-${idx}`)}
                                title={t('redteam.copy')}
                                type='button'
                              >
                                <Copy className='w-3 h-3 text-gray-400' />
                              </button>
                              {copied === `originalInput-${idx}` && (
                                <span className='ml-1 text-green-500 text-xs flex-shrink-0'>{t('redteam.copied')}</span>
                              )}
                            </div>
                          </div>
                        )}
                        <div className='mb-4'>
                          <div className='text-sm text-gray-700 mb-1 flex items-center'>
                            <FileText className='w-3 h-3 mr-1' />
                            {t('redteam.attackInput')}
                          </div>
                          <div className='flex items-start'>
                            <div className='flex-1'>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className='block overflow-hidden text-ellipsis' style={{
                                    display: '-webkit-box',
                                    WebkitLineClamp: 3,
                                    WebkitBoxOrient: 'vertical',
                                    lineHeight: '1.4em',
                                    maxHeight: '4.2em'
                                  }}>{item.input || '-'}</span>
                                </TooltipTrigger>
                                <TooltipContent className='max-w-[80vw] whitespace-pre-line break-words'>
                                  <span>{item.input || '-'}</span>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            {item.input && (
                              <button
                                className='ml-2 p-1 rounded hover:bg-gray-100 inline-flex items-center flex-shrink-0'
                                onClick={() => handleCopy(item.input!, `input-${idx}`)}
                                title={t('redteam.copy')}
                                type='button'
                              >
                                <Copy className='w-3 h-3 text-gray-400' />
                              </button>
                            )}
                            {copied === `input-${idx}` && (
                              <span className='ml-1 text-green-500 text-xs flex-shrink-0'>{t('redteam.copied')}</span>
                            )}
                          </div>
                        </div>
                        <div className='mb-4'>
                          <div className='text-sm text-gray-700 mb-1 flex items-center'>
                            <MessageSquare className='w-3 h-3 mr-1' />
                            {t('redteam.modelOutput')}
                          </div>
                          <div className='flex items-start'>
                            <div className='flex-1'>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className='block overflow-hidden text-ellipsis' style={{
                                    display: '-webkit-box',
                                    WebkitLineClamp: 3,
                                    WebkitBoxOrient: 'vertical',
                                    lineHeight: '1.4em',
                                    maxHeight: '4.2em'
                                  }}>{item.output || '-'}</span>
                                </TooltipTrigger>
                                <TooltipContent className='max-w-[80vw] whitespace-pre-line break-words'>
                                  <span>{item.output || '-'}</span>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            {item.output && (
                              <button
                                className='ml-2 p-1 rounded hover:bg-gray-100 inline-flex items-center flex-shrink-0'
                                onClick={() => handleCopy(item.output!, `output-${idx}`)}
                                title={t('redteam.copy')}
                                type='button'
                              >
                                <Copy className='w-3 h-3 text-gray-400' />
                              </button>
                            )}
                            {copied === `output-${idx}` && (
                              <span className='ml-1 text-green-500 text-xs flex-shrink-0'>{t('redteam.copied')}</span>
                            )}
                          </div>
                        </div>
                        <div className='mb-4'>
                          <div className='text-sm text-gray-700 mb-1 flex items-center'>
                            <Info className='w-3 h-3 mr-1' />
                            {t('redteam.evaluationBasis')}
                          </div>
                          <div className={`whitespace-pre-wrap break-words text-sm text-gray-700 mt-2 p-2 rounded-md border ${
                            item.status === 'Jailbreak'
                              ? 'bg-red-50 border-red-200'
                              : 'bg-green-50 border-green-200'
                          }`}>
                            {item.reason || '-'}
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className='text-sm text-center text-gray-400 -mt-8 pb-2 flex items-center justify-center gap-1'>
                      <Info className='w-3 h-3' />
                      {t('redteam.noValidModelsMessage')}
                    </div>
                  )}
                </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Back-to-top button */}
        {showScrollTop && (
          <button
            onClick={scrollToTop}
            className="fixed bottom-6 right-6 z-[9999] w-10 h-10 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-xl transition-all duration-300 hover:scale-110 flex items-center justify-center border-2 border-white"
            title={t('redteam.backToTop')}
            style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  // Default text display
  return (
    <div className="p-4" data-testid="result-display">
      <Card className="border-none shadow-none">
        <CardContent className="p-0">
          <div className="prose prose-sm max-w-none [&_table_td]:align-top">
            <div className='whitespace-pre-wrap text-sm text-gray-700'>
              {typeof content === 'string' ? content : ''}
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Back-to-top button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-6 right-6 z-[9999] w-10 h-10 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-xl transition-all duration-300 hover:scale-110 flex items-center justify-center border-2 border-white"
          title={t('redteam.backToTop')}
          style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};

export default ResultDisplay; 