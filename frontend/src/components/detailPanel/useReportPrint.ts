import { useReactToPrint } from 'react-to-print';

export const useReportPrint = (contentRef: React.RefObject<HTMLDivElement | null>, documentTitle: string) => {
  return useReactToPrint({
    contentRef,
    documentTitle,
    pageStyle: `
      @page {
        size: auto;
        margin: 20mm;
      }
      @media print {
        html, body {
          height: initial !important;
          overflow: initial !important;
          -webkit-print-color-adjust: exact;
        }
        .print-content-wrapper,
        .print-content-wrapper * {
          font-family: sans-serif, -apple-system, Avenir, Helvetica, Arial, "Segoe UI", "Songti SC", SimSun, serif;
        }  
        
        /* Force-reset the print container */
        .print-content-wrapper {
          display: block !important;
          height: auto !important;
          min-height: auto !important;
          max-height: none !important;
          overflow: visible !important;
          width: 100% !important;
        }

        /* Optimize internal scroll containers to prevent content from being truncated, but skip overflow-hidden (used for rounded-corner clipping) */
        .print-content-wrapper [class*="overflow-auto"],
        .print-content-wrapper [class*="overflow-scroll"],
        .print-content-wrapper [class*="overflow-y-"],
        .print-content-wrapper [class*="scroll"] {
          overflow: visible !important;
          height: auto !important;
          max-height: none !important;
        }

        /* Hide buttons and other elements that are not needed for printing */
        button, 
        .fixed,
        [role="button"] {
          display: none !important;
        }

        /* Core fix: reset the layout model for truncated text */
        .print-content-wrapper span[style*="WebkitLineClamp"],
        .print-content-wrapper span[style*="webkit-line-clamp"],
        .print-content-wrapper .text-ellipsis {
          display: block !important;
          height: auto !important;
          max-height: none !important;
          overflow: visible !important;
          -webkit-line-clamp: unset !important;
          line-clamp: unset !important;
        }

        /* Fully remove any potential internal page-break restrictions and only protect the smallest units */
        .card, .p-4, .rounded-2xl, div, section, article {
          break-inside: auto !important; 
          page-break-inside: auto !important;
        }
        
        /* Keep only truly indivisible atomic elements intact */
        tr, td, th, img, svg {
          break-inside: avoid !important;
          page-break-inside: avoid !important;
        }
        
        /* Force allow page breaks after headings */
        h1, h2, h3, h4, h5, h6 {
          break-after: auto !important;
          page-break-after: auto !important;
        }

        /* Remove all shadows to fix gray borders/blocks that appear when printing */
        * {
          box-shadow: none !important;
          text-shadow: none !important;
        }
      }
    `,
  });
};
