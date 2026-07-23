import { useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { systemApi, AIG_RELEASE_URL } from '../lib/systemApi';
import { enableVersionCheck } from '../config/privateModules';

// Last notified version info (avoids repeated popups for the same version on the same day)
const LAST_NOTIFIED_KEY = 'aig_version_last_notified';

// Daily check interval: for sessions that stay on the page for a long time
const ONE_DAY = 24 * 60 * 60 * 1000;

/**
 * Version-check hook:
 * - Whether it is enabled is decided by the private overlay's enableVersionCheck
 *   (enabled by default in the open-source build)
 * - Calls GET /api/v1/system/version once on page open/refresh
 * - Calls it again once per day for long-lived sessions
 * - If a new version is available, shows a notification (does not auto-close;
 *   the user must dismiss it manually) with a release link.
 *   Notifies at most once per day for the same version.
 */
export function useVersionCheck() {
  const { t } = useTranslation();
  // Prevent duplicate triggers under React.StrictMode on first paint
  const startedRef = useRef(false);

  const notifyIfNeeded = useCallback(
    (currentVersion: string, latestVersion: string, releaseUrl: string) => {
      const today = new Date().toDateString();
      try {
        const raw = localStorage.getItem(LAST_NOTIFIED_KEY);
        const notified = raw ? JSON.parse(raw) : {};
        // Skip if the same version has already been notified today
        if (notified.version === latestVersion && notified.date === today) {
          return;
        }
        localStorage.setItem(
          LAST_NOTIFIED_KEY,
          JSON.stringify({ version: latestVersion, date: today })
        );
      } catch {
        // Ignore when localStorage is unavailable and still show the notification
      }

      // Show both current and latest versions in the description (keep the title concise, without version numbers)
      let description: string;
      if (currentVersion && latestVersion) {
        description = t('versionUpdate.descriptionFull', {
          current: currentVersion,
          latest: latestVersion,
        });
      } else if (latestVersion) {
        description = t('versionUpdate.descriptionLatest', { latest: latestVersion });
      } else if (currentVersion) {
        description = t('versionUpdate.descriptionWithCurrent', { current: currentVersion });
      } else {
        description = t('versionUpdate.description');
      }

      // Use a custom description and place the "View release" button below the prompt text
      toast.info(t('versionUpdate.title'), {
        description: (
          <div className="flex flex-col gap-2">
            <span>{description}</span>
            <button
              type="button"
              onClick={() =>
                window.open(releaseUrl || AIG_RELEASE_URL, '_blank', 'noopener,noreferrer')
              }
              className="self-center rounded-md bg-zinc-900 px-3 py-1 text-xs font-medium text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              {t('versionUpdate.viewRelease')}
            </button>
          </div>
        ),
        duration: Infinity, // Do not auto-close
        closeButton: true, // Show the close button so the user can dismiss it manually
      });
    },
    [t]
  );

  const runCheck = useCallback(async () => {
    try {
      const resp = await systemApi.checkVersion();
      // Handle both status === 0 (business success) and responses without a status wrapper
      if (resp && resp.status !== undefined && resp.status !== 0) {
        return;
      }
      const data = resp?.data;
      if (data?.update_available) {
        notifyIfNeeded(
          data.current_version || '',
          data.latest_version || '',
          data.release_url || AIG_RELEASE_URL
        );
      }
    } catch {
      // A failed version check should not affect the main flow; swallow silently
    }
  }, [notifyIfNeeded]);

  useEffect(() => {
    // Whether to enable is decided by the private overlay (avoids repeated popups in internal environments)
    if (!enableVersionCheck) return;
    if (startedRef.current) return;
    startedRef.current = true;

    // Check immediately on page open/refresh
    runCheck();
    // Check once per day for long-lived sessions
    const timer = setInterval(runCheck, ONE_DAY);
    return () => clearInterval(timer);
  }, [runCheck]);
}
