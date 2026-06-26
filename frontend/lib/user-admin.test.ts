import { describe, expect, it } from 'vitest';
import type { AdminUserCreate, AdminUserUpdate } from './api';

describe('user admin payloads', () => {
  it('supports create payload role assignment', () => {
    const payload: AdminUserCreate = {
      email: 'manager@example.com',
      display_name: 'Manager',
      password: 'change-this-password',
      is_active: true,
      role_codes: ['BPP_ADMIN'],
    };

    expect(payload.role_codes).toEqual(['BPP_ADMIN']);
    expect(payload.is_active).toBe(true);
  });

  it('supports update payload role assignment', () => {
    const payload: AdminUserUpdate = {
      role_codes: ['INDEPENDENT_ADMIN'],
      is_active: false,
    };

    expect(payload.role_codes).toEqual(['INDEPENDENT_ADMIN']);
    expect(payload.is_active).toBe(false);
  });
});
