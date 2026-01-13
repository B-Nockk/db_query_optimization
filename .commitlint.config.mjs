// .commitlint.config.mjs
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // Optional custom rules — start simple, tighten later
    "type-enum": [2, "always", ["feat", "fix", "docs", "style", "refactor", "perf", "test", "chore", "ci", "revert"]],
    "subject-max-length": [2, "always", 72],
  },
}
