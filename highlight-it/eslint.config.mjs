import globals from "globals";
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.worker,
      },
      ecmaVersion: 12,
      sourceType: "module"
    },
    rules: {
      "no-undef": "error",
      "no-redeclare": "warn",
      "no-unused-vars": "warn"
    },
    files: ["src/**/*.js", "src/**/*.jsx"],
    ignores: ["dist/**", "node_modules/**"],
  },
  {
    files: ["**/*.ts", "**/*.d.ts"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: "./tsconfig.json"
      },
      globals: {
        ...globals.browser,
        ...globals.worker,
      }
    },
    plugins: {
      "@typescript-eslint": tseslint.plugin
    },
    rules: {
      "@typescript-eslint/no-unused-vars": "warn"
    }
  },
  {
    languageOptions: {
      globals: {
        ...globals.node,
      },
      ecmaVersion: 12,
      sourceType: "commonjs"
    },
    rules: {
      // Disable some rules for Node.js environment
      "no-undef": "error",
      "no-restricted-syntax": "off",
      "import/no-commonjs": "off",
      "import/no-require": "off",
      "@typescript-eslint/no-require-imports": "off"
    },
    files: ["build.js"],
  },
  // Ignore dist files completely
  {
    ignores: ["dist/**"]
  }
]; 