import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary.tsx';
import { env } from './config/env';
import { AppShell } from './config/privateModules';
import './index.css';
import { initPromise } from './i18n';
import App from './App.tsx';
import LanguageQuerySync from './components/LanguageQuerySync.tsx';
import { applyTranslateDomFix } from './utils/domTranslateFix';

// Fix DOM conflicts between translation extensions (Chrome / Google Translate, etc.) and React
applyTranslateDomFix();

/**
 * Render the root application.
 * AppShell is injected by the private overlay: it is a passthrough by default
 * (open-source build); the internal build can wrap it with
 * GoogleOAuthProvider and AuthProvider to enable login capabilities.
 */
const renderApp = () => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <ErrorBoundary>
        <BrowserRouter basename={env.VITE_BASENAME}>
          <AppShell>
            <LanguageQuerySync />
            <App />
          </AppShell>
        </BrowserRouter>
      </ErrorBoundary>
    </StrictMode>,
  );
};

// Wait for i18n initialization before rendering the app (force render on failure to avoid a blank screen)
initPromise
  .then(renderApp)
  .catch(error => {
    console.error('i18n init failed:', error);
    renderApp();
  });
