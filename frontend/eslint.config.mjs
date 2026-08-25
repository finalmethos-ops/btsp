import { defineConfig } from "eslint/config";

export default defineConfig({
  parser: "@typescript-eslint/parser",
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
  ],
  settings: {
    react: { version: "detect" },
  },
  rules: {
    "react-hooks/set-state-in-effect": "off",
  },
  ignorePatterns: [
    ".next/**",
    "out/**",
    "dist/**",
    "coverage/**",
    "next-env.d.ts",
  ],
});
