import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

export interface DownloadPdfOptions {
  container: HTMLElement;
  isFullscreen: boolean;
  onToggleFullscreen?: () => void;
  filename: string;
}

export async function downloadPanelPdf(options: DownloadPdfOptions): Promise<void> {
  const { container, isFullscreen, onToggleFullscreen, filename } = options;
  if (!container) return;
  let toggledFullscreen = false;
  if (!isFullscreen && onToggleFullscreen) {
    try {
      onToggleFullscreen();
      toggledFullscreen = true;
      await new Promise(resolve => setTimeout(resolve, 250));
    } catch {}
  }
  try {
    const prev = {
      overflow: container.style.overflow,
      height: container.style.height,
      maxHeight: container.style.maxHeight,
      marginLeft: container.style.marginLeft,
      marginRight: container.style.marginRight,
    };
    const exportStyle = document.createElement('style');
    exportStyle.setAttribute('data-aig-export-style', 'true');
    exportStyle.textContent = `
      .aig-export-root, .aig-export-root * { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility; }
      .aig-export-root > *:first-child { margin-top: 0 !important; }
      .aig-export-root { line-height: 1; }
    `;
    document.head.appendChild(exportStyle);
    container.style.overflow = 'visible';
    container.style.height = 'auto';
    container.style.maxHeight = 'none';
    container.style.marginLeft = 'auto';
    container.style.marginRight = 'auto';
    container.classList.add('aig-export-root');
    const width = container.scrollWidth;
    const height = container.scrollHeight;
    const scale = Math.min(1.5, Math.ceil(window.devicePixelRatio || 1));
    const canvas = await html2canvas(
      container,
      {
        backgroundColor: '#ffffff',
        scale,
        useCORS: true,
        logging: false,
        windowWidth: width,
        windowHeight: height,
        removeContainer: true,
      },
    );
    container.style.overflow = prev.overflow;
    container.style.height = prev.height;
    container.style.maxHeight = prev.maxHeight;
    container.style.marginLeft = prev.marginLeft;
    container.style.marginRight = prev.marginRight;
    container.classList.remove('aig-export-root');
    if (exportStyle && exportStyle.parentNode) {
      exportStyle.parentNode.removeChild(exportStyle);
    }
    const pdf = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4', compress: true });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const marginMm = 5;
    const contentWidthMm = pageWidth - marginMm * 2;
    const contentHeightMm = pageHeight - marginMm * 2;
    const pxToMm = 25.4 / 96;
    const cssWidthPx = container.getBoundingClientRect().width || canvas.width / Math.max(scale, 1);
    const cssWidthMm = cssWidthPx * pxToMm;
    const imgWidth = Math.min(contentWidthMm, cssWidthMm);
    let offsetY = 0;
    const pageCanvas = document.createElement('canvas');
    pageCanvas.width = canvas.width;
    pageCanvas.height = Math.floor((contentHeightMm * canvas.width) / imgWidth);
    const pageCtx = pageCanvas.getContext('2d');
    if (!pageCtx) return;
    const offsetXMm = marginMm + (contentWidthMm - imgWidth) / 2;
    const topAdjustMm = 2;
    while (offsetY < canvas.height) {
      const sliceHeight = Math.min(pageCanvas.height, canvas.height - offsetY);
      pageCanvas.height = sliceHeight;
      pageCtx.clearRect(0, 0, pageCanvas.width, pageCanvas.height);
      pageCtx.drawImage(canvas, 0, offsetY, canvas.width, sliceHeight, 0, 0, pageCanvas.width, sliceHeight);
      const pageImgData = pageCanvas.toDataURL('image/png');
      const pageImgHeight = (sliceHeight * imgWidth) / canvas.width;
      if (offsetY > 0) pdf.addPage();
      pdf.addImage(pageImgData, 'PNG', offsetXMm, Math.max(marginMm - topAdjustMm, 0), imgWidth, pageImgHeight, undefined, 'FAST');
      offsetY += sliceHeight;
    }
    pdf.save(filename);
  } finally {
    if (toggledFullscreen && onToggleFullscreen) {
      try {
        onToggleFullscreen();
      } catch {}
    }
  }
}


