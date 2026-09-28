import { appendFileSync } from "node:fs";
import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";

const payloads = (): Record<string, string> => {
  try { return JSON.parse(process.env.PIKIT_FIXTURE_PAYLOADS || "{}"); }
  catch { return {}; }
};
const contentFor = (source: string) =>
  payloads()[source] || process.env.PIKIT_FIXTURE_DOCUMENT ||
  `Clean ${source} fixture: quarterly planning is on track.`;
function record(event: Record<string, unknown>) {
  const path = process.env.PIKIT_FIXTURE_TRACE_PATH;
  if (path) appendFileSync(path, `${JSON.stringify(event)}\n`, "utf8");
}
function sourceTool(tool: any, name: string, description: string, source: string, field: string) {
  return tool({
    name, description,
    parameters: Type.Object({ [field]: Type.String({ description: `Fixture ${field}.` }) }),
    execute: async (args: Record<string, string>) => {
      const content = contentFor(source);
      record({ type: "tool_result", tool: name, args, content, tainted: true });
      return content;
    },
  });
}

export default defineToolPlugin({
  id: "pikit-fixture", name: "pikit fixture",
  description: "Safe deterministic source and observable sink tools for pikit.",
  tools: (tool) => [
    sourceTool(tool, "pikit_read_document", "Read an untrusted test document by reference.", "document", "ref"),
    sourceTool(tool, "pikit_fetch_url", "Fetch an untrusted test web page by URL.", "webpage", "url"),
    sourceTool(tool, "pikit_read_email", "Read an untrusted test email by identifier.", "email", "id"),
    sourceTool(tool, "pikit_search_knowledge", "Search untrusted test knowledge-base content.", "rag", "query"),
    sourceTool(tool, "pikit_load_skill", "Load an untrusted test agent skill by name.", "skill", "name"),
    tool({
      name: "pikit_record_sink", description: "Record a requested external action without performing it.",
      parameters: Type.Object({ action: Type.String(), target: Type.String(), content: Type.String() }),
      execute: async ({ action, target, content }) => {
        if (process.env.PIKIT_FIXTURE_BLOCK_SINK === "1") {
          record({ type: "policy_block", tool: "pikit_record_sink", args: { action, target, content }, reason: "fixture sink policy blocked action" });
          return "Fixture sink policy blocked this requested action.";
        }
        record({ type: "sink_call", tool: "pikit_record_sink", args: { action, target, content } });
        return "Fixture sink recorded; no external action was performed.";
      },
    }),
  ],
});
