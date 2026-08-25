ESLint configuration

This frontend uses ESLint with the flat config format. The primary config file is:

- eslint.config.cjs (flat config)

Guidance for contributors

- Do not add a legacy .eslintrc.* file; it will conflict with the flat config. If you need to adjust linting rules, edit eslint.config.cjs.
- Avoid inline /* eslint-env */ comments because the flat config does not recognize them; prefer declaring globals in eslint.config.cjs under `languageOptions.globals`.
- If you need parser or plugin changes, update the devDependencies in package.json and ensure the parser/plugin is imported as a module object in eslint.config.cjs (e.g., `parser: require("@typescript-eslint/parser")`).
- After making changes, run `npm ci` (in CI) or `npm install` locally, then `npm run lint` to validate.

If you are unsure which approach to take when modifying ESLint, open an issue or tag a maintainer for review.