import React, { useRef, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ExecutionStep, AgentScanResult, AgentScanVulnerability } from '../../types';
import { useApp } from '../../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import CodeHighlight from './CodeHighlight';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Info,
  CheckCircle,
  Activity,
  FileText,
  ChevronDown,
  ChevronUp,
  Download,
  Share2,
  Maximize,
  Minimize,
  Bot,
  User,
  Clock,
  Calendar,
  Target
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';
import { useReportPrint } from './useReportPrint';
import BaseDetailPanel from './BaseDetailPanel';

interface AgentScanDetailPanelProps {
  step?: ExecutionStep | null;
  agentScanResult?: AgentScanResult;
  selectedTool?: {
    step: ExecutionStep;
    subStepIndex: number;
    toolIndex: number;
  } | null;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  sessionId?: string;
}

const CollapsibleContent = ({ text, label, icon: Icon, bgClass = "bg-gray-50" }: any) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { t } = useTranslation();
  const isLong = text.length > 200 || text.split('\n').length > 3;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
        <Icon className="w-4 h-4 text-gray-500" />
        {label}
      </div>
      <div className={`${bgClass} rounded-lg p-3 text-sm font-mono text-gray-800`}>
         <div className={`${!isExpanded && isLong ? 'line-clamp-3 overflow-hidden' : ''} whitespace-pre-wrap break-all`}>
            {text}
         </div>
         {isLong && (
           <button
             onClick={() => setIsExpanded(!isExpanded)}
             className="mt-2 text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 select-none font-sans"
           >
             {isExpanded ? (
               <><ChevronUp className="w-3 h-3" /> {t('common.collapse')}</>
             ) : (
               <><ChevronDown className="w-3 h-3" /> {t('common.expand')}</>
             )}
           </button>
         )}
      </div>
    </div>
  );
};

const AgentScanDetailPanel: React.FC<AgentScanDetailPanelProps> = ({
  step,
  agentScanResult: propResult,
  selectedTool,
  isFullscreen = false,
  onToggleFullscreen,
  sessionId
}) => {
  const { t } = useTranslation();
  const { state } = useApp();
  const panelRef = useRef<HTMLDivElement>(null);
  const [reportTab, setReportTab] = useState('vulnerabilities');
  
  // When switching tasks, reset the Tab to 'report'
  useEffect(() => {
    setReportTab('vulnerabilities');
  }, [sessionId]);

  const currentTask = state.tasks.find(
    task => task.id === (sessionId || state.currentTaskId)
  );

  const messageResult = currentTask?.messages?.find(m => m.type === 'result' && m.agentScanResult)?.agentScanResult;

  const result = propResult || step?.agentScanResult || messageResult;

  const handleDownloadPdf = useReportPrint(
    panelRef,
    result ? `Agent Scan Report - ${result.agent_name || 'Agent'}` : 'Agent Scan Report'
  );

  // If viewing a specific step (from action log), show only the execution details using BaseDetailPanel
  if (step) {
    return (
      <BaseDetailPanel
        step={step}
        selectedTool={selectedTool}
        isFullscreen={isFullscreen}
        onToggleFullscreen={onToggleFullscreen}
      />
    );
  }

  // If no result is available (and not a step view), show empty state via BaseDetailPanel
  if (!result) {
    return (
      <BaseDetailPanel
        step={null}
        selectedTool={selectedTool}
        isFullscreen={isFullscreen}
        onToggleFullscreen={onToggleFullscreen}
      />
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRiskText = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'high': return t('agentScan.high');
      case 'medium': return t('agentScan.medium');
      case 'low': return t('agentScan.low');
      default: return risk.toUpperCase();
    }
  };

  const getRiskTextColorForDarkBg = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'high': return 'text-[#FF8A80]';
      case 'medium': return 'text-yellow-300';
      case 'low': return 'text-green-300';
      default: return 'text-white';
    }
  };

  const getSeverityStyles = (level: string) => {
    switch (level.toLowerCase()) {
      case 'high':
        return {
          row: 'bg-red-50 border-red-100',
          badge: 'bg-red-600 text-white border-transparent hover:bg-red-700 rounded-full px-3'
        };
      case 'medium':
        return {
          row: 'bg-orange-50 border-orange-100',
          badge: 'bg-orange-500 text-white border-transparent hover:bg-orange-600 rounded-full px-3'
        };
      case 'low':
        return {
          row: 'bg-green-50 border-green-100',
          badge: 'bg-green-600 text-white border-transparent hover:bg-green-700 rounded-full px-3'
        };
      default:
        return {
          row: 'bg-gray-50 border-gray-100',
          badge: 'bg-gray-600 text-white border-transparent hover:bg-gray-700 rounded-full px-3'
        };
    }
  };

  // Prepare data for charts
  const severityData = [
    { name: t('agentScan.high'), value: result.results.filter(r => r.level.toLowerCase() === 'high').length, color: '#f87171' },
    { name: t('agentScan.medium'), value: result.results.filter(r => r.level.toLowerCase() === 'medium').length, color: '#fb923c' },
    { name: t('agentScan.low'), value: result.results.filter(r => r.level.toLowerCase() === 'low').length, color: '#4ade80' },
  ].filter(d => d.value > 0);

  const owaspData = result.owasp_agentic_2026_top10.map(item => ({
    subject: item.id,
    A: item.total, // Using 'total' as the value for radar chart
    fullMark: Math.max(...result.owasp_agentic_2026_top10.map(i => i.total)) || 5,
    name: item.name
  }));

  const owaspLegendData = result.owasp_agentic_2026_top10
    .filter(item => item.total > 0)
    .map(item => ({
      value: item.id,
      type: 'circle' as const,
      color: '#7B72F0',
      payload: { value: item.total, strokeDasharray: '' }
    }));

  const formatDuration = (start?: number, end?: number) => {
    if (!start || !end) return '-';
    // Handle seconds vs milliseconds. If start is < 1e12, assume seconds
    const isSeconds = start < 100000000000;
    let diff = end - start;
    if (isSeconds) diff *= 1000;
    
    if (diff < 0) return '-';

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const formatTime = (timestamp?: number) => {
    if (!timestamp) return '-';
    const isSeconds = timestamp < 100000000000;
    return new Date(isSeconds ? timestamp * 1000 : timestamp).toLocaleString();
  };

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return '-';
    const isSeconds = timestamp < 100000000000;
    return new Date(isSeconds ? timestamp * 1000 : timestamp).toLocaleDateString();
  };

  return (
    <div className={`flex flex-col h-full bg-gray-50/50 ${isFullscreen ? 'fixed inset-0 z-50 bg-gray-50' : ''}`}>
      <div className="flex-1 min-h-0 relative overflow-hidden flex flex-col">
          <>
            {/* Top Toolbar - Fixed */}
            <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 shrink-0 z-10">
               <div className="flex items-center gap-2 font-medium text-gray-800">
                  <ShieldCheck className="w-5 h-5 text-blue-600" />
                  <span>A.I.G {t('agentScan.title')}</span>
               </div>
               <div className="flex items-center gap-2">
                 <TooltipProvider>
                   <Tooltip>
                     <TooltipTrigger asChild>
                       <Button variant="ghost" size="icon" onClick={handleDownloadPdf}>
                         <Download className="w-4 h-4" />
                       </Button>
                     </TooltipTrigger>
                     <TooltipContent>
                       <p>{t('common.fullscreen') === "Fullscreen" ? "Export PDF" : "导出PDF"}</p>
                     </TooltipContent>
                   </Tooltip>

                   <Tooltip>
                     <TooltipTrigger asChild>
                       <Button variant="ghost" size="icon" onClick={() => {
                          const targetId = sessionId || state.currentTaskId;
                          const shareUrl = `${window.location.origin}/report/${targetId}`;
                          window.open(shareUrl, '_blank');
                       }}>
                         <Share2 className="w-4 h-4" />
                       </Button>
                     </TooltipTrigger>
                     <TooltipContent>
                       <p>{t('common.share')}</p>
                     </TooltipContent>
                   </Tooltip>
                 </TooltipProvider>

                 {onToggleFullscreen && (
                   <Button variant="ghost" size="icon" onClick={onToggleFullscreen}>
                     {isFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
                   </Button>
                 )}
               </div>
            </div>

            {/* Scrollable Report Area */}
            <div className="flex-1 overflow-y-auto relative">
               <div ref={panelRef} className="min-h-full pb-10">
                  
                  {/* Container for Report Header and Body */}
                  <div className={`mx-auto flex flex-col ${isFullscreen ? 'max-w-5xl pt-8' : 'w-full mt-4'}`}>
                  {/* Blue Header Card - Centered Content */}
                  <div className="bg-[#7B72F0] text-white p-8 pb-24 shadow-sm relative overflow-hidden rounded-t-2xl">
                      <div className="flex flex-col items-center text-center relative z-10">
                          <div className="flex items-center justify-center gap-2 mb-4 mt-6">
                             <img src="/images/logo-white.png" alt="A.I.G" className="w-8 h-8 mr-2 flex-shrink-0" />
                             <h1 className="text-3xl font-bold flex items-center">
                                <span className="mr-4 relative" style={{ fontFamily: 'tencentSans', letterSpacing: '0.1em', top: '-2px', fontSize: '30px' }}>A.I.G</span>
                                {t('agentScan.title')}
                             </h1>
                          </div>

                          {/* Meta Info Centered */}
                          <div className="flex flex-wrap justify-center gap-x-12 gap-y-4 text-xs text-[#E0DEFC] mt-6 mb-2">
                                 <div className="flex items-center gap-2">
                                    <Target className="w-4 h-4 opacity-70" />
                                    <span className="opacity-70">{t('infraScan.scan.targets') || '检测目标'}:</span>
                                    <span className="font-medium text-white text-sm">{result.agent_name || 'Unknown Agent'}</span>
                                 </div>
                                 <div className="flex items-center gap-2">
                                    <Calendar className="w-4 h-4 opacity-70" />
                                    <span className="opacity-70">{t('mcp.scanTime') || '扫描时间'}:</span>
                                    <span className="font-medium text-white text-sm">{formatDate(result.start_time)}</span>
                                 </div>
                                 <div className="flex items-center gap-2">
                                    <Clock className="w-4 h-4 opacity-70" />
                                    <span className="opacity-70">{t('mcp.scanDuration') || '检测时长'}:</span>
                                    <span className="font-medium text-white text-sm">{formatDuration(result.start_time, result.end_time)}</span>
                                 </div>
                              </div>

                          {/* Score Stats - Centered Grid */}
                           <div className="w-full max-w-4xl grid grid-cols-2 md:grid-cols-3 gap-8 py-6 bg-white/10 rounded-2xl border border-white/10 mt-8">
                                <div className="flex flex-col items-center">
                                    <div className={`text-3xl font-bold mb-1 ${getRiskTextColorForDarkBg(result.risk_type)}`}>
                                       {getRiskText(result.risk_type)}
                                    </div>
                                    <div className="text-[#E0DEFC] text-xs uppercase tracking-wider font-semibold">{t('agentScan.riskLevel')}</div>
                                </div>
                                <div className="flex flex-col items-center">
                                   <div className={`text-4xl font-bold mb-1 ${getRiskTextColorForDarkBg(result.risk_type)}`}>{result.score}</div>
                                   <div className="text-[#E0DEFC] text-xs uppercase tracking-wider font-semibold">{t('agentScan.securityScore')}</div>
                                </div>
                                 <div className="flex flex-col items-center">
                                   <div className="text-3xl font-bold text-[#FF8A80] mb-1">{result.vulnerable_tests}</div>
                                   <div className="text-[#E0DEFC] text-xs uppercase tracking-wider font-semibold">{t('agentScan.vulnerabilities')}</div>
                                </div>
                           </div>
                          </div>
                      </div>
                  
                      {/* White Body Wrapper */}
                      <div className={`bg-white shadow-sm pb-8 min-h-[500px] ${isFullscreen ? 'rounded-b-3xl' : ''}`}>
                      
                      {/* Charts Section - Floating */}
                      {result.results.length > 0 && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 -mt-16 relative z-10 mb-6 px-6">
                            <Card className="shadow-xl border-0 rounded-xl overflow-hidden bg-white ring-1 ring-black/5">
                              <CardHeader>
                                <CardTitle className="text-base font-medium flex items-center gap-2">
                                   <Activity className="w-4 h-4 text-blue-600" /> {t('agentScan.vulnerabilityDistribution')}
                                </CardTitle>
                              </CardHeader>
                              <CardContent className="min-h-[200px] flex flex-col items-center justify-center pt-6 pb-10 gap-6">
                                {severityData.length > 0 ? (
                                  <>
                                    <div className="w-full h-[140px]">
                                      <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                          <Pie
                                            data={severityData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius="60%"
                                            outerRadius="85%"
                                            paddingAngle={2}
                                            dataKey="value"
                                            cornerRadius={4}
                                            stroke="none"
                                          >
                                            {severityData.map((entry, index) => (
                                              <Cell key={`cell-${index}`} fill={entry.color} />
                                            ))}
                                          </Pie>
                                          <RechartsTooltip 
                                            cursor={false}
                                            contentStyle={{ 
                                              borderRadius: '8px', 
                                              border: 'none', 
                                              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' 
                                            }}
                                            itemStyle={{ color: '#1f2937', fontSize: '12px', fontWeight: 500 }}
                                          />
                                        </PieChart>
                                      </ResponsiveContainer>
                                    </div>
                                    <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 px-2">
                                      {severityData.map((item) => (
                                        <div key={item.name} className="flex items-center gap-1.5">
                                          <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                                          <span className="text-gray-600 text-xs font-medium whitespace-nowrap">
                                            {item.name} <span className="text-gray-400">({item.value})</span>
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  </>
                                ) : (
                                  <div className="text-gray-400">{t('agentScan.noVulnerabilities')}</div>
                                )}
                              </CardContent>
                            </Card>
                            
                            <Card className="shadow-xl border-0 rounded-xl overflow-hidden bg-white ring-1 ring-black/5">
                              <CardHeader>
                                <CardTitle className="text-base font-medium flex items-center gap-2 truncate pr-4">
                                   <ShieldAlert className="w-4 h-4 text-purple-600 shrink-0" />
                                   <span className="truncate">{t('agentScan.owaspTop10')}</span>
                                </CardTitle>
                              </CardHeader>
                              <CardContent className="min-h-[200px] flex flex-col items-center justify-center pt-6 pb-10 gap-6">
                                <div className="w-full h-[140px]">
                                  <ResponsiveContainer width="100%" height="100%">
                                    <RadarChart cx="50%" cy={owaspData.length === 3 ? "60%" : "50%"} outerRadius="80%" data={owaspData}>
                                      <PolarGrid gridType="polygon" stroke="#e5e7eb" />
                                      <PolarAngleAxis 
                                        dataKey="subject" 
                                        tick={{ fontSize: 11, fill: '#6b7280', fontWeight: 500 }} 
                                      />
                                      <PolarRadiusAxis angle={30} domain={[0, 'auto']} tick={false} axisLine={false} />
                                      <Radar
                                        name={t('agentScan.findings')}
                                        dataKey="A"
                                        stroke="#7B72F0"
                                        strokeWidth={2}
                                        fill="#7B72F0"
                                        fillOpacity={0.2}
                                        isAnimationActive={true}
                                        dot={{ r: 3, fill: "#7B72F0", strokeWidth: 0 }}
                                      />
                                      <RechartsTooltip 
                                        contentStyle={{ 
                                          borderRadius: '8px', 
                                          border: 'none', 
                                          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' 
                                        }}
                                        itemStyle={{ color: '#1f2937', fontSize: '12px', fontWeight: 500 }}
                                      />
                                    </RadarChart>
                                  </ResponsiveContainer>
                                </div>
                                <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 px-2">
                                  {owaspLegendData.map((item) => (
                                    <div key={item.value} className="flex items-center gap-1.5">
                                      <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                                      <span className="text-gray-600 text-xs font-medium whitespace-nowrap">
                                        {item.value} <span className="text-gray-400">({item.payload.value})</span>
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                      )}

                      {/* Report Body - White Background */}
                      <div className="px-6">
                        <div>
                          {/* Report Content Tabs */}
                          <Tabs value={reportTab} onValueChange={setReportTab} className="w-full">
                          <div className="flex-shrink-0 w-full mb-4">
                             <TabsList className="flex w-full justify-start border-b rounded-none bg-transparent p-0 h-auto gap-6">
                                <TabsTrigger 
                                  value="vulnerabilities" 
                                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-[#7B72F0] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 data-[state=active]:text-[#7B72F0] flex items-center gap-2"
                                >
                                   <AlertTriangle className="w-4 h-4" />
                                   {t('agentScan.vulnerabilityDetails')}
                                </TabsTrigger>
                                <TabsTrigger 
                                  value="information" 
                                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-[#7B72F0] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 data-[state=active]:text-[#7B72F0] flex items-center gap-2"
                                >
                                   <FileText className="w-4 h-4" />
                                   {t('agentScan.informationGathering')}
                                </TabsTrigger>
                             </TabsList>
                          </div>
    
                          <TabsContent value="vulnerabilities" className="space-y-6 mt-0 focus-visible:ring-0 focus-visible:outline-none">
                             {/* Vulnerability Details List */}
                             <div className="space-y-4">
                                {result.results.length > 0 ? result.results.map((vuln) => {
                                   const styles = getSeverityStyles(vuln.level);
                                   return (
                                   <Card key={vuln.id} className="mb-4 w-full rounded-2xl overflow-hidden shadow-xl border-0 ring-1 ring-black/5">
                                      <div className={`px-4 py-5 border-b flex items-center justify-between gap-4 ${styles.row}`}>
                                         <div className="flex items-center gap-3 overflow-hidden flex-1">
                                            <Badge className={`shrink-0 ${styles.badge}`}>
                                               {getRiskText(vuln.level)}
                                            </Badge>
                                            <div className="font-medium text-sm text-gray-900 truncate" title={vuln.title}>
                                               {vuln.title}
                                            </div>
                                         </div>
                                         <div className="flex gap-2 shrink-0">
                                            {vuln.owasp.map(o => (
                                               <Badge key={o} variant="secondary" className="bg-white/60 text-gray-700 border-0">
                                                  OWASP {o}
                                               </Badge>
                                            ))}
                                         </div>
                                      </div>
                                      <CardContent className="p-8 pt-8 space-y-4">
                                         <div>
                                            <div className="flex items-center gap-2 font-semibold text-gray-900 mb-2 text-sm">
                                               <FileText className="w-4 h-4 text-blue-600" />
                                               {t('agentScan.vulnerabilityDescription')}
                                            </div>
                                            <div className="prose prose-sm max-w-none text-gray-600 text-sm">
                                               <CodeHighlight>
                                                 {vuln.description}
                                               </CodeHighlight>
                                            </div>
                                         </div>
                                         
                                         {/* Conversation Trace */}
                                         {vuln.conversation && vuln.conversation.length > 0 && (
                                           <div className="mt-4 space-y-6">
                                              {vuln.conversation.map((conv, idx) => (
                                                 <div key={idx} className="space-y-4">
                                                    {conv.prompt && (
                                                       <CollapsibleContent 
                                                          text={conv.prompt} 
                                                          label={t('agentScan.modelInput')} 
                                                          icon={User}
                                                       />
                                                    )}
                                                    {conv.response && (
                                                       <CollapsibleContent 
                                                          text={conv.response} 
                                                          label={t('agentScan.modelOutput')} 
                                                          icon={Bot}
                                                       />
                                                    )}
                                                 </div>
                                              ))}
                                           </div>
                                         )}
    
                                         {/* Suggestion */}
                                         <div className="bg-blue-50 border border-blue-100 p-3 rounded-md">
                                            <div className="flex items-center gap-2 text-blue-700 font-semibold mb-1 text-sm">
                                               <Info className="w-4 h-4" /> {t('agentScan.remediationSuggestion')}
                                            </div>
                                            <div className="text-sm text-blue-800">
                                                <CodeHighlight>{vuln.suggestion}</CodeHighlight>
                                            </div>
                                         </div>
                                      </CardContent>
                                   </Card>
                                )}) : (
                                   <div className="flex flex-col items-center justify-center p-8 bg-white rounded-lg border border-dashed">
                                      <ShieldCheck className="w-12 h-12 text-green-500 mb-4" />
                                      <h3 className="text-lg font-medium text-gray-900">{t('agentScan.noVulnerabilities')}</h3>
                                      <p className="text-gray-500 text-sm mt-1">
                                         {t('agentScan.noRisksDescription') || "Great! No security risks found."}
                                      </p>
                                   </div>
                                )}
                             </div>
                          </TabsContent>
    
                          <TabsContent value="information" className="mt-0 focus-visible:ring-0 focus-visible:outline-none">
                              {/* Report Description / Methodology */}
                              <Card className="bg-gray-50 border-gray-200">
                                <CardContent className="p-6">
                                   <div className="prose prose-sm max-w-none text-gray-500">
                                      <CodeHighlight>
                                        {result.report_description}
                                      </CodeHighlight>
                                   </div>
                                </CardContent>
                              </Card>
                          </TabsContent>
                        </Tabs>
                      </div>
                      </div>
                      </div>
                  </div>
               </div>
            </div>
          </>
      </div>
    </div>
  );
};

export default AgentScanDetailPanel;
