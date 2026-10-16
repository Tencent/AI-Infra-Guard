import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthGate, extraRoutes, isDocSiteMode } from '@/config/privateModules';
import HelpDocumentPage from '../pages/HelpDocumentPage';
import { Toaster } from './ui/sonner';
import Shell from '../desk/Shell';
import NewScan from '../desk/NewScan';
import Records from '../desk/Records';
import EvalView from '../studio/EvalView';
import Config from '../desk/Config';

const App: React.FC = () => {
  if (isDocSiteMode) {
    return (
      <Routes>
        <Route path="*" element={<HelpDocumentPage />} />
      </Routes>
    );
  }

  return (
    <AuthGate>
      <Routes>
        {extraRoutes.map(route => (
          <Route key={route.path} path={route.path} element={route.element} />
        ))}
        <Route path="/help" element={<HelpDocumentPage />} />
        <Route element={<Shell />}>
          <Route path="/" element={<NewScan />} />
          <Route path="/records" element={<Records />} />
          <Route path="/records/:sessionId" element={<EvalView />} />
          <Route path="/report/:sessionId" element={<EvalView />} />
          <Route path="/config/:section" element={<Config />} />
        </Route>
      </Routes>
      <Toaster />
    </AuthGate>
  );
};

export default App;
