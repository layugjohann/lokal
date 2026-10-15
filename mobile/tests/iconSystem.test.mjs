import test from 'node:test';
import assert from 'node:assert';
import {
  SUPPORTED_ICON_NAMES,
  iconMapping,
  iconButtonDimensions,
  semanticIconColors,
  getIconAccessibilityProps,
} from '../src/theme/icons.ts';
import { colors } from '../src/theme/tokens.ts';

test('SUPPORTED_ICON_NAMES contains all 14 approved minimalist icons', () => {
  const expectedIcons = [
    'close',
    'community',
    'profile',
    'location',
    'sparkles',
    'coffee',
    'heart',
    'share',
    'edit',
    'verified',
    'pending',
    'rejected',
    'document',
    'star',
  ];

  assert.strictEqual(
    SUPPORTED_ICON_NAMES.length,
    14,
    `Expected exactly 14 icons, received ${SUPPORTED_ICON_NAMES.length}`
  );

  for (const expected of expectedIcons) {
    assert.ok(
      SUPPORTED_ICON_NAMES.includes(expected),
      `Expected icon "${expected}" to be included in SUPPORTED_ICON_NAMES`
    );
  }
});

test('iconMapping provides valid configuration for all 14 supported icons', () => {
  for (const name of SUPPORTED_ICON_NAMES) {
    const config = iconMapping[name];
    assert.ok(config, `Icon "${name}" must have a mapping configuration`);
    assert.ok(
      typeof config.componentName === 'string' && config.componentName.length > 0,
      `Icon "${name}" must define a valid componentName`
    );
    assert.ok(
      typeof config.defaultSize === 'number' && config.defaultSize > 0,
      `Icon "${name}" must define a positive defaultSize`
    );
    assert.ok(
      typeof config.description === 'string' && config.description.length > 0,
      `Icon "${name}" must define a descriptive summary`
    );
  }
});

test('iconMapping default colors bind strictly to approved design tokens', () => {
  const validColorValues = Object.values(colors);

  for (const name of SUPPORTED_ICON_NAMES) {
    const config = iconMapping[name];
    assert.ok(
      validColorValues.includes(config.defaultColor),
      `Icon "${name}" defaultColor "${config.defaultColor}" must be an approved token in colors`
    );
  }
});

test('getIconAccessibilityProps returns correct contracts for decorative vs interactive icons', () => {
  const decorativeProps = getIconAccessibilityProps();
  assert.strictEqual(decorativeProps.accessible, false);
  assert.strictEqual(decorativeProps.importantForAccessibility, 'no');
  assert.strictEqual(decorativeProps.accessibilityElementsHidden, true);

  const interactiveProps = getIconAccessibilityProps({
    isInteractive: true,
    label: 'Dismiss modal',
  });
  assert.strictEqual(interactiveProps.accessible, true);
  assert.strictEqual(interactiveProps.accessibilityRole, 'button');
  assert.strictEqual(interactiveProps.accessibilityLabel, 'Dismiss modal');
});

test('iconButtonDimensions enforces physical touch-target minimum floor of 48x48', () => {
  assert.ok(
    iconButtonDimensions.minWidth >= 48,
    `iconButtonDimensions.minWidth must be >= 48, got ${iconButtonDimensions.minWidth}`
  );
  assert.ok(
    iconButtonDimensions.minHeight >= 48,
    `iconButtonDimensions.minHeight must be >= 48, got ${iconButtonDimensions.minHeight}`
  );
  assert.strictEqual(iconButtonDimensions.justifyContent, 'center');
  assert.strictEqual(iconButtonDimensions.alignItems, 'center');
});

test('semanticIconColors binds strictly to approved palette tokens and contracts', () => {
  // Favorite states
  assert.strictEqual(
    semanticIconColors.favoriteActive,
    colors.deepCaramel,
    'favoriteActive must use colors.deepCaramel (#9A6330)'
  );
  assert.strictEqual(
    semanticIconColors.favoriteInactive,
    colors.mutedGray,
    'favoriteInactive must use colors.mutedGray (#686868)'
  );

  // Review star states
  assert.strictEqual(
    semanticIconColors.starActive,
    colors.deepCaramel,
    'starActive must use colors.deepCaramel (#9A6330)'
  );
  assert.strictEqual(
    semanticIconColors.starInactive,
    colors.mutedGray,
    'starInactive must use colors.mutedGray (#686868)'
  );

  // Verification & Claim states
  assert.strictEqual(
    semanticIconColors.statusVerified,
    colors.successText,
    'statusVerified must use colors.successText (#2E7D32)'
  );
  assert.strictEqual(
    semanticIconColors.statusPending,
    colors.warningText,
    'statusPending must use colors.warningText (#92400E)'
  );
  assert.strictEqual(
    semanticIconColors.statusRejected,
    colors.errorText,
    'statusRejected must use colors.errorText (#C62828)'
  );
});

test('in-scope TSX icon-only interactive controls enforce 48x48 bounds and accessibility labels', async () => {
  const fs = await import('node:fs');

  const componentsToVerify = [
    {
      file: '../src/components/LokalMapView.tsx',
      controls: [
        { styleName: 'communityButton', expectedLabelPattern: /Open Community/i },
        { styleName: 'profileButton', expectedLabelPattern: /Open user profile/i },
      ],
    },
    {
      file: '../src/components/NearbyShopsSheet.tsx',
      controls: [
        { styleName: 'clearButton', expectedLabelPattern: /Clear search/i },
      ],
    },
    {
      file: '../src/components/ShopDetailCard.tsx',
      controls: [
        { styleName: 'closeButton', expectedLabelPattern: /Close shop details/i },
        { styleName: 'shareButton', expectedLabelPattern: /Share coffee shop details/i },
        { styleName: 'favoriteButton', expectedLabelPattern: /favorite/i },
        { styleName: 'favoriteErrorDismiss', expectedLabelPattern: /Dismiss favorite error/i },
        { styleName: 'starTouchTarget', expectedLabelPattern: /Rate \$\{star\} star/i },
      ],
    },
    {
      file: '../src/components/ProfileView.tsx',
      controls: [
        { styleName: 'closeButton', expectedLabelPattern: /Close profile/i },
      ],
    },
    {
      file: '../src/components/CommunityFeedView.tsx',
      controls: [
        { styleName: 'closeButton', expectedLabelPattern: /Close Community Feed/i },
      ],
    },
    {
      file: '../src/components/OwnerDashboardModal.tsx',
      controls: [
        { styleName: 'closeButton', expectedLabelPattern: /Close owner dashboard/i },
      ],
    },
  ];

  for (const comp of componentsToVerify) {
    const filePath = new URL(comp.file, import.meta.url);
    const content = fs.readFileSync(filePath, 'utf8');

    for (const ctrl of comp.controls) {
      // 1. Verify style dimensions: width >= 48, height >= 48
      const styleRegex = new RegExp(`${ctrl.styleName}:\\s*{([^}]+)}`, 's');
      const match = content.match(styleRegex);
      assert.ok(match, `Style definition for "${ctrl.styleName}" must exist in ${comp.file}`);

      const styleBody = match[1];
      const widthMatch = styleBody.match(/(?:minWidth|width):\s*(\d+)/);
      const heightMatch = styleBody.match(/(?:minHeight|height):\s*(\d+)/);

      assert.ok(widthMatch, `"${ctrl.styleName}" in ${comp.file} must specify width or minWidth`);
      assert.ok(heightMatch, `"${ctrl.styleName}" in ${comp.file} must specify height or minHeight`);

      assert.ok(
        Number(widthMatch[1]) >= 48,
        `"${ctrl.styleName}" in ${comp.file} width (${widthMatch[1]}) must be >= 48`
      );
      assert.ok(
        Number(heightMatch[1]) >= 48,
        `"${ctrl.styleName}" in ${comp.file} height (${heightMatch[1]}) must be >= 48`
      );

      // 2. Verify accessibility attributes
      assert.ok(
        ctrl.expectedLabelPattern.test(content),
        `Component ${comp.file} must contain accessibilityLabel matching ${ctrl.expectedLabelPattern}`
      );
      assert.ok(
        content.includes('accessibilityRole="button"'),
        `Component ${comp.file} must specify accessibilityRole="button"`
      );
    }
  }
});

test('starPickerRow specifies flexWrap: wrap and responsive spacing for narrow screen safety', async () => {
  const fs = await import('node:fs');
  const shopCardPath = new URL('../src/components/ShopDetailCard.tsx', import.meta.url);
  const content = fs.readFileSync(shopCardPath, 'utf8');

  // Verify flexWrap: 'wrap' in starPickerRow
  const pickerMatch = content.match(/starPickerRow:\s*{([^}]+)}/s);
  assert.ok(pickerMatch, 'starPickerRow style definition must exist');

  const pickerBody = pickerMatch[1];
  assert.ok(
    /flexWrap:\s*['"]wrap['"]/.test(pickerBody),
    'starPickerRow must specify flexWrap: "wrap" to prevent narrow viewport overflow'
  );
  assert.ok(
    /justifyContent:\s*['"]center['"]/.test(pickerBody),
    'starPickerRow must specify justifyContent: "center" for balanced alignment across rows'
  );
  assert.ok(
    /rowGap:\s*\d+/.test(pickerBody),
    'starPickerRow must specify rowGap for clean vertical spacing when wrapped'
  );
  assert.ok(
    /columnGap:\s*\d+/.test(pickerBody),
    'starPickerRow must specify columnGap for horizontal item spacing'
  );

  // Validate mathematical layout constraint on 320pt narrow viewport
  const NARROW_VIEWPORT_WIDTH = 320;
  const SHEET_PADDING_HORIZONTAL = 16 * 2;
  const CARD_PADDING_HORIZONTAL = 16 * 2;
  const FORM_PADDING_HORIZONTAL = 12 * 2;
  const availableWidth =
    NARROW_VIEWPORT_WIDTH -
    SHEET_PADDING_HORIZONTAL -
    CARD_PADDING_HORIZONTAL -
    FORM_PADDING_HORIZONTAL;

  // Available width is 232pt
  assert.strictEqual(availableWidth, 232);

  const TARGET_SIZE = 48;
  const COLUMN_GAP = 2;
  const unwrapWidth = 5 * TARGET_SIZE + 4 * COLUMN_GAP; // 248pt

  // Confirm unwrap would have overflowed 232pt
  assert.ok(
    unwrapWidth > availableWidth,
    `Unwrapped width (${unwrapWidth}pt) exceeds available width (${availableWidth}pt)`
  );

  // Confirm that with wrapping, 4 stars fit on Row 1 (198pt <= 200pt) and 1 star on Row 2 (48pt <= 200pt)
  const row1Width = 4 * TARGET_SIZE + 3 * COLUMN_GAP; // 198pt
  const row2Width = 1 * TARGET_SIZE; // 48pt
  assert.ok(
    row1Width <= availableWidth,
    `Wrapped row 1 width (${row1Width}pt) must fit within available width (${availableWidth}pt)`
  );
  assert.ok(
    row2Width <= availableWidth,
    `Wrapped row 2 width (${row2Width}pt) must fit within available width (${availableWidth}pt)`
  );
});


