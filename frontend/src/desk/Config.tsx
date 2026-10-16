import React, { useEffect, useState } from 'react';
import { NavLink, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import ModelManagementSettings from '../components/management/ModelManagementDialog';
import FingerprintTabContent from '../components/management/FingerprintTabContent';
import VulnerabilityTabContent from '../components/management/VulnerabilityTabContent';
import EvaluationTabContent from '../components/management/EvaluationTabContent';

const sections = ['models', 'fingerprints', 'vulns', 'evals'] as const;
type Section = typeof sections[number];

const Config: React.FC = () => {
  const { t } = useTranslation();
  const params = useParams();
  const section = (sections.includes(params.section as Section) ? params.section : 'models') as Section;

  return (
    <div className="flex h-full">
      <nav className="flex w-52 shrink-0 flex-col gap-1 border-r border-gray-200 bg-white p-4 text-sm">
        {sections.map(id => (
          <NavLink
            key={id}
            to={`/config/${id}`}
            className={({ isActive }) => `rounded-md px-3 py-2 ${isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
          >
            {t(`desk.config.${id}`)}
          </NavLink>
        ))}
      </nav>
      <div className="flex min-w-0 flex-1 flex-col bg-white">
        {section === 'models' ? <ModelManagementSettings /> : <Library section={section} />}
      </div>
    </div>
  );
};

const Library: React.FC<{ section: Exclude<Section, 'models'> }> = ({ section }) => {
  const { t } = useTranslation();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const path = section === 'fingerprints' ? 'fingerprints' : section === 'vulns' ? 'vulnerabilities' : 'evaluations';

  const load = async (nextPage = page, q = searchTerm) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(nextPage), size: '10', ...(q ? { q } : {}) });
      const response = await fetch(`/api/v1/knowledge/${path}?${params}`);
      const body = await response.json();
      if (body.status !== 0) {
        toast.error(body.message || t('common.error'));
        return;
      }
      setItems(body.data?.items || []);
      setTotal(body.data?.total || 0);
      setTotalPages(Math.max(1, Math.ceil((body.data?.total || 0) / 10)));
    } catch {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSearchTerm('');
    setPage(1);
    load(1, '');
    // section change reloads the library
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section]);

  const shared = {
    loading,
    searchTerm,
    setSearchTerm,
    currentPage: page,
    totalPages,
    total,
    setCurrentPage: (value: number) => { setPage(value); load(value, searchTerm); },
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col p-4">
      {section === 'fingerprints' && (
        <FingerprintTabContent {...shared} fingerprints={items} fetchFingerprints={(p, _s, q) => { const query = q ?? searchTerm; setSearchTerm(query); setPage(p || 1); load(p || 1, query); }} />
      )}
      {section === 'vulns' && (
        <VulnerabilityTabContent {...shared} vulnerabilities={items} fetchVulnerabilities={(p, _s, q) => { const query = q ?? searchTerm; setSearchTerm(query); setPage(p || 1); load(p || 1, query); }} />
      )}
      {section === 'evals' && (
        <EvaluationTabContent {...shared} evaluations={items} fetchEvaluations={(p, _s, q) => { const query = q ?? searchTerm; setSearchTerm(query); setPage(p || 1); load(p || 1, query); }} />
      )}
    </div>
  );
};

export default Config;
