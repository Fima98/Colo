import { FlatCompat } from "@eslint/eslintrc";
import js from "@eslint/js";
import path from "node:path";
import { fileURLToPath } from "node:url";

import parserTypescript from "@typescript-eslint/parser";
import pluginTypescript from "@typescript-eslint/eslint-plugin";
import pluginReactHooks from "eslint-plugin-react-hooks";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: js.configs.recommended,
  allConfig: js.configs.all,
});

export default [
  ...compat.extends("standard", "next/core-web-vitals", "next/typescript", "prettier"),

  {
    languageOptions: {
      parser: parserTypescript,
    },
    plugins: {
      "@typescript-eslint": pluginTypescript,
      "react-hooks": pluginReactHooks,
    },
    rules: {
      "no-undef": "off",
      camelcase: "off",
      "@typescript-eslint/no-require-imports": "off",
      "react-hooks/exhaustive-deps": "off",
      "import/order": [
        "error",
        {
          groups: ["builtin", "external", "internal", ["parent", "sibling"], "index", "object"],
          "newlines-between": "never",
          pathGroups: [{ pattern: "@app/**", group: "external", position: "after" }],
          pathGroupsExcludedImportTypes: ["builtin"],
          alphabetize: { order: "asc", caseInsensitive: true },
        },
      ],
    },
  },
];
