import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import { 
  Blocks, 
  Bug, 
  Shield, 
  Plus, 
  Edit, 
  Trash2, 
  Search,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Fingerprint,
  Minimize,
  Maximize,
  BookOpen,
  Code,
} from 'lucide-react';
import yaml from 'js-yaml';
import { toast } from 'sonner';
import YamlUploadDialog from './YamlUploadDialog';
import YamlEditDialog from './YamlEditDialog';
import FingerprintTabContent from './FingerprintTabContent';
import VulnerabilityTabContent from './VulnerabilityTabContent';
import EvaluationTabContent from './EvaluationTabContent';
import MCPTabContent from './MCPTabContent';

interface Fingerprint {
  info: {
    name: string;
    author: string;
    example: string[];
    desc: string;
    severity: string;
    metadata: {
      product: string;
      vendor: string;
    };
  };
  http: Array<{
    method: string;
    path: string;
    matchers: string[];
  }>;
}

interface Vulnerability {
  info: {
    name: string;
    cve: string;
    summary: string;
    details: string;
    cvss: string;
    severity: string;
    security_advice: string;
    references: string[];
  };
  rule: string;
  references: string[];
}

interface MCP {
  info: {
    id: string;
    name: string;
    description: string;
    author: string;
    category: string[];
  };
  prompt_template: string;
  RawData: string;
}

interface KnowledgeBaseSettingsProps {
  initialTab?: string;
}

export interface KnowledgeBaseSettingsRef {
  refreshAll: () => void;
}

const KnowledgeBaseSettings = forwardRef<KnowledgeBaseSettingsRef, KnowledgeBaseSettingsProps>(({ initialTab = 'evaluations' }, ref) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState(initialTab);
  const [fingerprints, setFingerprints] = useState<Fingerprint[]>([]);
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [evaluations, setEvaluations] = useState([]);
  const [mcps, setMcps] = useState<MCP[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editYamlContent, setEditYamlContent] = useState('');
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState('');
  const [editTarget, setEditTarget] = useState<Fingerprint | null>(null);
  const [editVulDialogOpen, setEditVulDialogOpen] = useState(false);
  const [editVulYamlContent, setEditVulYamlContent] = useState('');
  const [editVulLoading, setEditVulLoading] = useState(false);
  const [editVulError, setEditVulError] = useState('');
  const [editVulTarget, setEditVulTarget] = useState<Vulnerability | null>(null);
  const [uploadVulDialogOpen, setUploadVulDialogOpen] = useState(false);
  const [uploadVulLoading, setUploadVulLoading] = useState(false);
  const [uploadVulError, setUploadVulError] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteType, setDeleteType] = useState<'fingerprint' | 'vul' | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string>('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [isEditFullscreen, setIsEditFullscreen] = useState(false);
  const [isEditVulFullscreen, setIsEditVulFullscreen] = useState(false);

  // Expose the refresh method to the parent component (used by the SettingsDialog 'Update data' button)
  // Note: evaluations / fingerprints / vulnerabilities share the same pagination state (total, totalPages);
  // concurrent refreshes would overwrite each other's pagination data. Therefore only refresh the list of the current activeTab here;
  // data for other tabs will be re-fetched automatically via the useEffect below when switching to that tab,
  // which also picks up the latest data synced by the update API.
  useImperativeHandle(ref, () => ({
    refreshAll: () => {
      if (activeTab === 'evaluations') {
        fetchEvaluations(currentPage, 10, searchTerm);
      } else if (activeTab === 'fingerprints') {
        fetchFingerprints(currentPage, 10, searchTerm);
      } else if (activeTab === 'vulnerabilities') {
        fetchVulnerabilities(currentPage, 10, searchTerm);
      } else if (activeTab === 'mcps') {
        fetchMCPs(currentPage, 10, searchTerm);
      }
    },
  }), [activeTab, currentPage, searchTerm]);

  // Fetch the fingerprint list
  const fetchFingerprints = async (page = 1, size = 10, q = '') => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        size: size.toString(),
        ...(q && { q }),
      });
      const response = await fetch(`/api/v1/knowledge/fingerprints?${params}`);
      const data = await response.json();
      if (data.status === 0) {
        setFingerprints(data.data.items || []);
        setTotalPages(Math.ceil(data.data.total / 10));
        setTotal(data.data.total || 0);
      } else {
        toast.error(t('knowledgeBase.getFingerprintListFailed'), {
          description: data.message || t('knowledgeBase.getFingerprintListFailed'),
        });
      }
    } catch (error) {
      toast.error(t('knowledgeBase.getFingerprintListFailed'), {
        description: t('knowledgeBase.getFingerprintListFailed'),
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch the vulnerability list
  const fetchVulnerabilities = async (page = 1, size = 10, q = '') => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        size: size.toString(),
        ...(q && { q }),
      });
      const response = await fetch(`/api/v1/knowledge/vulnerabilities?${params}`);
      const data = await response.json();
      if (data.status === 0) {
        setVulnerabilities(data.data.items || []);
        setTotalPages(Math.ceil(data.data.total / size));
        setTotal(data.data.total || 0);
      } else {
        toast.error(t('knowledgeBase.getVulnerabilityLibraryFailed'), {
          description: data.message || t('knowledgeBase.getVulnerabilityLibraryFailed'),
        });
      }
    } catch (error) {
      toast.error(t('knowledgeBase.getVulnerabilityLibraryFailed'), {
        description: t('knowledgeBase.getVulnerabilityLibraryFailed'),
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch the evaluation-set list
  const fetchEvaluations = async (page = 1, size = 10, q = '') => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        size: size.toString(),
        ...(q && { q }),
      });
      const response = await fetch(`/api/v1/knowledge/evaluations?${params}`);
      const data = await response.json();
      if (data.status === 0) {
        setEvaluations(data.data.items || []);
        setTotalPages(Math.ceil(data.data.total / size));
        setTotal(data.data.total || 0);
      } else {
        toast.error(t('knowledgeBase.getEvaluationSetFailed'), {
          description: data.message || t('knowledgeBase.getEvaluationSetFailed'),
        });
      }
    } catch (error) {
      toast.error(t('knowledgeBase.getEvaluationSetFailed'), {
        description: t('knowledgeBase.getEvaluationSetFailed'),
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch the MCP config list
  const fetchMCPs = async (page = 1, size = 10, q = '') => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        size: size.toString(),
        ...(q && { q }),
      });
      const response = await fetch(`/api/v1/knowledge/mcp?${params}`);
      const data = await response.json();
      if (data.status === 0) {
        setMcps(data.data.items || []);
        setTotalPages(Math.ceil(data.data.total / size));
        setTotal(data.data.total || 0);
      } else {
        toast.error(t('knowledgeBase.getMCPConfigFailed'), {
          description: data.message || t('knowledgeBase.getMCPConfigFailed'),
        });
      }
    } catch (error) {
      toast.error(t('knowledgeBase.getMCPConfigFailed'), {
        description: t('knowledgeBase.getMCPConfigFailed'),
      });
    } finally {
      setLoading(false);
    }
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

  // Delete the vulnerability
  const deleteVulnerabilities = async (cves: string[]) => {
    try {
      const response = await fetch('/api/v1/knowledge/vulnerabilities', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ cves }),
      });
      const data = await response.json();
      if (data.status === 0) {
        toast.success(t('knowledgeBase.deleteVulnerabilitySuccess'), {
          description: t('knowledgeBase.vulnerabilitySuccessfullyDeleted'),
        });
        fetchVulnerabilities(currentPage, 10, searchTerm);
      } else {
        setDeleteError(data.message || t('knowledgeBase.deleteVulnerabilityFailed'));
        toast.error(t('knowledgeBase.deleteVulnerabilityFailed'), {
          description: data.message || t('knowledgeBase.deleteVulnerabilityFailed'),
        });
      }
    } catch (error) {
      setDeleteError(t('knowledgeBase.deleteVulnerabilityFailed'));
      toast.error(t('knowledgeBase.deleteVulnerabilityFailed'), {
        description: t('knowledgeBase.deleteVulnerabilityFailed'),
      });
    }
  };

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
  author: 腾讯朱雀实验室
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
      regex: 'x-version:\s*(\d+\.\d+\.?\d+?)'
`;
    const blob = new Blob([sample], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample-fingerprint.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Open the edit dialog
  const handleEditFingerprint = (fingerprint: Fingerprint) => {
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
        setEditError(data.message || t('knowledgeBase.uploadFailed'));
        toast.error(t('knowledgeBase.editFingerprintFailed'), {
          description: data.message || t('knowledgeBase.uploadFailed'),
        });
      }
    } catch (error) {
      setEditError(t('knowledgeBase.uploadFailed'));
      toast.error(t('knowledgeBase.editFingerprintFailed'), {
        description: t('knowledgeBase.uploadFailed'),
      });
    }
    setEditLoading(false);
  };

  // Open the edit-vulnerability dialog
  const handleEditVulnerability = (vul: Vulnerability) => {
    setEditVulTarget(vul);
    try {
      setEditVulYamlContent(yaml.dump(vul));
    } catch (e) {
      setEditVulYamlContent('');
    }
    setEditVulDialogOpen(true);
    setEditVulError('');
  };

  // Save the vulnerability edits
  const handleSaveEditVul = async () => {
    if (!editVulTarget?.info?.cve) {
      setEditVulError(t('knowledgeBase.fingerprintNameMissing'));
      toast.error(t('knowledgeBase.editVulnerabilityFailed'), {
        description: t('knowledgeBase.fingerprintNameMissing'),
      });
      return;
    }
    setEditVulLoading(true);
    setEditVulError('');
    try {
      const response = await fetch(`/api/v1/knowledge/vulnerabilities/${editVulTarget.info.cve}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_content: editVulYamlContent,
        }),
      });
      const data = await response.json();
      if (data.status === 0) {
        setEditVulDialogOpen(false);
        toast.success(t('knowledgeBase.editVulnerabilitySuccess'), {
          description: t('knowledgeBase.vulnerabilitySuccessfullyUpdated'),
        });
        fetchVulnerabilities(1, 10, searchTerm);
      } else {
        setEditVulError(data.message || t('knowledgeBase.uploadFailed'));
        toast.error(t('knowledgeBase.editVulnerabilityFailed'), {
          description: data.message || t('knowledgeBase.uploadFailed'),
        });
      }
    } catch (error) {
      setEditVulError(t('knowledgeBase.uploadFailed'));
      toast.error(t('knowledgeBase.editVulnerabilityFailed'), {
        description: t('knowledgeBase.uploadFailed'),
      });
    }
    setEditVulLoading(false);
  };

  // Upload the vulnerability yaml
  const handleUploadVul = async (file: File) => {
    setUploadVulLoading(true);
    setUploadVulError('');
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const content = e.target?.result as string;
        const response = await fetch('/api/v1/knowledge/vulnerabilities', {
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
          setUploadVulDialogOpen(false);
          toast.success(t('knowledgeBase.createVulnerabilitySuccess'), {
            description: t('knowledgeBase.vulnerabilitySuccessfullyUploaded'),
          });
          fetchVulnerabilities(1, 10, searchTerm);
        } else {
          setUploadVulError(data.message || t('knowledgeBase.uploadFailed'));
          toast.error(t('knowledgeBase.createVulnerabilityFailed'), {
            description: data.message || t('knowledgeBase.uploadFailed'),
          });
        }
        setUploadVulLoading(false);
      };
      reader.readAsText(file);
    } catch (error) {
      setUploadVulError(t('knowledgeBase.fileReadOrUploadFailed'));
      toast.error(t('knowledgeBase.createVulnerabilityFailed'), {
        description: t('knowledgeBase.fileReadOrUploadFailed'),
      });
      setUploadVulLoading(false);
    }
  };

  // Download the sample vulnerability yaml
  const downloadSampleVulYaml = () => {
    const sample = `info:
  name: anyalgorithm
  cve: CVE-2024-12345
  summary: Gradio XX版本存在XX漏洞
  details: 详细描述内容
  cvss: "8.5"
  severity: HIGH
  security_advice: 建议升级到3.50.3版本
  references:
    - https://github.com/gradio-app/gradio/security/advisories/1234
rule: version <= "3.50.2"
references:
  - https://nvd.nist.gov/vuln/detail/CVE-2024-12345
`;
    const blob = new Blob([sample], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample-vulnerability.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Trigger the delete dialog
  const handleDeleteClick = (type: 'fingerprint' | 'vul', target: string) => {
    setDeleteType(type);
    setDeleteTarget(target);
    setDeleteDialogOpen(true);
    setDeleteError('');
  };

  // Confirm deletion
  const handleConfirmDelete = async () => {
    setDeleteLoading(true);
    setDeleteError('');
    try {
      if (deleteType === 'fingerprint') {
        await deleteFingerprints([deleteTarget]);
      } else if (deleteType === 'vul') {
        await deleteVulnerabilities([deleteTarget]);
      }
      setDeleteDialogOpen(false);
    } catch (e) {
      setDeleteError(t('knowledgeBase.deleteFingerprintFailed'));
    }
    setDeleteLoading(false);
  };

  useEffect(() => {
    setCurrentPage(1);
    if (activeTab === 'fingerprints') {
      fetchFingerprints(1, 10, '');
    } else if (activeTab === 'vulnerabilities') {
      fetchVulnerabilities(1, 10, '');
    } else if (activeTab === 'evaluations') {
      fetchEvaluations(1, 10, '');
    } else if (activeTab === 'mcps') {
      fetchMCPs(1, 10, '');
    }
  }, [activeTab]);

  return (
    <div className="w-full h-full flex flex-col relative p-4">
      <Tabs value={activeTab} onValueChange={(tab) => {
        setActiveTab(tab);
        setSearchTerm('');
      }} className="w-full flex-1 min-h-0 flex flex-col">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="evaluations" className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            {t('knowledgeBase.jailbreakEvaluationSet')}
          </TabsTrigger>
          <TabsTrigger value="fingerprints" className="flex items-center gap-2">
            <Fingerprint className="w-4 h-4" />
            {t('knowledgeBase.aiAppFingerprint')}
          </TabsTrigger>
          <TabsTrigger value="vulnerabilities" className="flex items-center gap-2">
            <Bug className="w-4 h-4" />
            {t('knowledgeBase.vulnerabilityLibrary')}
          </TabsTrigger>
          <TabsTrigger value="mcps" className="flex items-center gap-2">
            <Code className="w-4 h-4" />
            {t('knowledgeBase.mcpPlugin')}
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="fingerprints"
          className={activeTab === 'fingerprints'
            ? 'flex-1 min-h-0 flex flex-col mt-4'
            : 'hidden'}
        >
          <FingerprintTabContent
            fingerprints={fingerprints}
            loading={loading}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            currentPage={currentPage}
            totalPages={totalPages}
            total={total}
            setCurrentPage={setCurrentPage}
            fetchFingerprints={fetchFingerprints}
          />
        </TabsContent>

        <TabsContent
          value="vulnerabilities"
          className={activeTab === 'vulnerabilities'
            ? 'flex-1 min-h-0 flex flex-col mt-4'
            : 'hidden'}
        >
          <VulnerabilityTabContent
            vulnerabilities={vulnerabilities}
            loading={loading}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            currentPage={currentPage}
            totalPages={totalPages}
            total={total}
            setCurrentPage={setCurrentPage}
            fetchVulnerabilities={fetchVulnerabilities}
          />
        </TabsContent>

        <TabsContent
          value="evaluations"
          className={activeTab === 'evaluations'
            ? 'flex-1 min-h-0 flex flex-col mt-4'
            : 'hidden'}
        >
          <EvaluationTabContent
            evaluations={evaluations}
            loading={loading}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            currentPage={currentPage}
            totalPages={totalPages}
            total={total}
            setCurrentPage={setCurrentPage}
            fetchEvaluations={fetchEvaluations}
          />
        </TabsContent>

        <TabsContent
          value="mcps"
          className={activeTab === 'mcps'
            ? 'flex-1 min-h-0 flex flex-col mt-4'
            : 'hidden'}
        >
          <MCPTabContent
            mcps={mcps}
            loading={loading}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            currentPage={currentPage}
            totalPages={totalPages}
            total={total}
            setCurrentPage={setCurrentPage}
            fetchMCPs={fetchMCPs}
          />
        </TabsContent>
      </Tabs>

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
      {/* Edit vulnerability-library dialog */}
      <YamlEditDialog
        open={editVulDialogOpen}
        onClose={setEditVulDialogOpen}
        onSave={handleSaveEditVul}
        loading={editVulLoading}
        error={editVulError}
        yamlContent={editVulYamlContent}
        onYamlChange={setEditVulYamlContent}
        isFullscreen={isEditVulFullscreen}
        onToggleFullscreen={() => setIsEditVulFullscreen(!isEditVulFullscreen)}
        title={t('knowledgeBase.editVulnerabilityYaml')}
      />
      {/* Upload vulnerability-library dialog */}
      <YamlUploadDialog
        open={uploadVulDialogOpen}
        onClose={(open) => {
          setUploadVulDialogOpen(open);
          if (!open) setUploadVulError('');
        }}
        onUpload={handleUploadVul}
        loading={uploadVulLoading}
        error={uploadVulError}
        onDownloadSample={downloadSampleVulYaml}
        title={t('knowledgeBase.uploadVulnerabilityYaml')}
      />

      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className='max-w-sm'>
          <DialogHeader>
            <DialogTitle>{t('knowledgeBase.confirmDelete')}</DialogTitle>
          </DialogHeader>
          <div className='py-4'>
            <div className='text-base text-gray-800 pb-4'>
              {t('knowledgeBase.confirmDeleteMessage', {
                type: deleteType === 'fingerprint' ? t('knowledgeBase.fingerprint') : t('knowledgeBase.vulnerability'),
                target: deleteTarget
              })}
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
    </div>
  );
});

KnowledgeBaseSettings.displayName = 'KnowledgeBaseSettings';

export default KnowledgeBaseSettings; 