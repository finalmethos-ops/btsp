module.exports = [
  {
    languageOptions: {
        parser: require("@typescript-eslint/parser"),
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
      "no-unused-vars": "warn",
      "no-undef": "error",
    },
    ignores: [
      ".next/**",
      "out/**",
      "dist/**",
      "coverage/**",
      "next-env.d.ts",
    ],
  },
];
