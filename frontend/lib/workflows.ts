export type WorkflowCode = 'BPP' | 'INDEPENDENT';

export type WorkflowRoute = {
  code: WorkflowCode;
  label: string;
  route: string;
};

export const workflowRoutes: WorkflowRoute[] = [
  { code: 'BPP', label: 'BPP Ordering', route: '/workflows/bpp' },
  { code: 'INDEPENDENT', label: 'Independent Ordering', route: '/workflows/independent' },
];
