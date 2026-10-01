import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'src/api/schema.d.ts'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Native dialogs read as out-of-app interruptions; use an in-app two-step
      // confirm (admin: kit/ConfirmButton; learner routes: an in-file pattern).
      'no-restricted-globals': ['error', { name: 'confirm', message: 'Use an in-app two-step confirmation, not the native confirm dialog.' }],
      'no-restricted-properties': ['error', { object: 'window', property: 'confirm', message: 'Use an in-app two-step confirmation, not window.confirm.' }],
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Every API call is typed against the generated schema (src/api/schema.d.ts); a double cast
      // through `unknown` is how the old rawRequest hatch hid a path/verb/param typo from tsc.
      'no-restricted-syntax': [
        'error',
        {
          selector: "TSAsExpression > TSAsExpression[typeAnnotation.type='TSUnknownKeyword']",
          message: 'No `as unknown as` casts: type the call against the generated schema instead.',
        },
      ],
    },
  },
)
