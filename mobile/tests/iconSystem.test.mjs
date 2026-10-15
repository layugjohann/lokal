import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
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

test('getIconAccessibilityProps returns purely decorative accessibility contracts', () => {
  const decorativeProps = getIconAccessibilityProps();
  assert.strictEqual(decorativeProps.accessible, false);
  assert.strictEqual(decorativeProps.importantForAccessibility, 'no-hide-descendants');
  assert.strictEqual(decorativeProps.accessibilityElementsHidden, true);
});

test('LokalLogo implements platform-specific decorative and informative contracts', () => {
  const logoPath = new URL('../src/components/LokalLogo.tsx', import.meta.url);
  const content = fs.readFileSync(logoPath, 'utf8');

  // Verify default accessible = false
  assert.ok(/accessible\s*=\s*false/.test(content), 'accessible prop must default to false');
  // Verify importantForAccessibility ternary for Android
  assert.ok(
    /importantForAccessibility=\{accessible \? ['"]yes['"] : ['"]no-hide-descendants['"]\}/.test(
      content
    ),
    'importantForAccessibility must use no-hide-descendants when decorative'
  );
  // Verify accessibilityElementsHidden for iOS
  assert.ok(
    /accessibilityElementsHidden=\{!accessible\}/.test(content),
    'accessibilityElementsHidden must hide decorative logo from iOS VoiceOver'
  );
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

/**
 * Helper using the TypeScript parser to extract StyleSheet styles and JSX elements
 * with their exact attributes.
 */
function analyzeComponentAst(filePath) {
  const resolvedPath = filePath instanceof URL ? fileURLToPath(filePath) : filePath;
  const code = fs.readFileSync(resolvedPath, 'utf8');
  const sf = ts.createSourceFile(
    resolvedPath,
    code,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX
  );

  const styles = {};
  const jsxElements = [];

  function visit(node) {
    if (ts.isCallExpression(node)) {
      const expr = node.expression;
      if (ts.isPropertyAccessExpression(expr) && expr.name.text === 'create') {
        const arg = node.arguments[0];
        if (arg && ts.isObjectLiteralExpression(arg)) {
          for (const prop of arg.properties) {
            if (ts.isPropertyAssignment(prop)) {
              const styleName = prop.name.getText(sf).replace(/['"]/g, '');
              if (ts.isObjectLiteralExpression(prop.initializer)) {
                const rules = {};
                for (const rule of prop.initializer.properties) {
                  if (ts.isPropertyAssignment(rule)) {
                    const ruleName = rule.name.getText(sf).replace(/['"]/g, '');
                    const ruleVal = rule.initializer.getText(sf).replace(/['"]/g, '');
                    rules[ruleName] = ruleVal;
                  }
                }
                styles[styleName] = rules;
              }
            }
          }
        }
      }
    }

    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
      const attrs = {};
      for (const prop of node.attributes.properties) {
        if (ts.isJsxAttribute(prop)) {
          const attrName = prop.name.text;
          const attrVal = prop.initializer ? prop.initializer.getText(sf) : 'true';
          attrs[attrName] = attrVal;
        }
      }
      jsxElements.push({
        tagName: node.tagName.getText(sf),
        attrs,
      });
    }

    ts.forEachChild(node, visit);
  }

  visit(sf);
  return { styles, jsxElements };
}

test('in-scope TSX icon-only interactive controls enforce 48x48 bounds and accessibility labels via AST', () => {
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
        { styleName: 'starTouchTarget', expectedLabelPattern: /Rate.*star/i },
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
    const { styles, jsxElements } = analyzeComponentAst(filePath);

    for (const ctrl of comp.controls) {
      // 1. Verify exact style dimensions from AST
      const styleObj = styles[ctrl.styleName];
      assert.ok(
        styleObj,
        `Style definition for "${ctrl.styleName}" must exist in ${comp.file}`
      );

      const width = Number(styleObj.width || styleObj.minWidth);
      const height = Number(styleObj.height || styleObj.minHeight);

      assert.ok(
        !Number.isNaN(width) && width >= 48,
        `"${ctrl.styleName}" in ${comp.file} width (${width}) must be >= 48`
      );
      assert.ok(
        !Number.isNaN(height) && height >= 48,
        `"${ctrl.styleName}" in ${comp.file} height (${height}) must be >= 48`
      );

      // 2. Locate the EXACT JSX opening element that binds to this style
      const matchingJsx = jsxElements.find(
        (e) => e.attrs.style && e.attrs.style.includes(ctrl.styleName)
      );
      assert.ok(
        matchingJsx,
        `JSX element referencing "${ctrl.styleName}" must exist in ${comp.file}`
      );

      // 3. Verify accessibilityRole and accessibilityLabel on that SAME element
      assert.strictEqual(
        matchingJsx.attrs.accessibilityRole,
        '"button"',
        `JSX element referencing "${ctrl.styleName}" in ${comp.file} must declare accessibilityRole="button"`
      );
      assert.ok(
        ctrl.expectedLabelPattern.test(matchingJsx.attrs.accessibilityLabel),
        `JSX element referencing "${ctrl.styleName}" in ${comp.file} accessibilityLabel (${matchingJsx.attrs.accessibilityLabel}) must match ${ctrl.expectedLabelPattern}`
      );
    }
  }
});

test('starPickerRow specifies flexWrap: wrap and responsive spacing for narrow screen safety', () => {
  const shopCardPath = new URL('../src/components/ShopDetailCard.tsx', import.meta.url);
  const { styles } = analyzeComponentAst(shopCardPath);

  const pickerStyle = styles.starPickerRow;
  assert.ok(pickerStyle, 'starPickerRow style definition must exist');

  assert.strictEqual(
    pickerStyle.flexWrap,
    'wrap',
    'starPickerRow must specify flexWrap: "wrap" to prevent narrow viewport overflow'
  );
  assert.strictEqual(
    pickerStyle.justifyContent,
    'center',
    'starPickerRow must specify justifyContent: "center" for balanced alignment across rows'
  );
  assert.ok(
    Number(pickerStyle.rowGap) > 0,
    'starPickerRow must specify rowGap for clean vertical spacing when wrapped'
  );
  assert.ok(
    Number(pickerStyle.columnGap) > 0,
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
  const COLUMN_GAP = Number(pickerStyle.columnGap);
  const unwrapWidth = 5 * TARGET_SIZE + 4 * COLUMN_GAP; // 248pt

  // Confirm unwrap would have overflowed 232pt
  assert.ok(
    unwrapWidth > availableWidth,
    `Unwrapped width (${unwrapWidth}pt) exceeds available width (${availableWidth}pt)`
  );

  // Confirm that with wrapping, 4 stars fit on Row 1 (198pt <= 232pt) and 1 star on Row 2 (48pt <= 232pt)
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

test('CommunityFeedView shopName and shopAddress specify flexShrink: 1 to prevent row overflow', () => {
  const feedPath = new URL('../src/components/CommunityFeedView.tsx', import.meta.url);
  const { styles } = analyzeComponentAst(feedPath);

  assert.ok(styles.shopName, 'shopName style definition must exist');
  assert.strictEqual(
    Number(styles.shopName.flexShrink),
    1,
    'shopName in CommunityFeedView must specify flexShrink: 1'
  );

  assert.ok(styles.shopAddress, 'shopAddress style definition must exist');
  assert.strictEqual(
    Number(styles.shopAddress.flexShrink),
    1,
    'shopAddress in CommunityFeedView must specify flexShrink: 1'
  );
});
