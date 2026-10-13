import test from 'node:test';
import assert from 'node:assert';
import {
  colors,
  spacing,
  radii,
  typography,
  shadows,
} from '../src/theme/tokens.ts';

// Dynamic WCAG 2.1 relative luminance and contrast calculations
function getRelativeLuminance(hex) {
  const clean = hex.replace('#', '');
  const r = parseInt(clean.substring(0, 2), 16) / 255;
  const g = parseInt(clean.substring(2, 4), 16) / 255;
  const b = parseInt(clean.substring(4, 6), 16) / 255;
  const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

function getContrastRatio(hex1, hex2) {
  const l1 = getRelativeLuminance(hex1);
  const l2 = getRelativeLuminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

test('theme color tokens conform to 6-digit hex format', () => {
  const hexPattern = /^#[0-9A-Fa-f]{6}$/;
  for (const [key, value] of Object.entries(colors)) {
    assert.match(
      value,
      hexPattern,
      `Color token "${key}" value "${value}" must be a valid 6-digit hex code`
    );
  }
});

test('normal text pairings meet or exceed WCAG 2.1 AA 4.5:1 threshold', () => {
  const normalTextPairs = [
    {
      name: 'Primary Button Label (white on deep caramel)',
      fg: colors.surfaceWhite,
      bg: colors.deepCaramel,
    },
    {
      name: 'Primary Form Text on Card (charcoal on white)',
      fg: colors.charcoal,
      bg: colors.surfaceWhite,
    },
    {
      name: 'Primary Canvas Text (charcoal on soft neutral)',
      fg: colors.charcoal,
      bg: colors.softNeutral,
    },
    {
      name: 'Supporting Text on Card (muted gray on white)',
      fg: colors.mutedGray,
      bg: colors.surfaceWhite,
    },
    {
      name: 'Inactive Tab Text on Switcher Track (muted gray on soft neutral)',
      fg: colors.mutedGray,
      bg: colors.softNeutral,
    },
    {
      name: 'Active Tab Text on Active Tab Pill (charcoal on white)',
      fg: colors.charcoal,
      bg: colors.surfaceWhite,
    },
    {
      name: 'Error Banner Text (error crimson on error background)',
      fg: colors.errorText,
      bg: colors.errorBg,
    },
    {
      name: 'Success Banner Text (success green on success background)',
      fg: colors.successText,
      bg: colors.successBg,
    },
  ];

  for (const pair of normalTextPairs) {
    const ratio = getContrastRatio(pair.fg, pair.bg);
    assert.ok(
      ratio >= 4.5,
      `Expected ${pair.name} contrast (${ratio.toFixed(2)}:1) to meet or exceed 4.5:1`
    );
  }
});

test('large text pairings meet or exceed WCAG 2.1 AA 3.0:1 threshold', () => {
  const largeTextPairs = [
    {
      name: 'Brand Title on Canvas (deep caramel on soft neutral)',
      fg: colors.deepCaramel,
      bg: colors.softNeutral,
    },
  ];

  for (const pair of largeTextPairs) {
    const ratio = getContrastRatio(pair.fg, pair.bg);
    assert.ok(
      ratio >= 3.0,
      `Expected ${pair.name} contrast (${ratio.toFixed(2)}:1) to meet or exceed 3.0:1`
    );
  }
});

test('non-text UI indicator pairings meet or exceed WCAG 2.1 AA 3.0:1 threshold', () => {
  const nonTextPairs = [
    {
      name: 'Focused Input Outline on White Card (borderFocus on white)',
      fg: colors.borderFocus,
      bg: colors.surfaceWhite,
    },
    {
      name: 'Primary Button Boundary on Canvas (deep caramel on soft neutral)',
      fg: colors.deepCaramel,
      bg: colors.softNeutral,
    },
    {
      name: 'Warm Caramel Accent with Dark Text (charcoal on warm caramel)',
      fg: colors.charcoal,
      bg: colors.warmCaramel,
    },
  ];

  for (const pair of nonTextPairs) {
    const ratio = getContrastRatio(pair.fg, pair.bg);
    assert.ok(
      ratio >= 3.0,
      `Expected ${pair.name} contrast (${ratio.toFixed(2)}:1) to meet or exceed 3.0:1`
    );
  }
});

test('warm caramel guardrail: white on warm caramel fails 4.5:1 (confirming warm caramel must never be used with white text)', () => {
  const ratio = getContrastRatio(colors.surfaceWhite, colors.warmCaramel);
  assert.ok(
    ratio < 3.0,
    `White on warm caramel contrast (${ratio.toFixed(2)}:1) should be below 3.0:1, confirming dark text is required`
  );
});

test('spacing scale has monotonically increasing 4-point rhythm', () => {
  const values = [
    spacing.xs,
    spacing.sm,
    spacing.md,
    spacing.base,
    spacing.lg,
    spacing.xl,
    spacing.xxl,
    spacing.xxxl,
  ];

  for (let i = 0; i < values.length; i++) {
    assert.strictEqual(
      values[i] % 4,
      0,
      `Spacing value ${values[i]} at index ${i} must adhere to 4-point grid`
    );
    if (i > 0) {
      assert.ok(
        values[i] > values[i - 1],
        `Spacing value ${values[i]} must be strictly greater than previous value ${values[i - 1]}`
      );
    }
  }
});

test('typography and radii tokens define expected structures', () => {
  assert.strictEqual(typeof radii.button, 'number');
  assert.strictEqual(typeof radii.card, 'number');
  assert.strictEqual(typeof radii.pill, 'number');
  assert.strictEqual(typeof radii.control, 'number');

  assert.strictEqual(typeof typography.title.fontSize, 'number');
  assert.strictEqual(typeof typography.headline.fontSize, 'number');
  assert.strictEqual(typeof typography.body.fontSize, 'number');
  assert.strictEqual(typeof typography.label.fontSize, 'number');
  assert.strictEqual(typeof typography.button.fontSize, 'number');

  assert.strictEqual(typeof shadows.card.shadowOpacity, 'number');
  assert.strictEqual(typeof shadows.tabActive.shadowOpacity, 'number');
});

test('touch targets guarantee minimum 48-unit height across interactive controls', async () => {
  const fs = await import('node:fs');
  const authPath = new URL('../src/components/AuthScreen.tsx', import.meta.url);
  const appPath = new URL('../App.tsx', import.meta.url);
  const authCode = fs.readFileSync(authPath, 'utf8');
  const appCode = fs.readFileSync(appPath, 'utf8');

  // Verify AuthScreen touch target constraints
  const tabMatch = authCode.match(/tab:\s*{[^}]*minHeight:\s*(\d+)/s);
  assert.ok(tabMatch, 'tab must specify minHeight');
  assert.ok(Number(tabMatch[1]) >= 48, `tab minHeight (${tabMatch[1]}) must be >= 48`);

  const inputMatch = authCode.match(/input:\s*{[^}]*minHeight:\s*(\d+)/s);
  assert.ok(inputMatch, 'input must specify minHeight');
  assert.ok(Number(inputMatch[1]) >= 48, `input minHeight (${inputMatch[1]}) must be >= 48`);

  const submitMatch = authCode.match(/submitButton:\s*{[^}]*minHeight:\s*(\d+)/s);
  assert.ok(submitMatch, 'submitButton must specify minHeight');
  assert.ok(Number(submitMatch[1]) >= 48, `submitButton minHeight (${submitMatch[1]}) must be >= 48`);

  // Verify App.tsx restoration action button constraints
  const signOutMatch = appCode.match(/signOutButton:\s*{[^}]*minHeight:\s*(\d+)/s);
  assert.ok(signOutMatch, 'signOutButton must specify minHeight');
  assert.ok(Number(signOutMatch[1]) >= 48, `signOutButton minHeight (${signOutMatch[1]}) must be >= 48`);

  const retryMatch = appCode.match(/retryButton:\s*{[^}]*minHeight:\s*(\d+)/s);
  assert.ok(retryMatch, 'retryButton must specify minHeight');
  assert.ok(Number(retryMatch[1]) >= 48, `retryButton minHeight (${retryMatch[1]}) must be >= 48`);
});

test('AuthScreen contentContainer specifies responsive maxWidth of 420 pt', async () => {
  const fs = await import('node:fs');
  const authPath = new URL('../src/components/AuthScreen.tsx', import.meta.url);
  const authCode = fs.readFileSync(authPath, 'utf8');

  const containerMatch = authCode.match(/contentContainer:\s*{[^}]*maxWidth:\s*(\d+)/s);
  assert.ok(containerMatch, 'contentContainer must specify maxWidth');
  assert.strictEqual(Number(containerMatch[1]), 420, 'contentContainer maxWidth must be 420');
});

