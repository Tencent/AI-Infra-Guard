import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';

interface PaginationBarProps {
  currentPage: number;
  totalPages: number;
  total?: number;
  onPageChange: (page: number) => void;
  className?: string;
}

const PaginationBar: React.FC<PaginationBarProps> = ({
  currentPage,
  totalPages,
  total,
  onPageChange,
  className = '',
}) => {
  const { t } = useTranslation();
  const pageWindow = 2;
  let start = Math.max(1, currentPage - pageWindow);
  let end = Math.min(totalPages, currentPage + pageWindow);
  const pages = [];
  if (start > 1) {
    pages.push(
      <Button key={1} variant={currentPage === 1 ? 'default' : 'outline'} onClick={() => onPageChange(1)}>1</Button>
    );
    if (start > 2) pages.push(<span key='start-ellipsis'>...</span>);
  }
  for (let i = start; i <= end; i++) {
    pages.push(
      <Button key={i} variant={currentPage === i ? 'default' : 'outline'} onClick={() => onPageChange(i)}>{i}</Button>
    );
  }
  if (end < totalPages) {
    if (end < totalPages - 1) pages.push(<span key='end-ellipsis'>...</span>);
    pages.push(
      <Button key={totalPages} variant={currentPage === totalPages ? 'default' : 'outline'} onClick={() => onPageChange(totalPages)}>{totalPages}</Button>
    );
  }
  return (
    <div className={`flex justify-center items-center gap-2 py-4 bg-white ${className}`}>
      <div className='flex items-center gap-2'>
        <Button
          variant='outline'
          disabled={currentPage === 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          {t('pagination.previousPage')}
        </Button>
        {pages}
        <Button
          variant='outline'
          disabled={currentPage === totalPages}
          onClick={() => onPageChange(currentPage + 1)}
        >
          {t('pagination.nextPage')}
        </Button>
      </div>
      {total !== undefined && (
        <div className='text-sm text-gray-500 ml-2'>
          {t('pagination.totalItems', { total })}
        </div>
      )}
    </div>
  );
};

export default PaginationBar; 