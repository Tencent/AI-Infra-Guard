import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Brain, ClipboardList, Fingerprint, Library, Plus, ShieldAlert } from 'lucide-react';
import { useLanguage } from '../hooks/useLanguage';
import { useVersionCheck } from '../hooks/useVersionCheck';

const Shell: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const { currentLanguage, changeLanguage } = useLanguage();
  useVersionCheck();

  const onNew = location.pathname === '/' || location.pathname.startsWith('/scan');
  const onRecords = location.pathname.startsWith('/records') || location.pathname.startsWith('/report');
  const title = location.pathname.startsWith('/scan/run')
    ? t('desk.live')
    : onRecords ? t('desk.nav.records') : location.pathname.startsWith('/config') ? t('desk.nav.config') : onNew && location.pathname.startsWith('/scan') ? t('desk.result') : t('desk.nav.new');

  const link = (active: boolean) =>
    `flex items-center gap-2 rounded-md px-2.5 py-2 text-sm ${active ? 'bg-blue-50 font-medium text-blue-700' : 'text-zinc-600 hover:bg-blue-50/60 hover:text-blue-700'}`;

  return (
    <div className="flex h-screen bg-zinc-50 text-zinc-800">
      <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-200 bg-white">
        <div className="flex h-14 items-center gap-2 border-b border-zinc-200 px-4">
          <img src="/images/logo.png" alt="" className="size-7" />
          <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-base font-semibold tracking-widest text-transparent" style={{ fontFamily: 'tencentSans' }}>A.I.G</span>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
          <div>
            <div className="px-2.5 pb-1 text-[11px] font-medium uppercase tracking-wide text-zinc-400">{t('desk.nav.scan')}</div>
            <NavLink to="/" end className={() => link(onNew && !location.pathname.startsWith('/scan'))}>
              <Plus className="size-4" />
              {t('desk.nav.new')}
            </NavLink>
            <NavLink to="/records" className={() => link(onRecords)}>
              <ClipboardList className="size-4" />
              {t('desk.nav.records')}
            </NavLink>
          </div>
          <div>
            <div className="px-2.5 pb-1 text-[11px] font-medium uppercase tracking-wide text-zinc-400">{t('desk.nav.config')}</div>
            <NavLink to="/config/models" className={({ isActive }) => link(isActive)}>
              <Brain className="size-4" />
              {t('desk.config.models')}
            </NavLink>
            <NavLink to="/config/fingerprints" className={({ isActive }) => link(isActive)}>
              <Fingerprint className="size-4" />
              {t('desk.config.fingerprints')}
            </NavLink>
            <NavLink to="/config/vulns" className={({ isActive }) => link(isActive)}>
              <ShieldAlert className="size-4" />
              {t('desk.config.vulns')}
            </NavLink>
            <NavLink to="/config/evals" className={({ isActive }) => link(isActive)}>
              <Library className="size-4" />
              {t('desk.config.evals')}
            </NavLink>
          </div>
        </nav>
        <div className="border-t border-zinc-200 p-3">
          <button
            type="button"
            className="w-full rounded-md px-2.5 py-2 text-left text-sm text-zinc-500 hover:bg-blue-50 hover:text-blue-700"
            onClick={() => changeLanguage(currentLanguage?.startsWith('en') ? 'zh' : 'en')}
          >
            {currentLanguage?.startsWith('en') ? '中文' : 'English'}
          </button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center border-b border-zinc-200 bg-white px-4">
          <h1 className="text-sm font-medium">{title}</h1>
        </header>
        <div className="min-h-0 flex-1">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default Shell;
