import { describe, expect, it } from 'vitest';
import { workflowRoutes } from './workflows';

describe('workflowRoutes', () => {
  it('keeps BPP and Independent workflow routes separate', () => {
    const routes = new Map(workflowRoutes.map((workflow) => [workflow.code, workflow.route]));

    expect(routes.get('BPP')).toBe('/workflows/bpp');
    expect(routes.get('INDEPENDENT')).toBe('/workflows/independent');
  });
});
