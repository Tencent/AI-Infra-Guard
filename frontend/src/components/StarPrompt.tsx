import React, { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, ExternalLink, ShieldAlert, Star, X } from 'lucide-react';
import { Trans, useTranslation } from 'react-i18next';
import { sensitiveContact } from '@/config/privateModules';

interface StarPromptProps {
  githubUrl: string;
}

const StarPrompt: React.FC<StarPromptProps> = ({ githubUrl }) => {
  const { t } = useTranslation();
  const [isVisible, setIsVisible] = useState(true);
  const [activeIndex, setActiveIndex] = useState(0);

  const promptItems = useMemo(() => {
    const items: Array<{ key: string; title: string; content: React.ReactNode; icon: React.ReactNode }> = [
      {
        key: 'star',
        title: t('starPrompt.title'),
        content: (
          <>
            <p className="text-xs text-gray-600">{t('starPrompt.description')}</p>
            <a
              href={githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-xs text-blue-600 hover:text-blue-800 transition-colors"
            >
              {t('starPrompt.goToGithub')}
              <ExternalLink className="w-3 h-3 ml-1" />
            </a>
          </>
        ),
        icon: <Star className="w-4 h-4 text-amber-500 mr-1" />,
      },
    ];

    // If the private overlay provides sensitive-data/collaboration contacts, add them as a second item
    if (sensitiveContact) {
      items.push({
        key: 'business',
        title: t('sensitivePrompt.title'),
        content: (
          <p className="text-xs text-gray-600 leading-relaxed">
            <Trans
              i18nKey={sensitiveContact.i18nKey}
              components={[
                <a
                  key="link"
                  href={sensitiveContact.href}
                  className="text-blue-600 hover:underline cursor-pointer"
                />,
              ]}
            />
          </p>
        ),
        icon: <ShieldAlert className="w-4 h-4 text-yellow-500 mr-1" />,
      });
    }

    return items;
  }, [githubUrl, t]);

  const canSwitch = promptItems.length > 1;
  const activeItem = promptItems[activeIndex];

  useEffect(() => {
    if (!canSwitch) {
      return;
    }

    const timer = window.setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % promptItems.length);
    }, 6000);

    return () => window.clearInterval(timer);
  }, [canSwitch, promptItems.length]);

  useEffect(() => {
    if (activeIndex > promptItems.length - 1) {
      setActiveIndex(0);
    }
  }, [activeIndex, promptItems.length]);

  const goToIndex = (nextIndex: number) => {
    if (!canSwitch) return;
    setActiveIndex((nextIndex + promptItems.length) % promptItems.length);
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-4 w-96 relative">
      <button
        onClick={() => setIsVisible(false)}
        className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 transition-colors"
        aria-label={t('common.close')}
      >
        <X className="w-4 h-4" />
      </button>
      <div className="flex items-center space-x-3">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900 flex items-center mb-2">
            {activeItem.icon}
            {activeItem.title}
          </p>
          {activeItem.content}
        </div>
      </div>
      {canSwitch && (
        <div className="mt-3 flex items-center justify-between">
          <div className="flex items-center gap-1">
            {promptItems.map((item, index) => (
              <button
                key={item.key}
                type="button"
                onClick={() => goToIndex(index)}
                className={`h-1.5 w-4 rounded-full transition-colors ${index === activeIndex ? 'bg-blue-500' : 'bg-gray-300 hover:bg-gray-400'}`}
                aria-label={`switch-prompt-${index + 1}`}
              />
            ))}
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => goToIndex(activeIndex - 1)}
              className="p-1 text-gray-500 hover:text-gray-700 transition-colors"
              aria-label="previous-prompt"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => goToIndex(activeIndex + 1)}
              className="p-1 text-gray-500 hover:text-gray-700 transition-colors"
              aria-label="next-prompt"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default StarPrompt;
