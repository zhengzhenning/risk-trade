// ESLint 扁平配置：TS + Vue 3 + 可访问性 + 分层限制
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import vue from "eslint-plugin-vue";
import vueA11y from "eslint-plugin-vuejs-accessibility";
import vueParser from "vue-eslint-parser";
import tsParser from "@typescript-eslint/parser";

const flat = (config) => (Array.isArray(config) ? config : [config]);

export default [
  ...flat(js.configs.recommended),
  ...flat(tseslint.configs.recommended),
  ...flat(vue.configs["flat/recommended"]),
  ...flat(vueA11y.configs["flat/recommended"]),
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: { parser: tsParser, sourceType: "module", extraFileExtensions: [".vue"] },
    },
  },
  {
    files: ["**/*.{ts,vue}"],
    rules: {
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "vue/component-api-style": ["error", ["script-setup"]],
      "vue/multi-word-component-names": "off",
      "vue/max-attributes-per-line": "off",
      "vue/singleline-html-element-content-newline": "off",
      "vue/block-order": ["error", { order: ["script", "template", "style"] }],
    },
  },
  {
    files: ["packages/core/**/*.ts"],
    rules: {
      "no-restricted-imports": ["error", { paths: ["vue", "uni-app"] }],
    },
  },
  { ignores: ["**/dist/**", "**/node_modules/**"] },
];
