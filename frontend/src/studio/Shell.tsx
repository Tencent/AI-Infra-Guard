import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import { useVersionCheck } from '../hooks/useVersionCheck';

const Shell: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const { currentLanguage, changeLanguage } = useLanguage();
  useVersionCheck();

  const onEvals = location.pathname.startsWith('/eval') || location.pathname.startsWith('/report');
  const item = (active: boolean) => (active ? 'text-neutral-900' : 'text-neutral-400 hover:text-neutral-700');

  return (
    <div className="flex h-screen flex-col bg-white text-neutral-900" style={{ fontFamily: 'tencentSans, sans-serif' }}>
      <header className="flex h-14 shrink-0 items-center gap-8 border-b border-neutral-200 px-8">
        <NavLink to="/" className="text-sm tracking-wide">
          {t('studio.brand')}
        </NavLink>
        <nav className="flex gap-6 text-sm">
          <NavLink to="/" end className={({ isActive }) => item(isActive)}>
            {t('studio.setup')}
          </NavLink>
          <NavLink to="/evals" className={({ isActive }) => item(isActive || onEvals)}>
            {t('studio.evals')}
          </NavLink>
        </nav>
        <button
          type="button"
          className="ml-auto text-sm text-neutral-400 hover:text-neutral-900"
          onClick={() => changeLanguage(currentLanguage?.startsWith('en') ? 'zh' : 'en')}
        >
          {currentLanguage?.startsWith('en') ? '中文' : 'EN'}
        </button>
      </header>
      <div className="min-h-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
};

export default Shell;
