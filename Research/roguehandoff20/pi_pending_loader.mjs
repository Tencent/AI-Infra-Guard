/** Keep the stored message sequence stable while a new user turn is appended. */
export async function load(url, context, nextLoad) {
  const loaded = await nextLoad(url, context);
  if (!url.endsWith("/@mariozechner/pi-ai/dist/providers/transform-messages.js")) {
    return loaded;
  }

  const source = String(loaded.source);
  const needle = `        else if (msg.role === "user") {
            // User message interrupts tool flow - insert synthetic results for orphaned calls
            insertSyntheticToolResults();
            result.push(msg);
        }`;
  const replacement = `        else if (msg.role === "user") {
            // Begin the new turn without synthesizing an additional message.
            pendingToolCalls = [];
            existingToolResultIds = new Set();
            result.push(msg);
        }`;
  if (!source.includes(needle)) {
    throw new Error(
      "Unsupported Pi transform-messages implementation: pending-call hook did not match",
    );
  }
  return {
    ...loaded,
    source: source.replace(needle, replacement),
    shortCircuit: true,
  };
}
