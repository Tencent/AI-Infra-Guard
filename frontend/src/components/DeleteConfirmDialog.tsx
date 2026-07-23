import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { AlertTriangle } from 'lucide-react';

interface DeleteConfirmDialogProps {
  open: boolean;
  loading: boolean;
  error?: string;
  onConfirm: () => void;
  onCancel: () => void;
  title?: string;
  description?: string;
  confirmText?: string;
  loadingText?: string;
  cancelText?: string;
}

const DeleteConfirmDialog: React.FC<DeleteConfirmDialogProps> = ({
  open,
  loading,
  error,
  onConfirm,
  onCancel,
  title,
  description,
  confirmText,
  loadingText,
  cancelText,
}) => {
  const { t } = useTranslation();
  const resolvedTitle = title || t('taskDelete.confirmTitle');
  const resolvedDescription = description || t('taskDelete.confirmDescription');
  return (
    <Dialog open={open} onOpenChange={onCancel}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <span>{resolvedTitle}</span>
          </DialogTitle>
          <DialogDescription className="text-gray-600">
            {resolvedDescription}
          </DialogDescription>
        </DialogHeader>
        
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
        
        <DialogFooter>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading
              ? (loadingText || t('taskDelete.deleting'))
              : (confirmText || t('taskDelete.confirm'))}
          </Button>
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelText || t('taskDelete.cancel')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DeleteConfirmDialog; 