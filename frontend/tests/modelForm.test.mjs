import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, realpathSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { after, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createInstance } from 'i18next';

const require = createRequire(import.meta.url);
const frontend = fileURLToPath(new URL('../', import.meta.url));
const temporaryRoot = realpathSync(tmpdir());
const output = mkdtempSync(join(temporaryRoot, 'aig-model-form-test-'));
after(() => {
  assert.equal(dirname(realpathSync(output)), temporaryRoot);
  rmSync(output, { recursive: true, force: true });
});
execFileSync(process.execPath, [
  require.resolve('typescript/bin/tsc'), 'src/lib/modelForm.ts',
  '--rootDir', 'src', '--outDir', output, '--target', 'ES2020',
  '--module', 'commonjs', '--strict', '--skipLibCheck',
], { cwd: frontend, stdio: 'pipe' });
const { saveModelForm, ModelFormValidationError } = require(join(output, 'lib/modelForm.js'));

const translations = Object.fromEntries(['en', 'zh'].map(language => [
  language, JSON.parse(readFileSync(new URL('../src/i18n/locales/' + language + '.json', import.meta.url), 'utf8')),
]));
const i18n = createInstance();
await i18n.init({
  lng: 'en', fallbackLng: 'en',
  resources: Object.fromEntries(Object.entries(translations).map(([language, translation]) => [
    language, { translation },
  ])),
  interpolation: { escapeValue: false },
});
const messages = (language = 'en') => ({
  invalidJson: i18n.t('modelManagement.invalidJson', { lng: language }),
  invalidHeaderValue: key => i18n.t('modelManagement.invalidHeaderValue', { key, lng: language }),
});

const makeInput = mode => ({
  mode, modelId: 'test-model',
  model: { model: 'fake-model', token: 'fake-token', base_url: 'https://example.invalid', note: 'test', limit: '7' },
  extraHeadersText: '{}', extraBodyText: '{}',
});
const success = { status: 0, data: null };
function makeApi() {
  const calls = [];
  return {
    calls,
    async createModel(data) { calls.push({ mode: 'create', data }); return success; },
    async updateModel(id, data) { calls.push({ mode: 'update', id, data }); return success; },
  };
}

for (const mode of ['create', 'update']) {
  for (const value of [null, 42, false, [], {}]) {
    test(mode + ' rejects header value ' + JSON.stringify(value) + ' before calling either API', async () => {
      const api = makeApi();
      const input = { ...makeInput(mode), extraHeadersText: JSON.stringify({ 'X-Valid': 'ok', Authorization: value }) };
      await assert.rejects(saveModelForm(api, input, messages()), error => {
        assert.ok(error instanceof ModelFormValidationError);
        assert.equal(error.message, 'Extra header "Authorization" must have a string value.');
        return true;
      });
      assert.deepEqual(api.calls, []);
    });
  }

  test(mode + ' preserves strings, masks, special keys and all nested body value types', async () => {
    const api = makeApi();
    const input = {
      ...makeInput(mode),
      extraHeadersText: '{"Authorization":"********","X-Empty":"","X-Space":" keep spaces ","__proto__":"literal"}',
      extraBodyText: '{"provider.order":["test"],"nested":{"list":[null,true,false,0,2.5,"text",{"deep":"value"}]},"number":3,"boolean":false,"null":null,"string":"text"}',
    };
    const before = structuredClone(input);
    assert.equal(await saveModelForm(api, input, messages()), success);
    assert.deepEqual(api.calls, [{
      mode,
      ...(mode === 'update' ? { id: input.modelId } : {}),
      data: {
        ...(mode === 'create' ? { model_id: input.modelId } : {}),
        model: {
          ...input.model, limit: 7,
          extra_headers: JSON.parse(input.extraHeadersText),
          extra_body: JSON.parse(input.extraBodyText),
        },
      },
    }]);
    assert.deepEqual(input, before);
  });

  for (const text of ['', ' \n\t ', '{}']) {
    test(mode + ' explicitly clears both options for ' + JSON.stringify(text), async () => {
      const api = makeApi();
      await saveModelForm(api, { ...makeInput(mode), extraHeadersText: text, extraBodyText: text }, messages());
      assert.deepEqual(api.calls[0].data.model.extra_headers, {});
      assert.deepEqual(api.calls[0].data.model.extra_body, {});
    });
  }

  for (const field of ['extraHeadersText', 'extraBodyText']) {
    for (const text of ['{"secret":"fake-value"', 'null', '[]', '42', 'true', '"text"']) {
      test(mode + ' rejects invalid object in ' + field + ': ' + text, async () => {
        const api = makeApi();
        await assert.rejects(saveModelForm(api, { ...makeInput(mode), [field]: text }, messages()), {
          name: 'Error', message: 'Invalid JSON',
        });
        assert.deepEqual(api.calls, []);
      });
    }
  }

  for (const failure of ['status', 'network']) {
    test(mode + ' preserves input and allows retry after ' + failure + ' failure', async () => {
      const api = makeApi();
      const method = mode === 'create' ? 'createModel' : 'updateModel';
      const original = api[method].bind(api);
      let attempts = 0;
      api[method] = async (...args) => {
        attempts++;
        if (attempts === 1) {
          if (failure === 'network') throw new Error('Simulated offline');
          return { status: 1, message: 'Simulated failure', data: null };
        }
        return original(...args);
      };
      const input = { ...makeInput(mode), extraHeadersText: '{"Authorization":"********"}', extraBodyText: '{"value":null}' };
      const before = structuredClone(input);
      if (failure === 'network') await assert.rejects(saveModelForm(api, input, messages()), /Simulated offline/);
      else assert.equal((await saveModelForm(api, input, messages())).status, 1);
      assert.deepEqual(input, before);
      assert.equal(await saveModelForm(api, input, messages()), success);
      assert.equal(attempts, 2);
      assert.equal(api.calls[0].data.model.extra_headers.Authorization, '********');
      assert.deepEqual(input, before);
    });
  }
}

test('header validation interpolates the exact key in both supported languages', async () => {
  for (const language of ['en', 'zh']) {
    const api = makeApi();
    const key = 'X-Custom/<key>';
    const input = { ...makeInput('update'), extraHeadersText: JSON.stringify({ [key]: null }) };
    const expected = language === 'en'
      ? 'Extra header "X-Custom/<key>" must have a string value.'
      : '额外请求头“X-Custom/<key>”的值必须为字符串。';
    await assert.rejects(saveModelForm(api, input, messages(language)), { message: expected });
    assert.deepEqual(api.calls, []);
  }
});
