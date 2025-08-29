module.exports = {
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
  },
  plugins: ['@typescript-eslint'],
  extends: [
    'eslint:recommended',
  ],
  rules: {
    // TypeScript specific rules
    '@typescript-eslint/no-unused-vars': 'error',
    '@typescript-eslint/no-explicit-any': 'warn',

    // General rules
    'no-console': 'off', // Turn off no-console since we have a logger function
    'no-debugger': 'error',
    'prefer-const': 'error',
    'no-var': 'error',
    'no-undef': 'off', // Turn off no-undef for TypeScript files
  },
  env: {
    node: true,
    es6: true,
  },
  globals: {
    // Add common Node.js and browser globals
    RequestInit: 'readonly',
    Express: 'readonly',
    Request: 'readonly',
    Response: 'readonly',
    NextFunction: 'readonly',
  },
  ignorePatterns: ['dist/', 'node_modules/', '*.js'],
};