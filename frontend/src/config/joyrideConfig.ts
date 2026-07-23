// Common Joyride style configuration
export const joyrideStyles = {
  options: {
    primaryColor: '#2563eb',
    zIndex: 10000,
  },
  tooltip: {
    fontSize: '14px',
  },
  tooltipContent: {
    fontSize: '14px',
    paddingTop: '30px',
  },
  tooltipFooter: {
    margin: '0 10px 10px 10px',
    fontSize: '14px',
  },
  buttonNext: {
    fontSize: '14px',
  },
  buttonBack: {
    fontSize: '14px',
  },
  buttonSkip: {
    fontSize: '14px',
  },
} as any;

// Common Joyride locale configuration function
export const getJoyrideLocale = (t: (key: string) => string) => ({
  back: t('common.previous'),
  close: t('common.close'),
  last: t('floatingInputArea.tour.finish'),
  next: t('common.next'),
  nextLabelWithProgress: t('floatingInputArea.tour.nextWithProgress'),
  skip: t('floatingInputArea.tour.skip'),
});

