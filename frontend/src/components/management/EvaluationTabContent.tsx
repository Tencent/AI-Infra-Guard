import React from 'react';
import { useTranslation } from 'react-i18next';
import i18n from '../../i18n';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import { BookOpen, Search, XCircle, Star, Plus, Download, Upload, Edit, Trash2 } from 'lucide-react';
import PaginationBar from './PaginationBar';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog';
import { toast } from 'sonner';

interface EvaluationItem {
  name: string;
  description: string;
  description_zh: string;
  author: string;
  source: string[];
  count: number;
  tags: string[];
  recommendation: number;
  language: string;
  default?: boolean;
  official?: boolean;
}

interface EvaluationTabContentProps {
  evaluations: EvaluationItem[];
  loading: boolean;
  searchTerm: string;
  setSearchTerm: (v: string) => void;
  currentPage: number;
  totalPages: number;
  total?: number;
  setCurrentPage: (v: number) => void;
  fetchEvaluations: (page?: number, size?: number, q?: string) => void;
}

const EvaluationTabContent: React.FC<EvaluationTabContentProps> = ({
  evaluations,
  loading,
  searchTerm,
  setSearchTerm,
  currentPage,
  totalPages,
  total,
  setCurrentPage,
  fetchEvaluations,
}) => {
  const { t } = useTranslation();
  const [detailOpen, setDetailOpen] = React.useState(false);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [detailError, setDetailError] = React.useState('');
  const [detailData, setDetailData] = React.useState<any>(null);
  const [detailPage, setDetailPage] = React.useState(1);
  const [detailPageSize] = React.useState(20);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [createLoading, setCreateLoading] = React.useState(false);
  const [fileInputRef] = React.useState(React.createRef<HTMLInputElement>());
  const [editOpen, setEditOpen] = React.useState(false);
  const [editLoading, setEditLoading] = React.useState(false);
  const [editingItem, setEditingItem] = React.useState<EvaluationItem | null>(null);
  const [editJsonContent, setEditJsonContent] = React.useState('');
  const [editFileInputRef] = React.useState(React.createRef<HTMLInputElement>());
  const [deleteLoading, setDeleteLoading] = React.useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = React.useState(false);
  const [itemToDelete, setItemToDelete] = React.useState<string | null>(null);

  const handleShowDetail = async (name: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError('');
    setDetailData(null);
    setDetailPage(1);
    try {
      const response = await fetch(`/api/v1/knowledge/evaluations/${encodeURIComponent(name)}`);
      const data = await response.json();
      if (data.status === 0) {
        setDetailData(data.data);
      } else {
        setDetailError(data.message || t('evaluationTab.getDetailsFailed'));
      }
    } catch (e) {
      setDetailError(t('evaluationTab.getDetailsFailed'));
    }
    setDetailLoading(false);
  };

  const pagedData = detailData && detailData.data
    ? detailData.data.slice((detailPage - 1) * detailPageSize, detailPage * detailPageSize)
    : [];
  const totalDetailPages = detailData && detailData.data
    ? Math.ceil(detailData.data.length / detailPageSize)
    : 1;

  const handleDownloadTemplate = () => {
    const template = {
      name: 'TestDataset',
      description: 'Test evaluation dataset',
      description_zh: '测试用评测数据集',
      author: '贡献者',
      source: ['https://example.com/dataset'],
      tags: ['测试', '示例'],
      recommendation: 3,
      language: 'zh',
      data: [
        {
          source: '手工创建',
          prompt: '请介绍一下人工智能的发展历史',
        },
        {
          source: '手工创建',
          prompt: '什么是机器学习？',
        },
      ],
    };
    const blob = new Blob([JSON.stringify(template, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'evaluation_template.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
          toast.success(t('evaluationTab.sampleFileDownloadSuccess'));
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.json')) {
      toast.error(t('evaluationTab.pleaseSelectJsonFile'));
      return;
    }

    setCreateLoading(true);
    try {
      const content = await file.text();
      const jsonData = JSON.parse(content);
      
      const response = await fetch('/api/v1/knowledge/evaluations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_content: content,
        }),
      });

      const result = await response.json();
      if (result.status === 0) {
        toast.success(t('evaluationTab.createEvaluationSuccess'));
        setCreateOpen(false);
        fetchEvaluations(currentPage, 10, searchTerm);
      } else {
        toast.error(result.message || t('evaluationTab.createEvaluationFailed'));
      }
    } catch (error) {
      toast.error(t('evaluationTab.fileFormatErrorOrUploadFailed'));
    }
    setCreateLoading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleEdit = (item: EvaluationItem, event: React.MouseEvent) => {
    event.stopPropagation();
    if (item.official) {
      return;
    }
    setEditingItem(item);
    setEditJsonContent('');
    setEditOpen(true);
    // Fetch the details of the current evaluation set
    fetchEvaluationDetail(item.name);
  };

  const fetchEvaluationDetail = async (name: string) => {
    try {
      const response = await fetch(`/api/v1/knowledge/evaluations/${encodeURIComponent(name)}`);
      const data = await response.json();
      if (data.status === 0) {
        // Build the full evaluation-set JSON data
        const evaluationData = {
          name: name,
          default: data.data.default || false,
          description: data.data.description || '',
          description_zh: data.data.description_zh || '',
          author: data.data.author || '',
          source: data.data.source || [],
          tags: data.data.tags || [],
          official: data.data.official || false,
          recommendation: data.data.recommendation || 3,
          language: data.data.language || 'zh',
          data: data.data.data || [],
        };
        setEditJsonContent(JSON.stringify(evaluationData, null, 2));
      } else {
        toast.error(t('evaluationTab.getEvaluationDetailsFailed'));
      }
    } catch (error) {
      toast.error(t('evaluationTab.getEvaluationDetailsFailed'));
    }
  };

  const handleDelete = async (item: EvaluationItem, event: React.MouseEvent) => {
    event.stopPropagation();
    if (item.official) {
      return;
    }
    setItemToDelete(item.name);
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (!itemToDelete) return;
    
    setDeleteLoading(itemToDelete);
    try {
      const response = await fetch('/api/v1/knowledge/evaluations', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          names: [itemToDelete],
        }),
      });

      const result = await response.json();
      if (result.status === 0) {
        toast.success(t('evaluationTab.deleteEvaluationSuccess'));
        fetchEvaluations(currentPage, 10, searchTerm);
      } else {
        toast.error(result.message || t('evaluationTab.deleteEvaluationFailed'));
      }
    } catch (error) {
      toast.error(t('evaluationTab.deleteEvaluationFailed'));
    }
    setDeleteLoading(null);
    setDeleteConfirmOpen(false);
    setItemToDelete(null);
  };

  const handleEditFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.json')) {
      toast.error('请选择JSON格式的文件');
      return;
    }

    try {
      const content = await file.text();
      setEditJsonContent(content);
    } catch (error) {
      toast.error(t('evaluationTab.fileReadFailed'));
    }
    if (editFileInputRef.current) {
      editFileInputRef.current.value = '';
    }
  };

  const handleSaveEdit = async () => {
    if (!editingItem || !editJsonContent.trim()) {
      toast.error(t('evaluationTab.pleaseProvideValidJson'));
      return;
    }

    setEditLoading(true);
    try {
      const response = await fetch(`/api/v1/knowledge/evaluations/${encodeURIComponent(editingItem.name)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_content: editJsonContent,
        }),
      });

      const result = await response.json();
      if (result.status === 0) {
        toast.success(t('evaluationTab.editEvaluationSuccess'));
        setEditOpen(false);
        fetchEvaluations(currentPage, 10, searchTerm);
      } else {
        toast.error(result.message || t('evaluationTab.editEvaluationFailed'));
      }
    } catch (error) {
      toast.error(t('evaluationTab.editEvaluationFailed'));
    }
    setEditLoading(false);
  };

  const handleDownloadCurrentEvaluation = () => {
    if (!editingItem || !editJsonContent.trim()) {
      toast.error(t('evaluationTab.noDataToDownload'));
      return;
    }

    try {
      const blob = new Blob([editJsonContent], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${editingItem.name}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(t('evaluationTab.currentEvaluationDataDownloadSuccess'));
    } catch (error) {
      toast.error(t('evaluationTab.downloadFailed'));
    }
  };

  return (
    <>
      <div className='pb-4'>
        <div className='flex items-center gap-2'>
          <div className='relative flex-1'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
            <Input
              placeholder={t('evaluationTab.searchPlaceholder')}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  setCurrentPage(1);
                  fetchEvaluations(1, 10, searchTerm);
                }
              }}
              className='pl-10 pr-8'
            />
            {searchTerm && (
              <button
                type='button'
                className='absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600'
                style={{ outline: 'none', border: 'none', background: 'transparent', cursor: 'pointer' }}
                onClick={() => {
                  setSearchTerm('');
                  setCurrentPage(1);
                  fetchEvaluations(1, 10, '');
                }}
                tabIndex={-1}
              >
                <XCircle className='w-4 h-4' />
              </button>
            )}
          </div>
          <Button onClick={() => {
            setCurrentPage(1);
            fetchEvaluations(1, 10, searchTerm);
          }}>
            {t('evaluationTab.search')}
          </Button>
          <Button onClick={() => setCreateOpen(true)} variant='outline' className='gap-0'>
            <Plus className='w-4 h-4' />
            {t('evaluationTab.createEvaluation')}
          </Button>
        </div>
      </div>
      <div className='flex-1 min-h-0 flex flex-col'>
        <ScrollArea className='flex-1 min-h-0'>
          {loading ? (
            <div className='flex items-center justify-center py-8'>
              <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
            </div>
          ) : evaluations.length === 0 ? (
            <div className='text-center py-8 text-gray-500'>
              <BookOpen className='w-12 h-12 mx-auto mb-4 opacity-50' />
              <p>{t('evaluationTab.noEvaluationData')}</p>
            </div>
          ) : (
            <div className='space-y-3'>
              {evaluations.map((item, index) => (
                <div key={index} className='border rounded-lg p-4 bg-white cursor-pointer' onClick={() => handleShowDetail(item.name)}
                title={t('evaluationTab.clickToViewDetails')}>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center gap-3'>
                      <h3
                        className='font-semibold text-gray-900'
                      >
                        {item.name}
                      </h3>
                      {item.official && (
                        <span className='text-xs text-blue-600 bg-blue-50 px-1 rounded'>{t('evaluationTab.official')}</span>
                      )}
                      <Badge>{item.language}</Badge>
                      {/* Recommendation stars */}
                                              <span className='text-xs text-yellow-600 flex items-center gap-0.5'>
                          {t('evaluationTab.recommendationIndex')}：
                          {Array.from({
                            length: item.recommendation,
                          }).map((_, i) => (
                            <Star key={i} className='inline w-4 h-4 fill-yellow-400 stroke-yellow-600' />
                          ))}
                        </span>
                                              <span className='text-xs text-gray-500'>
                          {t('evaluationTab.totalItems', { count: item.count || 0 })}
                        </span>
                    </div>
                    <div className='flex items-center gap-2'>
                      <Button
                        size='sm'
                        variant='outline'
                        onClick={e => handleEdit(item, e)}
                        disabled={item.official}
                        className='h-8 px-2'
                      >
                        <Edit className='w-3 h-3' />
                      </Button>
                      <Button
                        size='sm'
                        variant='outline'
                        onClick={e => handleDelete(item, e)}
                        disabled={deleteLoading === item.name || item.official}
                        className='h-8 px-2 text-red-600 hover:text-red-700 hover:bg-red-50'
                      >
                        {deleteLoading === item.name ? (
                          <div className='animate-spin rounded-full h-3 w-3 border-b-2 border-red-600'></div>
                        ) : (
                          <Trash2 className='w-3 h-3' />
                        )}
                      </Button>
                    </div>
                  </div>
                  <div className='flex flex-wrap gap-2 my-4'>
                    {item.tags && item.tags.map((tag, i) => (
                      <Badge key={i} variant='outline' className='bg-gray-50 text-gray-600 border-gray-200'>{tag}</Badge>
                    ))}
                  </div>
                  <div className='my-4 text-sm text-gray-700'>
                    {i18n.language === 'zh' ? item.description_zh || item.description : item.description || item.description_zh}
                  </div>
                  <div className='mt-2 flex items-center gap-4 text-xs text-gray-500'>
                    {item.author && (
                      <span className='flex-shrink-0'>{t('evaluationTab.contributor')}<span className="text-blue-600 font-bold">{item.author}</span></span>
                    )}
                    {item.source && item.source.length > 0 && (
                                              <span className='flex-1 min-w-0 truncate' title={item.source[0]}>
                          {t('evaluationTab.source')}{item.source[0]}{item.source.length > 1 ? ` ${t('evaluationTab.sourceMultiple', { count: item.source.length || 0 })}` : ''}
                        </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
        <PaginationBar
          currentPage={currentPage}
          totalPages={totalPages}
          total={total}
          onPageChange={page => {
            setCurrentPage(page);
            fetchEvaluations(page, 10, searchTerm);
          }}
        />
      </div>
      {/* Details dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className='max-w-3xl h-[80vh] max-h-[90vh] flex flex-col'>
          <DialogHeader>
            <DialogTitle>{t('evaluationTab.evaluationDetails')}</DialogTitle>
          </DialogHeader>
          {detailLoading ? (
            <div className='flex-1 flex items-center justify-center'>
              <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
            </div>
          ) : detailError ? (
            <div className='text-red-500 text-center flex-1 flex items-center justify-center'>{detailError}</div>
          ) : detailData ? (
            <div className='flex-1 flex flex-col min-h-0'>
              <ScrollArea className='flex-1 min-h-0'>
                <table className='w-full text-sm border'>
                  <thead>
                    <tr className='bg-gray-100'>
                      <th className='border px-2 py-1 text-left'>#</th>
                      <th className='border px-2 py-1 text-left'>{t('evaluationTab.prompt')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagedData.map((row: any, idx: number) => (
                      <tr key={idx}>
                        <td className='border px-2 py-1'>{(detailPage - 1) * detailPageSize + idx + 1}</td>
                        <td className='border px-2 py-1 break-all'>{row.prompt}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollArea>
              <PaginationBar
                currentPage={detailPage}
                totalPages={totalDetailPages}
                total={detailData?.data?.length}
                onPageChange={page => setDetailPage(page)}
              />
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
      {/* Create evaluation-set dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className='max-w-md'>
          <DialogHeader>
            <DialogTitle>{t('evaluationTab.createEvaluationTitle')}</DialogTitle>
          </DialogHeader>
          <div className='space-y-4'>
            <div className='text-sm text-gray-600'>
              {t('evaluationTab.createEvaluationDescription')}
            </div>
            <div className='space-y-3'>
              <Button onClick={handleDownloadTemplate} variant='outline' className='w-full'>
                <Download className='w-4 h-4 mr-2' />
                {t('evaluationTab.downloadSampleFile')}
              </Button>
              <div className='relative'>
                <input
                  ref={fileInputRef}
                  type='file'
                  accept='.json'
                  onChange={handleFileUpload}
                  className='hidden'
                />
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={createLoading}
                  className='w-full'
                >
                  <Upload className='w-4 h-4 mr-2' />
                  {createLoading ? t('evaluationTab.uploading') : t('evaluationTab.uploadJsonFile')}
                </Button>
              </div>
            </div>
            <div className='text-xs text-gray-500'>
              <p>{t('evaluationTab.jsonFormatRequirements')}</p>
              <ul className='list-disc list-inside mt-1 space-y-1'>
                <li>{t('evaluationTab.jsonFormatName')}</li>
                <li>{t('evaluationTab.jsonFormatDescription')}</li>
                <li>{t('evaluationTab.jsonFormatDescriptionZh')}</li>
                <li>{t('evaluationTab.jsonFormatAuthor')}</li>
                <li>{t('evaluationTab.jsonFormatSource')}</li>
                <li>{t('evaluationTab.jsonFormatTags')}</li>
                <li>{t('evaluationTab.jsonFormatRecommendation')}</li>
                <li>{t('evaluationTab.jsonFormatLanguage')}</li>
                <li>{t('evaluationTab.jsonFormatData')}</li>
              </ul>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {/* Edit evaluation-set dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className='max-w-4xl h-[80vh] max-h-[90vh] flex flex-col'>
          <DialogHeader>
            <DialogTitle>{t('evaluationTab.editEvaluationTitle', { name: editingItem?.name })}</DialogTitle>
          </DialogHeader>
          <div className='flex-1 flex flex-col min-h-0 space-y-4'>
            <div className='flex-1 min-h-0'>
              <textarea
                value={editJsonContent}
                onChange={e => setEditJsonContent(e.target.value)}
                placeholder={t('evaluationTab.editEvaluationPlaceholder')}
                className='w-full h-full p-3 border rounded-md font-mono text-sm resize-none outline-none'
                style={{ minHeight: '300px' }}
              />
            </div>
            <div className='flex justify-between items-center gap-2'>
              <div className='flex gap-2'>
                <Button onClick={handleDownloadCurrentEvaluation} variant='outline' size='sm' className='gap-1'>
                  <Download className='w-4 h-4' />
                  {t('evaluationTab.downloadCurrentData')}
                </Button>
                <div className='relative'>
                  <input
                    ref={editFileInputRef}
                    type='file'
                    accept='.json'
                    onChange={handleEditFileUpload}
                    className='hidden'
                  />
                  <Button
                    onClick={() => editFileInputRef.current?.click()}
                    variant='outline'
                    size='sm'
                    className='gap-1'
                  >
                    <Upload className='w-4 h-4' />
                    {t('evaluationTab.uploadJsonFileEdit')}
                  </Button>
                </div>
              </div>
              <div className='flex gap-2'>
                <Button onClick={handleSaveEdit} disabled={editLoading || !editJsonContent.trim()}>
                  {editLoading ? t('evaluationTab.saving') : t('evaluationTab.save')}
                </Button>
                <Button variant='outline' onClick={() => setEditOpen(false)}>
                  {t('evaluationTab.cancel')}
                </Button>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('evaluationTab.confirmDeleteTitle')}</AlertDialogTitle>
            <AlertDialogDescription className='pb-4'>
              {t('evaluationTab.confirmDeleteDescription', { name: itemToDelete })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className='flex flex-col-reverse sm:flex-row sm:justify-start gap-2'>
            <AlertDialogAction onClick={confirmDelete} disabled={deleteLoading === itemToDelete}>
              {deleteLoading === itemToDelete ? (
                <div className='animate-spin rounded-full h-4 w-4 border-b-2 border-red-600'></div>
              ) : (
                t('evaluationTab.delete')
              )}
            </AlertDialogAction>
            <AlertDialogCancel onClick={() => setDeleteConfirmOpen(false)}>{t('evaluationTab.cancel')}</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default EvaluationTabContent; 