import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { X, Plus, Trash2 } from 'lucide-react';
import ReactDOM from 'react-dom';

interface HttpHeader {
  key: string;
  value: string;
}

interface HttpHeaderDialogProps {
  open: boolean;
  headers: HttpHeader[];
  onConfirm: (headers: HttpHeader[]) => void;
  onCancel: () => void;
}

const HttpHeaderDialog: React.FC<HttpHeaderDialogProps> = ({
  open,
  headers,
  onConfirm,
  onCancel,
}) => {
  const { t } = useTranslation();
  const [localHeaders, setLocalHeaders] = useState<HttpHeader[]>([]);

  useEffect(() => {
    if (open) {
      setLocalHeaders([...headers]);
    }
  }, [open, headers]);

  const addHeader = () => {
    setLocalHeaders([...localHeaders, { key: '', value: '' }]);
  };

  const removeHeader = (index: number) => {
    setLocalHeaders(localHeaders.filter((_, i) => i !== index));
  };

  const updateHeader = (index: number, field: 'key' | 'value', value: string) => {
    const newHeaders = [...localHeaders];
    newHeaders[index] = { ...newHeaders[index], [field]: value };
    setLocalHeaders(newHeaders);
  };

  const handleConfirm = () => {
    // Filter out headers whose key is empty; value may be empty
    const validHeaders = localHeaders.filter(header => header.key.trim());
    onConfirm(validHeaders);
    onCancel();
  };

  if (!open) return null;

  const dialog = (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-1/2">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">{t('httpHeaderDialog.title')}</h3>
          <Button
            size="sm"
            variant="ghost"
            onClick={onCancel}
            className="p-1 h-8 w-8"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        
        <div className="space-y-3 mb-4">
          {localHeaders.map((header, index) => (
            <div key={index} className="flex items-center space-x-2">
              <Input
                placeholder={t('httpHeaderDialog.headerName')}
                value={header.key}
                onChange={(e) => updateHeader(index, 'key', e.target.value)}
                className="flex-1"
              />
              <Input
                placeholder={t('httpHeaderDialog.headerValue')}
                value={header.value}
                onChange={(e) => updateHeader(index, 'value', e.target.value)}
                className="flex-1"
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeHeader(index)}
                className="p-1 h-8 w-8 text-red-500 hover:text-red-700"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
        
        <Button
          onClick={addHeader}
          variant="outline"
          className="w-full mb-4"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t('httpHeaderDialog.addHeader')}
        </Button>
        
        <div className="flex space-x-2">
          <Button
            onClick={handleConfirm}
            className="flex-1 bg-blue-600 hover:bg-blue-700"
          >
            {t('common.confirm')}
          </Button>
          <Button
            onClick={onCancel}
            variant="outline"
            className="flex-1"
          >
            {t('common.cancel')}
          </Button>
        </div>
      </div>
    </div>
  );

  return ReactDOM.createPortal(dialog, document.body);
};

export default HttpHeaderDialog; 