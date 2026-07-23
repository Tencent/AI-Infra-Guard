/**
 * =============================================================================
 * Private Overlay Bridge
 * =============================================================================
 *
 * This file is the interface contract layer of the "open-source core +
 * private overlay" architecture:
 *
 * 1) Open-source build (default): This file is the only implementation.
 *    All exports are "no-op / null / empty array / default component". The
 *    open-source repository only exposes this file, and no internal
 *    information is included in the compiled artifacts.
 *
 * 2) Private overlay: For internal builds, a vite alias points
 *    "@/config/privateModules" to "private/privateModules"
 *    (see vite.config.ts). The private implementation may override any of
 *    the exports below on demand, e.g. returning <ProLoginPage />, a real
 *    businessPartners array, etc.
 *
 * 3) Contract constraint: When introducing new pro/internal-only
 *    capabilities, an "empty implementation signature" must first be
 *    defined here and then overridden on the private side, to avoid
 *    isPro branches or mailto:xxx@tencent.com appearing directly in the
 *    open-source code.
 * =============================================================================
 */
import React from 'react';

/**
 * AppShell: wraps the entire App in main.tsx.
 *
 * Open-source build: passthrough, no wrapping.
 * Internal overlay: can mount <GoogleOAuthProvider> + <AuthProvider> here
 * to enable Google login and other capabilities. The related dependencies
 * (e.g. @react-oauth/google) are only bundled in the internal build.
 */
export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <>{children}</>
);

/**
 * AuthGate: wraps the main app routes to decide whether login is required.
 *
 * Open-source build: directly passes through children; no login flow.
 * Internal overlay: can be replaced with an <AuthGuard> component
 * (requires login and renders ProLoginPage).
 */
export const AuthGate: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <>{children}</>
);

/** Sensitive data / collaboration contact hint (second tab in the Star / SensitiveData dialog) */
export interface SensitiveContact {
  /** i18n key used as the content of the Trans component */
  i18nKey: string;
  /** href for the link (may be mailto:, wxwork://, etc.) */
  href: string;
}

/**
 * Returns extra "cooperation / contact" hints; the open-source build
 * returns null (not rendered). The internal build can return internal
 * emails or Enterprise WeChat group links.
 */
export const sensitiveContact: SensitiveContact | null = null;

/** Home page "business partners" data; empty array in the open-source build means not rendered */
export interface BusinessPartner {
  name: string;
  logo: string;
}
export const businessPartners: readonly BusinessPartner[] = [];

/** Article list for the "Practice and Research" section on the home page; open-source build returns null to skip rendering */
export interface ArticleItem {
  id: number;
  title: string;
  image: string;
  author: string;
  date: string;
  url: string;
}
export interface PracticeArticles {
  practicalCases: ArticleItem[];
  latestResearch: ArticleItem[];
  /** Link to a landing page with more articles */
  moreArticlesUrl?: string;
}
export const practiceArticles: PracticeArticles | null = null;

/**
 * "Practice and Research" showcase (Contributors + article list). The
 * open-source build returns null (not rendered); the internal overlay
 * returns the real component. Used as an alternative to VITE_SHOW_PRACTICE
 * inside ChatArea.
 */
export const PracticeShowcase: React.ComponentType | null = null;

/** Whether to show the "More features" dropdown menu (contains internal-only entries such as liveJailBench) */
export const hasMoreFeaturesMenu: boolean = false;

/** Whether to show the "Business partners" section (disabled by default) */
export const showBusinessPartners: boolean = false;

/** Whether to guard against "deleting the default model" (no such restriction in the open-source build) */
export const protectDefaultModel: boolean = false;

/** Maximum number of attack methods; null means unlimited */
export const maxAttackMethods: number | null = null;

/**
 * Whether the "standalone documentation site" mode is enabled
 * (previously the openSourceDoc environment).
 * Defaults to false in the open-source build; can be set to true for
 * `vite --mode docSite` scenarios.
 */
export const isDocSiteMode: boolean = false;

/**
 * Documentation variant identifier used as the suffix when
 * HelpDocumentPage loads md files.
 * Fixed to 'openSource' in the open-source build. The private build
 * may override it to 'pro', 'internal', etc.
 */
export type DocVariant = 'openSource' | 'pro' | 'internal';
export const docVariant: DocVariant = 'openSource';

/** Whether the "check for new version" reminder is enabled (open-source build enables it by default, pointing to GitHub Releases) */
export const enableVersionCheck: boolean = true;

/**
 * Extra routes: standalone sub-apps injected by the private overlay
 * (e.g. the LiveJailBench leaderboard).
 * Defaults to an empty array in the open-source build.
 *
 * Each item = { path, element } and is mounted at the top level of the
 * main <Routes>. Example:
 * { path: '/liveJailBench/*', element: <AttackLeaderboardApp /> }
 */
export interface ExtraRoute {
  path: string;
  element: React.ReactElement;
}
export const extraRoutes: readonly ExtraRoute[] = [];

/**
 * Extra menu items shown in the "More features" dropdown
 * (e.g. the "LLM security leaderboard" entry).
 * Defaults to an empty array in the open-source build and, combined with
 * hasMoreFeaturesMenu=false, is hidden entirely.
 *
 * The icon is passed in by the caller as a lucide-react component; href
 * is opened via window.open.
 */
export interface ExtraFeatureItem {
  icon: React.ComponentType<{ className?: string }>;
  labelI18nKey: string;
  href: string;
}
export const extraMoreFeatures: readonly ExtraFeatureItem[] = [];
