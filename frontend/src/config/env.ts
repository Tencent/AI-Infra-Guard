/**
 * Environment constants.
 *
 * Note: The open-source build only supports two modes:
 *   - development (local development)
 *   - openSource (production build)
 *
 * Other environments (such as pro/internal/docSite) no longer exist as
 * hard-coded branches in the source. Instead, their behavior is injected by
 * the private overlay through the `src/config/privateModules.ts` bridge
 * (see that file for details).
 *
 * Therefore only the isDevelopment / isOpenSource constants are kept here,
 * to avoid any isPro / isProduction or other internal environment checks
 * appearing in the open-source repository.
 */
export const env = {
  VITE_APP_ENV: import.meta.env.VITE_APP_ENV || 'development',
  VITE_API_BASE_URL: '',
  VITE_ENABLE_WELCOME_ANIMATION: import.meta.env.VITE_ENABLE_WELCOME_ANIMATION === 'TRUE',
  VITE_BASENAME: import.meta.env.VITE_BASENAME || '/',
  VITE_ENABLE_EVAL_MODEL: import.meta.env.VITE_ENABLE_EVAL_MODEL,
} as const;

export const isDevelopment = env.VITE_APP_ENV === 'development';
export const isOpenSource = env.VITE_APP_ENV === 'openSource';

/**
 * Whether to show the "scoring model" (evalModel) selection button for
 * the LLM security checkup / jailbreak tasks.
 *
 * Controlled independently by VITE_ENABLE_EVAL_MODEL (recommended: "TRUE" / "FALSE").
 * If not set, it falls back to isOpenSource to preserve the previous default:
 *   - openSource build   → enabled
 *   - other builds       → disabled
 *
 * To force enable/disable regardless of the build variant, set
 * VITE_ENABLE_EVAL_MODEL=TRUE (or FALSE) in the corresponding .env file.
 */
export const enableEvalModel: boolean =
  env.VITE_ENABLE_EVAL_MODEL === undefined || env.VITE_ENABLE_EVAL_MODEL === ''
    ? isOpenSource
    : String(env.VITE_ENABLE_EVAL_MODEL).toUpperCase() === 'TRUE';
