import React from 'react';
import { useTranslation } from 'react-i18next';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import { Fingerprint, Edit, Trash2, Search, XCircle, Shield, Plus } from 'lucide-react';
import PaginationBar from './PaginationBar';
import YamlUploadDialog from './YamlUploadDialog';
import YamlEditDialog from './YamlEditDialog';
import yaml from 'js-yaml';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

interface FingerprintInfo {
  name: string;
  author: string;
  example: string[];
  desc: string;
  severity: string;
  metadata: {
    product: string;
    vendor: string;
  };
}

interface FingerprintType {
  info: FingerprintInfo;
  http: Array<{
    method: string;
    path: string;
    matchers: string[];
  }>;
}

interface FingerprintTabContentProps {
  fingerprints: FingerprintType[];
  loading: boolean;
  searchTerm: string;
  setSearchTerm: (v: string) => void;
  currentPage: number;
  totalPages: number;
  total?: number;
  setCurrentPage: (v: number) => void;
  fetchFingerprints: (page?: number, size?: number, q?: string) => void;
}

const getSeverityColor = (severity: string) => {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'bg-red-300 text-red-800 hover:bg-red-300 hover:text-red-800';
    case 'high':
      return 'bg-red-100 text-red-800 hover:bg-red-100 hover:text-red-800';
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100 hover:text-yellow-800';
    case 'low':
      return 'bg-green-100 text-green-800 hover:bg-green-100 hover:text-green-800';
    default:
      return 'bg-gray-100 text-gray-800 hover:bg-gray-100 hover:text-gray-800';
  }
};

const FingerprintTabContent: React.FC<FingerprintTabContentProps> = ({
  fingerprints,
  loading,
  searchTerm,
  setSearchTerm,
  currentPage,
  totalPages,
  total,
  setCurrentPage,
  fetchFingerprints,
}) => {
  const [uploadDialogOpen, setUploadDialogOpen] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [uploadError, setUploadError] = React.useState('');
  const [editDialogOpen, setEditDialogOpen] = React.useState(false);
  const [editYamlContent, setEditYamlContent] = React.useState('');
  const [editLoading, setEditLoading] = React.useState(false);
  const [editError, setEditError] = React.useState('');
  const [editTarget, setEditTarget] = React.useState<FingerprintType | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState('');
  const [deleteLoading, setDeleteLoading] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState('');
  const [isEditFullscreen, setIsEditFullscreen] = React.useState(false);

  const { t } = useTranslation();

  // Upload the fingerprint yaml
  const handleUploadFingerprint = async (file: File) => {
    setUploading(true);
    setUploadError('');
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const content = e.target?.result as string;
        const response = await fetch('/api/v1/knowledge/fingerprints', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            file_content: content,
          }),
        });
        const data = await response.json();
                  if (data.status === 0) {
            setUploadDialogOpen(false);
            toast.success(t('knowledgeBase.createFingerprintSuccess'), {
              description: t('knowledgeBase.fingerprintSuccessfullyUploaded'),
            });
            fetchFingerprints(1, 10, searchTerm);
          } else {
            setUploadError(data.message || t('knowledgeBase.uploadFailed'));
            toast.error(t('knowledgeBase.createFingerprintFailed'), {
              description: data.message || t('knowledgeBase.uploadFailed'),
            });
          }
        setUploading(false);
      };
      reader.readAsText(file);
    } catch (error) {
      setUploadError(t('knowledgeBase.fileReadOrUploadFailed'));
      toast.error(t('knowledgeBase.createFingerprintFailed'), {
        description: t('knowledgeBase.fileReadOrUploadFailed'),
      });
      setUploading(false);
    }
  };

  // Download the sample yaml
  const downloadSampleYaml = () => {
    const sample = `info:
  name: dify
  author: ${t('knowledgeBase.sampleAuthor')}
  severity: info
  metadata:
    product: dify
    vendor: dify
http:
  - method: GET
    path: '/'
    matchers:
      - body="<title>Dify</title>" || icon="97378986"
version:
  - method: GET
    path: '/console/api/version'
    extractor:
      part: header
      group: 1
      regex: 'x-version:\s*(\\d+\\.\\d+\\.?\\d+?)'
`;
    const blob = new Blob([sample], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = t('knowledgeBase.sampleFileName');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Open the edit dialog
  const handleEditFingerprint = (fingerprint: FingerprintType) => {
    setEditTarget(fingerprint);
    try {
      setEditYamlContent(yaml.dump(fingerprint));
    } catch (e) {
      setEditYamlContent('');
    }
    setEditDialogOpen(true);
    setEditError('');
  };

  // Save the edits
  const handleSaveEdit = async () => {
    if (!editTarget?.info?.name) {
      setEditError(t('knowledgeBase.fingerprintNameMissing'));
      toast.error(t('knowledgeBase.editFingerprintFailed'), {
        description: t('knowledgeBase.fingerprintNameMissing'),
      });
      return;
    }
    setEditLoading(true);
    setEditError('');
    try {
      const response = await fetch(`/api/v1/knowledge/fingerprints/${editTarget.info.name}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_content: editYamlContent,
        }),
      });
      const data = await response.json();
      if (data.status === 0) {
        setEditDialogOpen(false);
        toast.success(t('knowledgeBase.editFingerprintSuccess'), {
          description: t('knowledgeBase.fingerprintSuccessfullyUpdated'),
        });
        fetchFingerprints(1, 10, searchTerm);
      } else {
        setEditError(data.message || t('common.save'));
        toast.error(t('knowledgeBase.editFingerprintFailed'), {
          description: data.message || t('common.save'),
        });
      }
    } catch (error) {
      setEditError(t('common.save'));
      toast.error(t('knowledgeBase.editFingerprintFailed'), {
        description: t('common.save'),
      });
    }
    setEditLoading(false);
  };

  // Delete the fingerprint
  const deleteFingerprints = async (names: string[]) => {
    try {
      const response = await fetch('/api/v1/knowledge/fingerprints', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: names }),
      });
      const data = await response.json();
      if (data.status === 0) {
        toast.success(t('knowledgeBase.deleteFingerprintSuccess'), {
          description: t('knowledgeBase.fingerprintSuccessfullyDeleted'),
        });
        fetchFingerprints(currentPage, 10, searchTerm);
      } else {
        setDeleteError(data.message || t('knowledgeBase.deleteFingerprintFailed'));
        toast.error(t('knowledgeBase.deleteFingerprintFailed'), {
          description: data.message || t('knowledgeBase.deleteFingerprintFailed'),
        });
      }
    } catch (error) {
      setDeleteError(t('knowledgeBase.deleteFingerprintFailed'));
      toast.error(t('knowledgeBase.deleteFingerprintFailed'), {
        description: t('knowledgeBase.deleteFingerprintFailed'),
      });
    }
  };

  // Trigger the delete dialog
  const handleDeleteClick = (target: string) => {
    setDeleteTarget(target);
    setDeleteDialogOpen(true);
    setDeleteError('');
  };

  // Confirm deletion
  const handleConfirmDelete = async () => {
    setDeleteLoading(true);
    setDeleteError('');
    try {
      await deleteFingerprints([deleteTarget]);
      setDeleteDialogOpen(false);
    } catch (e) {
      setDeleteError(t('knowledgeBase.deleteFingerprintFailed'));
    }
    setDeleteLoading(false);
  };

  return (
    <>
      <div className='pb-4'>
        <div className='flex items-center gap-2'>
          <div className='relative flex-1'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
            <Input
              placeholder={t('knowledgeBase.searchFingerprintPlaceholder')}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  setCurrentPage(1);
                  fetchFingerprints(1, 10, searchTerm);
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
                  fetchFingerprints(1, 10, '');
                }}
                tabIndex={-1}
              >
                <XCircle className='w-4 h-4' />
              </button>
            )}
          </div>
          <Button onClick={() => {
            setCurrentPage(1);
            fetchFingerprints(1, 10, searchTerm);
          }}>
                         {t('common.search')}
          </Button>
          <Button className='gap-0' variant='outline' onClick={() => setUploadDialogOpen(true)}>
            <Plus className='w-4 h-4' />
                         {t('knowledgeBase.createFingerprint')}
          </Button>
        </div>
      </div>
      <div className='flex-1 min-h-0 flex flex-col'>
        <ScrollArea className='flex-1 min-h-0'>
          {loading ? (
            <div className='flex items-center justify-center py-8'>
              <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
            </div>
          ) : fingerprints.length === 0 ? (
            <div className='text-center py-8 text-gray-500'>
              <Shield className='w-12 h-12 mx-auto mb-4 opacity-50' />
                             <p>{t('knowledgeBase.noFingerprintData')}</p>
            </div>
          ) : (
            <div className='space-y-3'>
              {fingerprints.map((fingerprint, index) => (
                <div key={index} className='border rounded-lg p-4 bg-white'>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center gap-3'>
                      <h3 className='font-semibold text-gray-900'>
                                                 {fingerprint.info?.name || t('knowledgeBase.unknown')}
                      </h3>
                                              <Badge className={`${getSeverityColor(fingerprint.info?.severity || t('knowledgeBase.unknown'))} hover:no-underline`}>
                                                 {fingerprint.info?.severity || t('knowledgeBase.unknown')}
                      </Badge>
                    </div>
                    <div className='flex items-center gap-2'>
                      <Button className='px-2' size='sm' variant='outline' onClick={() => handleEditFingerprint(fingerprint)}>
                        <Edit className='w-4 h-4' />
                      </Button>
                      <Button
                        size='sm'
                        variant='outline'
                        className='text-red-600 hover:bg-red-50 hover:text-red-700 px-2'
                        onClick={() => handleDeleteClick(fingerprint.info?.name || '')}
                      >
                        <Trash2 className='w-4 h-4' />
                      </Button>
                    </div>
                  </div>
                  <p className='text-sm text-gray-600 my-4'>
                                         {fingerprint.info?.desc || t('knowledgeBase.noDescription')}
                  </p>
                  <div className='flex items-center gap-4 text-xs text-gray-500'>
                                         <span>{t('knowledgeBase.contributor')}: <span className='text-blue-600 font-bold'>{fingerprint.info?.author || t('knowledgeBase.unknown')}</span></span>
                     <span>{t('knowledgeBase.product')}: {fingerprint.info?.metadata?.product || t('knowledgeBase.unknown')}</span>
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
            fetchFingerprints(page, 10, searchTerm);
          }}
        />
      </div>
      {/* Upload fingerprint dialog */}
      <YamlUploadDialog
        open={uploadDialogOpen}
        onClose={(open) => {
          setUploadDialogOpen(open);
          if (!open) setUploadError('');
        }}
        onUpload={handleUploadFingerprint}
        loading={uploading}
        error={uploadError}
        onDownloadSample={downloadSampleYaml}
        title={t('knowledgeBase.uploadFingerprintYaml')}
        type='fingerprint'
      />
      {/* Edit fingerprint dialog */}
      <YamlEditDialog
        open={editDialogOpen}
        onClose={setEditDialogOpen}
        onSave={handleSaveEdit}
        loading={editLoading}
        error={editError}
        yamlContent={editYamlContent}
        onYamlChange={setEditYamlContent}
        isFullscreen={isEditFullscreen}
        onToggleFullscreen={() => setIsEditFullscreen(!isEditFullscreen)}
        title={t('knowledgeBase.editFingerprintYaml')}
      />
      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className='max-w-sm'>
          <DialogHeader>
                         <DialogTitle>{t('knowledgeBase.confirmDelete')}</DialogTitle>
          </DialogHeader>
          <div className='py-4'>
            <div className='text-base text-gray-800 pb-4'>
                             {t('knowledgeBase.confirmDeleteMessage', { type: t('knowledgeBase.fingerprint'), target: deleteTarget })}
            </div>
            {deleteError && <div className='text-red-500 text-sm'>{deleteError}</div>}
            <div className='flex gap-2 mt-4'>
              <Button onClick={handleConfirmDelete} disabled={deleteLoading}>
                                 {t('knowledgeBase.confirm')}
              </Button>
              <Button
                variant='outline'
                onClick={() => setDeleteDialogOpen(false)}
                disabled={deleteLoading}
              >
                                 {t('knowledgeBase.cancel')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default FingerprintTabContent; 