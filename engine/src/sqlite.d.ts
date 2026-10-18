declare module 'node:sqlite' {
  export class DatabaseSync {
    constructor(path: string, options?: { readOnly?: boolean });
    prepare(sql: string): {
      all(...args: unknown[]): Record<string, unknown>[];
      get(...args: unknown[]): Record<string, unknown> | undefined;
      run(...args: unknown[]): { changes: number };
    };
    close(): void;
  }
}
