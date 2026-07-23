import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { AppProvider, useApp } from '../context/AppContext';
import { AuthGate } from '../config/privateModules';
import TaskSidebar from './TaskSidebar';
import ChatArea from './ChatArea';
import McpStepDetail from './detailPanel/McpStepDetail';
import InfraScanDetailPanel from './detailPanel/InfraScanDetailPanel';
import RedteamReportDetailPanel from './detailPanel/RedteamReportDetailPanel';
import JailbreakDetailPanel from './detailPanel/JailbreakDetailPanel';
import AgentScanDetailPanel from './detailPanel/AgentScanDetailPanel';
import HelpDocumentPage from '../pages/HelpDocumentPage';
import ReportPage from '../pages/ReportPage';
import { ExecutionStep, MCPScanResult, InfraScanResult, RedteamReportResult, JailbreakResult, AgentScanResult } from '../types';
import { Toaster } from './ui/sonner';
import WelcomeAnimation from './WelcomeAnimation';
import { env } from '../config/env';
import { isDocSiteMode, extraRoutes } from '../config/privateModules';
import { useVersionCheck } from '../hooks/useVersionCheck';

const AppContent: React.FC = () => {
  const { state } = useApp();
  const location = useLocation();

  // Check for a new platform version on page open and once per day; notify the user when available
  useVersionCheck();
  const [selectedStep, setSelectedStep] = useState<ExecutionStep | null>(null);
  const [selectedTool, setSelectedTool] = useState<{
    step: ExecutionStep;
    subStepIndex: number;
    toolIndex: number;
  } | null>(null);
  const [mcpResult, setMcpResult] = useState<MCPScanResult | undefined>(undefined);
  const [infraScanResult, setInfraScanResult] = useState<InfraScanResult | undefined>(undefined);
  const [redteamReportResult, setRedteamReportResult] = useState<RedteamReportResult | undefined>(undefined);
  const [jailbreakResult, setJailbreakResult] = useState<JailbreakResult | undefined>(undefined);
  const [agentScanResult, setAgentScanResult] = useState<AgentScanResult | undefined>(undefined);
  const [chatAreaWidth, setChatAreaWidth] = useState<number>(60); // Percentage width
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showWelcome, setShowWelcome] = useState<boolean>(env.VITE_ENABLE_WELCOME_ANIMATION);
  const [welcomeAnimationCompleted, setWelcomeAnimationCompleted] = useState<boolean>(!env.VITE_ENABLE_WELCOME_ANIMATION);


  const handleStepSelect = (step: ExecutionStep | null) => {
    setSelectedStep(step);
    setSelectedTool(null); // Clear the selected tool
    setMcpResult(undefined); // Clear mcpResult
    setInfraScanResult(undefined); // Clear infraScanResult
    setRedteamReportResult(undefined); // Clear redteamReportResult
    setJailbreakResult(undefined); // Clear jailbreakResult
    setAgentScanResult(undefined); // Clear agentScanResult
  };

  const handleToolSelect = (step: ExecutionStep, subStepIndex: number, toolIndex: number) => {
    setSelectedTool({ step, subStepIndex, toolIndex });
    setSelectedStep(step); // Also select the corresponding step
    setMcpResult(undefined); // Clear mcpResult
    setInfraScanResult(undefined); // Clear infraScanResult
    setRedteamReportResult(undefined); // Clear redteamReportResult
    setJailbreakResult(undefined); // Clear jailbreakResult
    setAgentScanResult(undefined); // Clear agentScanResult
  };

  const handleMcpResultSelect = (result: MCPScanResult | InfraScanResult | RedteamReportResult | JailbreakResult | AgentScanResult) => {
    // Determine the result type based on the current task type
    const currentTask = state.tasks.find(task => task.id === state.currentTaskId);
    
    if (currentTask?.type === 'AI-Infra-Scan') {
      setInfraScanResult(result as InfraScanResult);
      setMcpResult(undefined);
      setRedteamReportResult(undefined);
      setJailbreakResult(undefined);
      setAgentScanResult(undefined);
    } else if (currentTask?.type === 'Model-Redteam-Report') {
      setRedteamReportResult(result as RedteamReportResult);
      setMcpResult(undefined);
      setInfraScanResult(undefined);
      setJailbreakResult(undefined);
      setAgentScanResult(undefined);
    } else if (currentTask?.type === 'Model-Jailbreak') {
      setJailbreakResult(result as JailbreakResult);
      setMcpResult(undefined);
      setInfraScanResult(undefined);
      setRedteamReportResult(undefined);
      setAgentScanResult(undefined);
    } else if (currentTask?.type === 'Agent-Scan') {
      setAgentScanResult(result as AgentScanResult);
      setMcpResult(undefined);
      setInfraScanResult(undefined);
      setRedteamReportResult(undefined);
      setJailbreakResult(undefined);
    } else {
      // Other task types default to MCP scan result
      setMcpResult(result as MCPScanResult);
      setInfraScanResult(undefined);
      setRedteamReportResult(undefined);
      setJailbreakResult(undefined);
      setAgentScanResult(undefined);
    }
    setSelectedStep(null); // Clear the selected step
  };

  const toggleFullscreen = () => {
    console.log('toggleFullscreen被调用，当前状态:', isFullscreen);
    const newState = !isFullscreen;
    setIsFullscreen(newState);
    console.log('toggleFullscreen设置新状态:', newState);
  };

  const handleWelcomeComplete = () => {
    setShowWelcome(false);
    setWelcomeAnimationCompleted(true);
  };

  // Watch route changes; show the welcome animation only on the home page
  useEffect(() => {
    if (location.pathname === '/') {
      setShowWelcome(env.VITE_ENABLE_WELCOME_ANIMATION);
      if (!env.VITE_ENABLE_WELCOME_ANIMATION) {
        setWelcomeAnimationCompleted(true);
      }
    } else {
      setShowWelcome(false);
    }
  }, [location.pathname]);

  const currentTask = state.tasks.find(task => task.id === state.currentTaskId);
  const selectedStepIndex = selectedStep && currentTask 
    ? currentTask.plan.findIndex(step => step.id === selectedStep.id)
    : undefined;

      // When currentTask changes, clear the McpStepDetail data
  useEffect(() => {
    setSelectedStep(null);
    setMcpResult(undefined);
    setInfraScanResult(undefined);
    setRedteamReportResult(undefined);
    setJailbreakResult(undefined);
    setAgentScanResult(undefined);
    // Do not reset the fullscreen state so the user can keep it
  }, [state.currentTaskId]);

  // Sync selectedStep when the underlying step data updates
  useEffect(() => {
    if (selectedStep && currentTask) {
      const updatedStep = currentTask.plan.find(step => step.id === selectedStep.id);
      if (updatedStep && updatedStep !== selectedStep) {
        setSelectedStep(updatedStep);
      }
    }
    
    // Sync selectedTool when the underlying step data updates
    if (selectedTool && currentTask) {
      const updatedStep = currentTask.plan.find(step => step.id === selectedTool.step.id);
      if (updatedStep && updatedStep !== selectedTool.step) {
        setSelectedTool({
          ...selectedTool,
          step: updatedStep,
        });
      }
    }
  }, [currentTask, selectedStep, selectedTool]);

  // When the task status is completed or done, automatically show the risk report
  useEffect(() => {
    if (currentTask && (currentTask.status === 'completed' || currentTask.status === 'done')) {
      // Prefer looking up the exact match by task type
      if (currentTask.type === 'Agent-Scan') {
        const agentResultMsg = currentTask.messages.find(msg => msg.type === 'result' && msg.agentScanResult);
        if (agentResultMsg?.agentScanResult) {
          setAgentScanResult(agentResultMsg.agentScanResult);
          setSelectedStep(null);
          return;
        }
      }

      // Generic logic: look up various result types in the result message
      const resultMessage = currentTask.messages.find(msg => msg.type === 'result');
      if (resultMessage) {
        if (resultMessage.mcpResult) {
          setMcpResult(resultMessage.mcpResult);
          setSelectedStep(null);
        } else if (resultMessage.infraScanResult) {
          setInfraScanResult(resultMessage.infraScanResult);
          setSelectedStep(null);
        } else if (resultMessage.redteamReportResult) {
          setRedteamReportResult(resultMessage.redteamReportResult);
          setSelectedStep(null);
        } else if (resultMessage.jailbreakResult) {
          setJailbreakResult(resultMessage.jailbreakResult);
          setSelectedStep(null);
        } else if (resultMessage.agentScanResult) {
          setAgentScanResult(resultMessage.agentScanResult);
          setSelectedStep(null);
        }
      }
    }
  }, [currentTask]);

  // When currentTaskId is null, set chatAreaWidth to 100
  useEffect(() => {
    if (state.currentTaskId === null) {
      setChatAreaWidth(100);
    } else {
      setChatAreaWidth(50);
    }
  }, [state.currentTaskId]);

  // Handle drag start
  const handleDragStart = () => {
    if (isFullscreen) return; // Disable dragging when in fullscreen
    setIsDragging(true);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  // Handle drag end
  const handleDragEnd = () => {
    setIsDragging(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  };

  // Handle drag move
  const handleDragMove = (e: MouseEvent) => {
    if (!isDragging || isFullscreen) return;
    
    const container = document.getElementById('main-content');
    if (!container) return;
    
    const containerRect = container.getBoundingClientRect();
    const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
    
    // Clamp the width between 20% and 80%
    const clampedWidth = Math.max(20, Math.min(80, newWidth));
    setChatAreaWidth(clampedWidth);
  };

  // Add and remove global mouse event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleDragMove);
      document.addEventListener('mouseup', handleDragEnd);
      
      return () => {
        document.removeEventListener('mousemove', handleDragMove);
        document.removeEventListener('mouseup', handleDragEnd);
      };
    }
  }, [isDragging, isFullscreen]);

  // Choose the DetailPanel component based on the task type
  const renderDetailPanel = () => {
    if (!currentTask) return null;

    // Choose a different DetailPanel component based on the task type
    switch (currentTask.type) {
      case 'AI-Infra-Scan':
        return (
          <InfraScanDetailPanel 
            step={selectedStep}
            stepIndex={selectedStepIndex}
            infraScanResult={infraScanResult}
            selectedTool={selectedTool}
            isFullscreen={isFullscreen}
            onToggleFullscreen={toggleFullscreen}
          />
        );
      case 'Model-Redteam-Report':
        return (
          <RedteamReportDetailPanel 
            step={selectedStep}
            stepIndex={selectedStepIndex}
            redteamReportResult={redteamReportResult}
            selectedTool={selectedTool}
            isFullscreen={isFullscreen}
            onToggleFullscreen={toggleFullscreen}
          />
        );
      case 'Model-Jailbreak':
        return (
          <JailbreakDetailPanel 
            step={selectedStep}
            stepIndex={selectedStepIndex}
            jailbreakResult={jailbreakResult}
            selectedTool={selectedTool}
            isFullscreen={isFullscreen}
            onToggleFullscreen={toggleFullscreen}
          />
        );
      case 'Agent-Scan':
        return (
          <AgentScanDetailPanel 
            step={selectedStep}
            agentScanResult={agentScanResult}
            selectedTool={selectedTool}
            isFullscreen={isFullscreen}
            onToggleFullscreen={toggleFullscreen}
          />
        );
      default:
        // Other task types use McpStepDetail (shared by Mcp-Scan / Skill-Scan)
        return (
          <McpStepDetail 
            step={selectedStep}
            stepIndex={selectedStepIndex}
            mcpResult={mcpResult}
            selectedTool={selectedTool}
            isFullscreen={isFullscreen}
            onToggleFullscreen={toggleFullscreen}
            taskType={currentTask.type}
          />
        );
    }
  };

  return (
    <>
      {showWelcome && <WelcomeAnimation onComplete={handleWelcomeComplete} />}
      <Routes>
        <Route path="/help" element={<HelpDocumentPage />} />
        {extraRoutes.map(r => (
          <Route key={r.path} path={r.path} element={r.element} />
        ))}
        <Route path="/" element={
          <div className="h-screen bg-gray-100 text-gray-900 flex overflow-hidden">
          {/* Task management sidebar */}
          <div 
            className={`transition-all duration-300 ease-in-out ${
              isFullscreen ? 'w-0 opacity-0 overflow-hidden' : 'w-80'
            }`}
            data-fullscreen={isFullscreen}
          >
            <TaskSidebar />
          </div>
          
          {/* Main content area */}
          <div id="main-content" className="flex-1 flex relative" style={{ width: 'calc(100% - 320px)' }}>
            {/* Chat area */}
            <div 
              className={`transition-all duration-300 ease-in-out ${
                isFullscreen ? 'w-0 opacity-0 overflow-hidden' : 'flex-shrink-0'
              }`}
              style={!isFullscreen ? { width: `${chatAreaWidth}%` } : {}}
              data-fullscreen={isFullscreen}
            >
              <ChatArea 
                selectedStep={selectedStep}
                onStepSelect={handleStepSelect}
                onMcpResultSelect={handleMcpResultSelect}
                onToolSelect={handleToolSelect}
                welcomeAnimationCompleted={welcomeAnimationCompleted}
              />
            </div>
            
            {/* Drag splitter */}
            <div
              className={`transition-all duration-300 ease-in-out ${
                isFullscreen ? 'w-0 opacity-0 overflow-hidden' : 'w-1 bg-gray-50 hover:bg-gray-300 cursor-col-resize flex-shrink-0 relative group'
              }`}
              onMouseDown={handleDragStart}
            >
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-0.5 h-8 bg-gray-400 group-hover:bg-gray-500 transition-colors" />
              </div>
            </div>
            
            {/* Step detail panel */}
            <div 
              className="flex-shrink-0 transition-all duration-300 ease-in-out"
              style={{ width: isFullscreen ? '100%' : `${100 - chatAreaWidth}%`, zIndex: 1 }}
              data-fullscreen={isFullscreen}
            >
              {renderDetailPanel()}
            </div>
          </div>
        </div>
      } />
    </Routes>
    </>
  );
};

const App: React.FC = () => {
  // Doc-site mode (controlled by the private overlay): no login required; only shows the help doc page
  if (isDocSiteMode) {
    return (
      <Routes>
        <Route path="*" element={<HelpDocumentPage />} />
      </Routes>
    );
  }

  // Whether login is required is controlled by the private overlay (in the open-source build AuthGate is a passthrough and does not enable login)
  return (
    <Routes>
      <Route path="/report/:sessionId" element={<ReportPage />} />
      <Route
        path="/*"
        element={
          <AuthGate>
            <AppProvider>
              <AppContent />
              <Toaster />
            </AppProvider>
          </AuthGate>
        }
      />
    </Routes>
  );
};

export default App;
