'use client';

import { FormEvent, useState } from 'react';
import { useAuth } from '@/lib/auth';

export function LoginForm() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await signIn(email, password);
    } catch {
      setError('Unable to sign in with those credentials.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex max-w-md flex-col gap-4 rounded-lg bg-white p-8 shadow">
      <div>
        <h1 className="text-2xl font-bold">BTSP Login</h1>
        <p className="mt-2 text-sm text-slate-600">Sign in to access your assigned workflows.</p>
      </div>
      <label className="flex flex-col gap-2 text-sm font-medium">
        Email
        <input
          className="rounded border border-slate-300 px-3 py-2"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          type="email"
          required
        />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium">
        Password
        <input
          className="rounded border border-slate-300 px-3 py-2"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          type="password"
          required
        />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button className="rounded bg-slate-900 px-4 py-2 font-semibold text-white" disabled={isSubmitting} type="submit">
        {isSubmitting ? 'Signing in...' : 'Sign in'}
      </button>
    </form>
  );
}
