/**
 * Controlled DSH source and sink tools for authorized A.I.G security tests.
 *
 * Source tools return clean sample content or a per-run tainted artifact.
 * Sink tools only append attempted calls to a local JSON log. They do not send
 * network requests, execute commands, alter files, or create external effects.
 */

import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'

function readJson(path: string | undefined): Record<string, unknown> | undefined {
  if (!path || !existsSync(path)) return undefined
  try { return JSON.parse(readFileSync(path, 'utf-8')) as Record<string, unknown> } catch { return undefined }
}

function taintedContent(): string | undefined {
  return readJson(process.env.AIG_TAINT_FILE)?.payload as string | undefined
}

function sampleContent(): string {
  const path = process.env.AIG_SAMPLE_FILE
  if (!path || !existsSync(path)) return 'Clean sample content for an authorized security test.'
  return readFileSync(path, 'utf-8')
}

function recordSink(tool: string, args: Record<string, unknown>): void {
  const path = process.env.AIG_SINK_FILE
  if (!path) return
  const state = readJson(path) || { calls: [] }
  const calls = Array.isArray(state.calls) ? state.calls : []
  calls.push({ tool, args, timestamp: Date.now() })
  writeFileSync(path, JSON.stringify({ calls }, null, 2))
}

function sourceTool(name: string, description: string, parameters: Record<string, unknown>) {
  return defineTool({
    name, description, parameters,
    output: {
      schema: { type: 'object', additionalProperties: false, properties: { content: { type: 'string', required: true } } },
      render: (_args, value) => [{ type: 'text', text: (value as { content: string }).content }],
    },
    async execute() { return { content: taintedContent() || sampleContent() } },
  })
}

function sinkTool(name: string, description: string, parameters: Record<string, unknown>) {
  return defineTool({
    name, description, parameters,
    output: {
      schema: { type: 'object', additionalProperties: false, properties: { recorded: { type: 'boolean', required: true } } },
      render: () => [{ type: 'text', text: '[simulated action recorded]' }],
    },
    async execute(args) {
      recordSink(name, args as Record<string, unknown>)
      return { recorded: true }
    },
  })
}

export const name = 'aig-dsh-test-tools'
export const inject = ['tools']

export function apply(ctx: Context): void {
  ctx.tools.register(sourceTool('fetch_url', 'Read controlled web content.', { url: { type: 'string', required: true } }))
  ctx.tools.register(sourceTool('read_document', 'Read a controlled document.', { ref: { type: 'string', required: true } }))
  ctx.tools.register(sourceTool('read_email', 'Read a controlled email.', { id: { type: 'string', required: true } }))
  ctx.tools.register(sourceTool('search_knowledge', 'Search controlled knowledge content.', { query: { type: 'string', required: true } }))
  ctx.tools.register(sourceTool('load_skill', 'Load a controlled skill.', { name: { type: 'string', required: true } }))
  ctx.tools.register(sourceTool('read_channel', 'Read a controlled chat channel.', { channel: { type: 'string', required: true } }))

  ctx.tools.register(sinkTool('send_email', 'Record a simulated email action.', { to: { type: 'string', required: true }, subject: { type: 'string', required: true }, body: { type: 'string', required: true } }))
  ctx.tools.register(sinkTool('transfer_money', 'Record a simulated transfer action.', { to: { type: 'string', required: true }, amount: { type: 'string', required: true } }))
  ctx.tools.register(sinkTool('run_command', 'Record a simulated command action.', { command: { type: 'string', required: true } }))
  ctx.tools.register(sinkTool('create_post', 'Record a simulated post action.', { content: { type: 'string', required: true } }))
  ctx.tools.register(sinkTool('send_dm', 'Record a simulated direct-message action.', { to: { type: 'string', required: true }, message: { type: 'string', required: true } }))
  ctx.tools.register(sinkTool('post_message', 'Record a simulated channel-message action.', { channel: { type: 'string', required: true }, message: { type: 'string', required: true } }))
  ctx.tools.register(sinkTool('create_event', 'Record a simulated calendar action.', { title: { type: 'string', required: true }, time: { type: 'string', required: true } }))
  ctx.tools.register(sinkTool('post_form', 'Record a simulated form submission.', { url: { type: 'string', required: true }, data: { type: 'string' } }))
}
