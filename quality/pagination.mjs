/** Bounded tools/list traversal using the official SDK; never invokes a tool. */
export async function collectToolPages(client) {
  const cursors = new Set();
  let cursor;
  let tools = 0;
  for (let page = 1; page <= 100; page++) {
    const result = await client.listTools(cursor === undefined ? undefined : { cursor });
    tools += result.tools.length;
    if (tools > 10000) throw new Error('Tool count exceeds admitted budget');
    if (result.nextCursor === undefined) return { pages: page, tools, continuation_exercised: page > 1 };
    if (typeof result.nextCursor !== 'string' || !result.nextCursor || cursors.has(result.nextCursor)) throw new Error('Invalid or repeated pagination cursor');
    cursors.add(result.nextCursor);
    cursor = result.nextCursor;
  }
  throw new Error('Pagination exceeds admitted page budget');
}
