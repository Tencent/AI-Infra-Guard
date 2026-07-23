import React, { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface VersionResponse {
  version: string;
  changelog: string;
}

interface ChangelogProps {
  onVersionLoaded?: (version: string) => void;
}

const Changelog: React.FC<ChangelogProps> = ({ onVersionLoaded }) => {
  const { t } = useTranslation();
  const [data, setData] = useState<VersionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const fetchChangelog = async () => {
      try {
        const response = await fetch('/api/v1/version');
        if (!response.ok) {
          throw new Error('Failed to fetch version info');
        }
        const jsonData = await response.json();
        setData(jsonData);
        if (jsonData.version && onVersionLoaded) {
          onVersionLoaded(jsonData.version);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchChangelog();
  }, [onVersionLoaded]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-500">
        {t('common.error')}: {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex flex-col h-full bg-white overflow-hidden">
      <div className="flex-1 mb-6 overflow-y-auto scrollbar-hover">
        <div className="px-6 prose prose-gray max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {data.changelog}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
};

export default Changelog;
