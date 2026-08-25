import { defineConfig } from "eslint/config";

// Minimal ESLint configuration that avoids extending external plugin configs
// which can fail in CI when peer deps or export shapes differ. This keeps
// lint runnable in the CI environment. Reintroduce plugin-based extends once
// peer deps and config shapes are stabilized.
export default defineConfig({
  languageOptions: {
    parser: "@typescript-eslint/parser",
    parserOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      ecmaFeatures: { jsx: true },
    },
    globals: {
      window: "readonly",
      process: "readonly",
    },
  },
  rules: {
    // Keep only a small set of safe rules; expand later when plugins are stable
    "no-unused-vars": "warn",
    "no-undef": "error",
  },
  ignorePatterns: [
    ".next/**",
    "out/**",
    "dist/**",
    "coverage/**",
    "next-env.d.ts",
  ],
});
