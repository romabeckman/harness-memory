import parser from "@babel/eslint-parser";

export default [
  { ignores: ["node_modules/**", "dist/**", "coverage/**"] },
  {
    files: ["**/*.ts"],
    languageOptions: { parser, parserOptions: { sourceType: "module", requireConfigFile: false,
      babelOptions: { plugins: ["@babel/plugin-syntax-typescript"] } } },
    rules: { "no-unreachable": "error" },
  },
];
