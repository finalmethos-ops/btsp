import { describe, expect, it } from 'vitest';
import type { ConfigEntryWrite } from './configuration-api';

describe('configuration API payloads', () => {
  it('supports scoped JSON settings', () => {
    const payload: ConfigEntryWrite = {
      scope_type: 'workflow',
      scope_key: 'BPP',
      key: 'ordering.enabled',
      value: { enabled: true },
      is_active: true,
      updated_by: 'admin@example.com',
    };

    expect(payload.scope_key).toBe('BPP');
    expect(payload.value).toEqual({ enabled: true });
  });
});
