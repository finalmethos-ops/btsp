module.exports = {
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
    ecmaFeatures: { jsx: true },
  },
  env: {
    browser: true,
    node: true,
    es2022: true,
  },
  rules: {
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
};
