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

  const item = (active: boolean) =>
    active ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900';
  const onRecords = location.pathname.startsWith('/records') || location.pathname.startsWith('/report');
  const onConfig = location.pathname.startsWith('/config');

  return (
    <div className="flex h-screen flex-col bg-gray-50 text-gray-900" style={{ fontFamily: 'tencentSans, sans-serif' }}>
      <header className="flex h-14 shrink-0 items-center gap-8 border-b border-gray-200 bg-white px-8">
        <NavLink to="/" className="text-sm font-medium tracking-wide">
          A.I.G
        </NavLink>
        <nav className="flex gap-6 text-sm">
          <NavLink to="/" end className={({ isActive }) => item(isActive)}>
            {t('desk.nav.new')}
          </NavLink>
          <NavLink to="/records" className={() => item(onRecords)}>
            {t('desk.nav.records')}
          </NavLink>
          <NavLink to="/config/models" className={() => item(onConfig)}>
            {t('desk.nav.config')}
          </NavLink>
        </nav>
        <button
          type="button"
          className="ml-auto text-sm text-gray-400 hover:text-gray-900"
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
