// ESLint 扁平配置：TS + Vue 3 + 可访问性 + 分层限制
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import vue from "eslint-plugin-vue";
import vueA11y from "eslint-plugin-vuejs-accessibility";

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs["flat/recommended"],
  vueA11y.configs["flat/recommended"],
  {
    files: ["**/*.{ts,vue}"],
    rules: {
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "vue/component-api-style": ["error", ["script-setup"]],
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
