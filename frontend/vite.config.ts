import path from 'path';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
import fs from 'fs';
import { glob } from 'glob';

/**
 * Open-source docs allowlist: only keeps the openSource variant + shared docs.
 * A private overlay can append its own rules via private/vite/docsAllowlist.mjs.
 */
const OPEN_SOURCE_DOC_ALLOWLIST: RegExp[] = [
  /openSource.*\.md$/,
  /^faq.*\.md$/,
  /^agent-scan-http-config.*\.md$/,
  /^getting-started.*\.md$/,
  /^mcp-scan.*\.md$/,
  /^skill-scan.*\.md$/,
  /^ai-infra-scan.*\.md$/,
  /^prompt-eval_method_Encoding.*\.md$/,
  /^prompt-eval_methpd_BehavioralControl.*\.md$/,
];

/**
 * Load the private overlay's docs allowlist (if present) to implement
 * "distribution variant" doc filtering.
 * private/vite/docsAllowlist.mjs must `export default` a RegExp[].
 */
async function loadPrivateDocsAllowlist(): Promise<RegExp[] | null> {
  const privateFile = path.resolve('private/vite/docsAllowlist.mjs');
  if (!fs.existsSync(privateFile)) return null;
  try {
    const mod = await import(privateFile);
    return Array.isArray(mod.default) ? mod.default : null;
  } catch (e) {
    console.warn('[private overlay] failed to load docsAllowlist:', e);
    return null;
  }
}

/**
 * Custom plugin: only copies public files that are actually referenced (including aigdocs).
 * Open-source build: only ships the openSource variant of the docs by default.
 * Internal override: when private/vite/docsAllowlist.mjs exists, it replaces the allowlist.
 */
function copyReferencedPublicFiles(mode: string) {
  // Only non-openSource modes are allowed to merge assets from private/ into dist.
  // This way, even if the local repo also contains private/, it will not contaminate
  // the open-source build output.
  const mergePrivateAssets = mode !== 'openSource';
  return {
    name: 'copy-referenced-public-files',
    async generateBundle() {
      const docsAllowlist = (await loadPrivateDocsAllowlist()) || OPEN_SOURCE_DOC_ALLOWLIST;

      const referencedFiles = new Set<string>();
      const publicRoot = path.resolve('public');
      const resolvePublicPath = (refPath: string, sourceFile: string) => {
        const normalizedPath = refPath.trim();
        if (normalizedPath.startsWith('http://') || normalizedPath.startsWith('https://')) return null;
        if (normalizedPath.startsWith('/')) {
          if (normalizedPath.startsWith('/api')) return null;
          return path.join('public', normalizedPath.substring(1));
        }
        if (normalizedPath.startsWith('./') || normalizedPath.startsWith('../')) {
          const absolutePath = path.resolve(path.dirname(sourceFile), normalizedPath);
          if (absolutePath.startsWith(publicRoot)) return absolutePath;
        }
        return null;
      };
      const normalizeRef = (rawRef: string) => {
        let cleanRef = rawRef.replace(/['"`]/g, '');
        if (cleanRef.startsWith('url(')) {
          cleanRef = cleanRef.replace(/url\(/g, '').replace(/\)$/g, '');
        }
        if (cleanRef.includes('${') && cleanRef.includes('images/')) {
          const match = cleanRef.match(/images\/([^\s`'"]+\.(png|jpg|jpeg|gif|svg|webp|ico))/);
          if (match) cleanRef = `/images/${match[1]}`;
        }
        return cleanRef;
      };

      const sourceFiles = await glob('src/**/*.{ts,tsx,js,jsx,css}');
      const htmlFiles = await glob('*.html');
      const mdFiles = await glob('public/aigdocs/**/*.md');

      const allFiles = [...sourceFiles, ...htmlFiles, ...mdFiles];

      for (const file of allFiles) {
        const content = fs.readFileSync(file, 'utf-8');

        const publicRefs =
          content.match(
            /['"`](\/|\.\.?\/)[^'"`]*\.(png|jpg|jpeg|gif|svg|webp|ico|md|yml|yaml|json|txt|pdf|doc|docx|css|js|woff|woff2|ttf|eot)['"`]/g,
          ) || [];
        const templateImageRefs =
          content.match(/\$\{[^}]*\}\/?images\/([^`'"\s]+\.(png|jpg|jpeg|gif|svg|webp|ico))/g) || [];
        const cssUrlRefs =
          content.match(/url\(['"`]?(\/|\.\.?\/)[^'"`\)]*\.(woff|woff2|ttf|eot|otf)['"`]?\)/g) || [];
        const markdownImageRefs = [
          ...content.matchAll(
            /!\[[^\]]*]\((?!https?:\/\/)((?:\/|\.\.?\/)[^)\s]*\.(?:png|jpg|jpeg|gif|svg|webp))\)/g,
          ),
        ].map(match => match[1]);

        const allRefs = [...publicRefs, ...cssUrlRefs, ...templateImageRefs];
        for (const ref of allRefs) {
          const cleanRef = normalizeRef(ref);
          const resolved = resolvePublicPath(cleanRef, file);
          if (resolved && fs.existsSync(resolved)) referencedFiles.add(resolved);
        }
        for (const markdownRef of markdownImageRefs) {
          const resolved = resolvePublicPath(markdownRef, file);
          if (resolved && fs.existsSync(resolved)) referencedFiles.add(resolved);
        }

        // Handle dynamically-loaded aigdocs files
        if (file.includes('HelpDocumentPage.tsx')) {
          const aigdocsFiles = await glob('public/aigdocs/**/*');
          for (const aigdocsFile of aigdocsFiles) {
            if (fs.statSync(aigdocsFile).isFile()) {
              const fileName = path.basename(aigdocsFile);
              let shouldInclude = true;
              if (fileName.endsWith('.md')) {
                shouldInclude = docsAllowlist.some(pattern => pattern.test(fileName));
              }
              if (!shouldInclude) continue;
              referencedFiles.add(aigdocsFile);
            }
          }
        }
      }

      // Force-copy all files under public/images/agents-icon
      const agentIconFiles = await glob('public/images/agents-icon/**/*');
      for (const iconFile of agentIconFiles) {
        if (fs.statSync(iconFile).isFile()) {
          referencedFiles.add(path.resolve(iconFile));
        }
      }


      // Copy referenced files into dist
      for (const filePath of referencedFiles) {
        const relativePath = path.relative('public', filePath);
        const destPath = path.join('dist', relativePath);
        const destDir = path.dirname(destPath);
        if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });
        fs.copyFileSync(filePath, destPath);
      }

      // ============================================================
      // Private overlay asset merging: if private/images or private/docs/aigdocs
      // exists, copy their contents into dist/images/ and dist/aigdocs/docs/
      // respectively, so that /images/xxx and /aigdocs/docs/xxx referenced by
      // private components remain accessible.
      // ============================================================
      const copyDir = (fromDir: string, toDir: string) => {
        if (!fs.existsSync(fromDir)) return;
        const files = fs.readdirSync(fromDir, { withFileTypes: true });
        for (const entry of files) {
          const src = path.join(fromDir, entry.name);
          const dst = path.join(toDir, entry.name);
          if (entry.isDirectory()) {
            copyDir(src, dst);
          } else if (entry.isFile()) {
            const dstDir = path.dirname(dst);
            if (!fs.existsSync(dstDir)) fs.mkdirSync(dstDir, { recursive: true });
            fs.copyFileSync(src, dst);
          }
        }
      };
      if (mergePrivateAssets) {
        const privateImagesDir = path.resolve('private/images');
        if (fs.existsSync(privateImagesDir)) {
          copyDir(privateImagesDir, path.resolve('dist/images'));
        }
        const privateDocsDir = path.resolve('private/docs/aigdocs');
        if (fs.existsSync(privateDocsDir)) {
          copyDir(privateDocsDir, path.resolve('dist/aigdocs/docs'));
        }
        // private/public/**: internal-only static assets (e.g. leaderboard/class.json)
        // are merged as-is into the dist/ root directory.
        const privatePublicDir = path.resolve('private/public');
        if (fs.existsSync(privatePublicDir)) {
          copyDir(privatePublicDir, path.resolve('dist'));
        }
      }
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Dev proxy target: prefer VITE_DEV_PROXY_TARGET, fall back to localhost if unset.
  const devProxyTarget = env.VITE_DEV_PROXY_TARGET || 'http://localhost:8088';

  const aliases: Record<string, string> = {
    '@': path.resolve(__dirname, './src'),
  };
  // If a private/ directory exists, allow imports via @private/xxx and (in non-openSource
  // modes) automatically point the bridge module @/config/privateModules to the private
  // implementation, overriding the default no-op stubs.
  const privateDir = path.resolve(__dirname, 'private');
  if (fs.existsSync(privateDir)) {
    aliases['@private'] = privateDir;
    if (mode !== 'openSource') {
      // Try both .tsx / .ts extensions (.tsx contains JSX bridge components such as
      // AppShell / AuthGate).
      const candidates = [
        path.join(privateDir, 'privateModules.tsx'),
        path.join(privateDir, 'privateModules.ts'),
      ];
      const privateModulesFile = candidates.find(f => fs.existsSync(f));
      if (privateModulesFile) {
        aliases['@/config/privateModules'] = privateModulesFile;
      }
    }
  }

  return {
    base: env.VITE_BASENAME || '/',
    plugins: [react(), copyReferencedPublicFiles(mode)],
    resolve: { alias: aliases },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: devProxyTarget,
          changeOrigin: true,
          rewrite: p => p.replace(/^\/api/, '/api'),
          configure: proxy => {
            proxy.on('proxyReq', proxyReq => {
              const cookies = proxyReq.getHeader('cookie') as string;
              if (cookies) {
                const gtMatch = cookies.match(/g_t=([^;]+)/);
                if (gtMatch) {
                  proxyReq.setHeader('Authorization', `Bearer ${gtMatch[1]}`);
                }
              }
            });
          },
        },
        '/llm': {
          target: devProxyTarget,
          changeOrigin: true,
          rewrite: p => p.replace(/^\/llm/, '/llm'),
        },
      },
      hmr: { overlay: false },
    },
    build: {
      assetsInlineLimit: 100000000,
      rollupOptions: {
        input: {
          main: path.resolve(__dirname, 'index.html'),
        },
      },
      copyPublicDir: false,
    },
    assetsInclude: ['**/*.png', '**/*.jpg', '**/*.jpeg', '**/*.gif', '**/*.svg', '**/*.webp'],
  };
});
