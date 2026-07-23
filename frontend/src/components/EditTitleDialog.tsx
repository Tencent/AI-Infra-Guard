import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from './ui/dialog';
import { Input } from './ui/input';
import { Button } from './ui/button';

interface EditTitleDialogProps {
  open: boolean;
  defaultValue: string;
  loading?: boolean;
  error?: string;
  onConfirm: (title: string) => void;
  onCancel: () => void;
}

const EditTitleDialog: React.FC<EditTitleDialogProps> = ({
  open,
  defaultValue,
  loading = false,
  error,
  onConfirm,
  onCancel,
}) => {
  const [title, setTitle] = useState(defaultValue);

  React.useEffect(() => {
    setTitle(defaultValue);
  }, [defaultValue, open]);

  return (
    <Dialog open={open} onOpenChange={v => !v && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>编辑标题</DialogTitle>
          <DialogDescription>请输入新标题</DialogDescription>
        </DialogHeader>
        <Input
          value={title}
          onChange={e => setTitle(e.target.value)}
          disabled={loading}
          autoFocus
          className='mb-2'
          maxLength={60}
        />
        {error && <div className='text-red-500 text-xs mb-2'>{error}</div>}
        <DialogFooter>
          <Button
            variant='outline'
            onClick={onCancel}
            disabled={loading}
          >
            取消
          </Button>
          <Button
            onClick={() => onConfirm(title)}
            disabled={loading || !title.trim()}
          >
            {loading ? '保存中...' : '确认'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default EditTitleDialog; 