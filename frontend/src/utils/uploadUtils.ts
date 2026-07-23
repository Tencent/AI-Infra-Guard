import { v4 as uuidv4 } from 'uuid';

const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
const LARGE_FILE_THRESHOLD = 50 * 1024 * 1024; // 50MB

interface UploadResult {
  status: number;
  data: {
    filename: string;
    fileUrl: string;
  };
  message?: string;
}

export const uploadFile = async (
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResult> => {
  if (file.size <= LARGE_FILE_THRESHOLD) {
    return uploadSimple(file, onProgress);
  } else {
    return uploadChunked(file, onProgress);
  }
};

const uploadSimple = async (
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResult> => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const xhr = new XMLHttpRequest();
    const promise = new Promise<UploadResult>((resolve, reject) => {
      xhr.open('POST', '/api/v1/app/tasks/uploadFile');
      
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percentComplete = (event.loaded / event.total) * 100;
          onProgress(percentComplete);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const result = JSON.parse(xhr.responseText);
            resolve(result);
          } catch (e) {
            reject(new Error('Invalid JSON response'));
          }
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      };

      xhr.onerror = () => reject(new Error('Network error'));
      
      xhr.send(formData);
    });

    return await promise;
  } catch (error) {
    console.error('Simple upload failed:', error);
    throw error;
  }
};

const uploadChunked = async (
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResult> => {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  const uploadId = uuidv4();
  const fileName = file.name;
  let fileUrl = '';

  for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
    const start = chunkIndex * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);

    const formData = new FormData();
    formData.append('file', chunk);
    formData.append('uploadId', uploadId);
    formData.append('chunkIndex', chunkIndex.toString());
    formData.append('totalChunks', totalChunks.toString());
    formData.append('fileName', fileName);

    try {
      const response = await fetch('/api/v1/app/tasks/uploadChunk', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Chunk ${chunkIndex} upload failed`);
      }

      const result = await response.json();
      if (result.status !== 0) {
        throw new Error(result.message || 'Chunk upload failed');
      }

      // If it's the last chunk, the server should return the final file info
      if (chunkIndex === totalChunks - 1) {
        fileUrl = result.data.fileUrl;
      }

      if (onProgress) {
        const percentComplete = ((chunkIndex + 1) / totalChunks) * 100;
        onProgress(percentComplete);
      }
    } catch (error) {
      console.error('Chunk upload failed:', error);
      throw error;
    }
  }

  return {
    status: 0,
    data: {
      filename: fileName,
      fileUrl: fileUrl,
    },
  };
};


