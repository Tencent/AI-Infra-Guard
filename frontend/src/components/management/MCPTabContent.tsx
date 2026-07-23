import React from 'react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import { Edit, Trash2, Search, XCircle, Plus, Code, Download, Upload } from 'lucide-react';
import PaginationBar from './PaginationBar';
import YamlUploadDialog from './YamlUploadDialog';
import yaml from 'js-yaml';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { useTranslation } from 'react-i18next';

interface MCPInfo {
  id: string;
  name: string;
  description: string;
  author: string;
  category: string[];
}

interface MCPType {
  info: MCPInfo;
  prompt_template: string;
  RawData: string;
}

interface MCPTabContentProps {
  mcps: MCPType[];
  loading: boolean;
  searchTerm: string;
  setSearchTerm: (v: string) => void;
  currentPage: number;
  totalPages: number;
  total?: number;
  setCurrentPage: (v: number) => void;
  fetchMCPs: (page?: number, size?: number, q?: string) => void;
}

const MCPTabContent: React.FC<MCPTabContentProps> = ({
  mcps,
  loading,
  searchTerm,
  setSearchTerm,
  currentPage,
  totalPages,
  total,
  setCurrentPage,
  fetchMCPs,
}) => {
  const { t } = useTranslation();
  const [uploadDialogOpen, setUploadDialogOpen] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [uploadError, setUploadError] = React.useState('');
  const [editDialogOpen, setEditDialogOpen] = React.useState(false);
  const [editYamlContent, setEditYamlContent] = React.useState('');
  const [editLoading, setEditLoading] = React.useState(false);
  const [editError, setEditError] = React.useState('');
  const [editTarget, setEditTarget] = React.useState<MCPType | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState('');
  const [deleteLoading, setDeleteLoading] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState('');
  const [fileInputRef] = React.useState(React.createRef<HTMLInputElement>());
  const [editFileInputRef] = React.useState(React.createRef<HTMLInputElement>());

  // Upload the MCP yaml
  const handleUploadMCP = async (file: File) => {
    setUploading(true);
    setUploadError('');
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const content = e.target?.result as string;
        const response = await fetch('/api/v1/knowledge/mcp', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            content: content,
          }),
        });
        const data = await response.json();
        if (data.status === 0) {
          setUploadDialogOpen(false);
          toast.success(t('knowledgeBase.createMCPSuccess'), {
            description: t('knowledgeBase.MCPSuccessfullyUploaded'),
          });
          fetchMCPs(1, 10, searchTerm);
        } else {
          setUploadError(data.message || t('knowledgeBase.uploadFailed'));
          toast.error(t('knowledgeBase.createMCPFailed'), {
            description: data.message || t('knowledgeBase.uploadFailed'),
          });
        }
        setUploading(false);
      };
      reader.readAsText(file);
    } catch (error) {
      setUploadError(t('knowledgeBase.fileReadOrUploadFailed'));
      toast.error(t('knowledgeBase.createMCPFailed'), {
        description: t('knowledgeBase.fileReadOrUploadFailed'),
      });
      setUploading(false);
    }
  };

  // Download the sample yaml
  const downloadSampleYaml = () => {
    const sample = `info:
  id: "auth_bypass"
  name: "Authentication Bypass Detection"
  description: "Detect possible authentication bypass vulnerabilities in MCP code"
  author: "Zhuque Security Team"
  category:
    - "code"
prompt_template: |
  As a professional cybersecurity analyst, you need to precisely detect authentication bypass vulnerabilities in MCP code. This detection requires extremely high accuracy - only report when you find concrete evidence of authentication bypass risks.

  ## Vulnerability Definition
  Authentication bypass refers to an attacker's ability to gain unauthorized access by circumventing the system's authentication mechanisms without providing valid credentials.

  ## Detection Criteria (Must meet at least one):
  1. **Missing Authentication**: No authentication checks on sensitive endpoints
  2. **Weak Authentication**: Easily bypassable authentication mechanisms
  3. **Inconsistent Authentication**: Some endpoints protected while others are not
  4. **Hardcoded Credentials**: Credentials embedded in code
  5. **Predictable Session Tokens**: Weak session management

  ## Analysis Instructions:
  1. Examine the MCP code structure and identify authentication mechanisms
  2. Look for endpoints that handle sensitive operations
  3. Check if authentication is consistently applied
  4. Identify any hardcoded credentials or weak session management
  5. Report specific code locations and explain the vulnerability

  ## Output Format:
  - **Vulnerability Found**: Yes/No
  - **Type**: [Specific bypass type]
  - **Location**: [File/line numbers]
  - **Description**: [Detailed explanation]
  - **Risk Level**: High/Medium/Low
  - **Recommendation**: [How to fix]`;
    const blob = new Blob([sample], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample-mcp.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Open the edit dialog
  const handleEditMCP = (mcp: MCPType) => {
    setEditTarget(mcp);
    try {
      // Exclude the RawData field and only keep info and prompt_template
      const { RawData, ...mcpWithoutRawData } = mcp;
      setEditYamlContent(yaml.dump(mcpWithoutRawData));
    } catch (e) {
      setEditYamlContent('');
    }
    setEditDialogOpen(true);
    setEditError('');
  };

  // Download the current MCP data
  const handleDownloadCurrentMCP = () => {
    if (!editTarget || !editYamlContent.trim()) {
      toast.error(t('knowledgeBase.mcpTab.noDataToDownload'));
      return;
    }

    try {
      const blob = new Blob([editYamlContent], { type: 'text/yaml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${editTarget.info?.id || 'mcp'}.yaml`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(t('knowledgeBase.mcpTab.currentMCPDataDownloadSuccess'));
    } catch (error) {
      toast.error(t('knowledgeBase.mcpTab.downloadFailed'));
    }
  };

  // Handle file uploads during editing
  const handleEditFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.yaml') && !file.name.endsWith('.yml')) {
      toast.error(t('knowledgeBase.mcpTab.pleaseSelectYamlFile'));
      return;
    }

    try {
      const content = await file.text();
      setEditYamlContent(content);
    } catch (error) {
      toast.error(t('knowledgeBase.mcpTab.fileReadFailed'));
    }
    if (editFileInputRef.current) {
      editFileInputRef.current.value = '';
    }
  };

  // Save the edits
  const handleSaveEdit = async () => {
    if (!editTarget?.info?.id) {
      setEditError(t('knowledgeBase.mcpTab.mcpIdMissing'));
      toast.error(t('knowledgeBase.editMCPFailed'), {
        description: t('knowledgeBase.mcpTab.mcpIdMissing'),
      });
      return;
    }
    setEditLoading(true);
    setEditError('');
    try {
      const response = await fetch(`/api/v1/knowledge/mcp/${editTarget.info.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: editYamlContent,
        }),
      });
      const data = await response.json();
      if (data.status === 0) {
        setEditDialogOpen(false);
        toast.success(t('knowledgeBase.editMCPSuccess'), {
          description: t('knowledgeBase.MCPSuccessfullyUpdated'),
        });
        fetchMCPs(1, 10, searchTerm);
      } else {
        setEditError(data.message || t('knowledgeBase.mcpTab.saveFailed'));
        toast.error(t('knowledgeBase.editMCPFailed'), {
          description: data.message || t('knowledgeBase.mcpTab.saveFailed'),
        });
      }
    } catch (error) {
      setEditError(t('knowledgeBase.mcpTab.saveFailed'));
      toast.error(t('knowledgeBase.editMCPFailed'), {
        description: t('knowledgeBase.mcpTab.saveFailed'),
      });
    }
    setEditLoading(false);
  };

  // Delete the MCP
  const deleteMCP = async (id: string) => {
    try {
      const response = await fetch(`/api/v1/knowledge/mcp/${id}`, {
        method: 'DELETE',
      });
      const data = await response.json();
      if (data.status === 0) {
        toast.success(t('knowledgeBase.mcpTab.deleteMCPSuccess'), {
          description: t('knowledgeBase.MCPSuccessfullyUpdated'),
        });
        fetchMCPs(currentPage, 10, searchTerm);
      } else {
        setDeleteError(data.message || t('knowledgeBase.mcpTab.deleteMCPFailed'));
        toast.error(t('knowledgeBase.mcpTab.deleteMCPFailed'), {
          description: data.message || t('knowledgeBase.mcpTab.deleteMCPFailed'),
        });
      }
    } catch (error) {
      setDeleteError(t('knowledgeBase.mcpTab.deleteMCPFailed'));
      toast.error(t('knowledgeBase.mcpTab.deleteMCPFailed'), {
        description: t('knowledgeBase.mcpTab.deleteMCPFailed'),
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
      await deleteMCP(deleteTarget);
      setDeleteDialogOpen(false);
    } catch (e) {
      setDeleteError(t('knowledgeBase.mcpTab.deleteFailed'));
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
              placeholder={t('knowledgeBase.mcpTab.searchPlaceholder')}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  setCurrentPage(1);
                  fetchMCPs(1, 10, searchTerm);
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
                  fetchMCPs(1, 10, '');
                }}
                tabIndex={-1}
              >
                <XCircle className='w-4 h-4' />
              </button>
            )}
          </div>
          <Button onClick={() => {
            setCurrentPage(1);
            fetchMCPs(1, 10, searchTerm);
          }}>
            {t('knowledgeBase.mcpTab.search')}
          </Button>
          <Button className='gap-0' variant='outline' onClick={() => setUploadDialogOpen(true)}>
            <Plus className='w-4 h-4' />
            {t('knowledgeBase.mcpTab.createMCPConfig')}
          </Button>
        </div>
      </div>
      <div className='flex-1 min-h-0 flex flex-col'>
        <ScrollArea className='flex-1 min-h-0'>
          {loading ? (
            <div className='flex items-center justify-center py-8'>
              <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
            </div>
          ) : mcps.length === 0 ? (
            <div className='text-center py-8 text-gray-500'>
              <Code className='w-12 h-12 mx-auto mb-4 opacity-50' />
              <p>{t('knowledgeBase.mcpTab.noMCPData')}</p>
            </div>
          ) : (
            <div className='space-y-3'>
              {mcps.map((mcp, index) => (
                <div key={index} className='border rounded-lg p-4 bg-white'>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center gap-3'>
                      <h3 className='font-semibold text-gray-900'>
                        {mcp.info?.name || t('knowledgeBase.mcpTab.unknown')}
                      </h3>
                      <Badge className='bg-blue-100 text-blue-800 hover:bg-blue-100 hover:text-blue-800'>
                        {mcp.info?.id || 'unknown'}
                      </Badge>
                    </div>
                    <div className='flex items-center gap-2'>
                      <Button className='px-2' size='sm' variant='outline' onClick={() => handleEditMCP(mcp)}>
                        <Edit className='w-4 h-4' />
                      </Button>
                      <Button
                        size='sm'
                        variant='outline'
                        className='text-red-600 hover:bg-red-50 hover:text-red-700 px-2'
                        onClick={() => handleDeleteClick(mcp.info?.id || '')}
                      >
                        <Trash2 className='w-4 h-4' />
                      </Button>
                    </div>
                  </div>
                  <p className='text-sm text-gray-600 my-4'>
                    {mcp.info?.description || t('knowledgeBase.mcpTab.noDescription')}
                  </p>
                  <div className='flex items-center gap-4 text-xs text-gray-500'>
                    <span>{t('knowledgeBase.mcpTab.contributor')}: <span className='text-blue-600 font-bold'>{mcp.info?.author || t('knowledgeBase.mcpTab.unknown')}</span></span>
                    <span>{t('knowledgeBase.mcpTab.category')}: {mcp.info?.category?.join(', ') || t('knowledgeBase.mcpTab.unknown')}</span>
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
            fetchMCPs(page, 10, searchTerm);
          }}
        />
      </div>
      {/* Upload MCP dialog */}
      <YamlUploadDialog
        open={uploadDialogOpen}
        onClose={(open) => {
          setUploadDialogOpen(open);
          if (!open) setUploadError('');
        }}
        onUpload={handleUploadMCP}
        loading={uploading}
        error={uploadError}
        onDownloadSample={downloadSampleYaml}
        title={t('knowledgeBase.mcpTab.uploadMCPYamlTitle')}
        type='mcp'
      />
      {/* Edit MCP dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className='max-w-4xl h-[80vh] max-h-[90vh] flex flex-col'>
          <DialogHeader>
            <DialogTitle>{t('knowledgeBase.mcpTab.editMCPTitle', { name: editTarget?.info?.name })}</DialogTitle>
          </DialogHeader>
          <div className='flex-1 flex flex-col min-h-0 space-y-4'>
            <div className='flex-1 min-h-0'>
              <textarea
                value={editYamlContent}
                onChange={e => setEditYamlContent(e.target.value)}
                placeholder={t('knowledgeBase.mcpTab.editMCPPlaceholder')}
                className='w-full h-full p-3 border rounded-md font-mono text-sm resize-none outline-none'
                style={{ minHeight: '300px' }}
              />
            </div>
            {editError && <div className='text-red-500 text-sm'>{editError}</div>}
            <div className='flex justify-between items-center gap-2'>
              <div className='flex gap-2'>
                <Button onClick={handleDownloadCurrentMCP} variant='outline' size='sm' className='gap-1'>
                  <Download className='w-4 h-4' />
                  {t('knowledgeBase.mcpTab.downloadCurrentData')}
                </Button>
                <div className='relative'>
                  <input
                    ref={editFileInputRef}
                    type='file'
                    accept='.yaml,.yml'
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
                    {t('knowledgeBase.mcpTab.uploadYamlFile')}
                  </Button>
                </div>
              </div>
              <div className='flex gap-2'>
                <Button variant='outline' onClick={() => setEditDialogOpen(false)}>
                  {t('common.cancel')}
                </Button>
                <Button onClick={handleSaveEdit} disabled={editLoading || !editYamlContent.trim()}>
                  {editLoading ? t('knowledgeBase.mcpTab.saving') : t('knowledgeBase.mcpTab.save')}
                </Button>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className='max-w-sm'>
          <DialogHeader>
            <DialogTitle>{t('knowledgeBase.mcpTab.confirmDeleteTitle')}</DialogTitle>
          </DialogHeader>
          <div className='py-4'>
            <div className='text-base text-gray-800 pb-4'>
              {t('knowledgeBase.mcpTab.confirmDeleteMessage', { target: deleteTarget })}
            </div>
            {deleteError && <div className='text-red-500 text-sm'>{deleteError}</div>}
            <div className='flex gap-2 mt-4'>
              <Button onClick={handleConfirmDelete} disabled={deleteLoading}>
                {t('common.confirm')}
              </Button>
              <Button
                variant='outline'
                onClick={() => setDeleteDialogOpen(false)}
                disabled={deleteLoading}
              >
                {t('common.cancel')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default MCPTabContent; 