import js from '@eslint/js';
import typescript from '@typescript-eslint/eslint-plugin';
import typescriptParser from '@typescript-eslint/parser';

export default [
  js.configs.recommended,
  {
    files: ['src/**/*.ts'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
      },
      globals: {
        // Add common Node.js and browser globals
        RequestInit: 'readonly',
        Express: 'readonly',
        Request: 'readonly',
        Response: 'readonly',
        NextFunction: 'readonly',
      },
    },
    plugins: {
      '@typescript-eslint': typescript,
    },
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
  },
  {
    ignores: ['dist/', 'node_modules/', '*.js'],
  },
];
