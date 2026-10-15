export const colors = {
  // Brand & Accents
  deepCaramel: '#9A6330',
  warmCaramel: '#C9955A',

  // Surfaces & Backgrounds
  softNeutral: '#F5F6F8',
  surfaceWhite: '#FFFFFF',

  // Content & Typography
  charcoal: '#242424',
  mutedGray: '#686868',

  // Borders & Dividers
  borderNeutral: '#E8E2D9',
  borderInput: '#D4C8BE',
  borderFocus: '#9A6330',

  // Semantic Feedback States
  errorText: '#C62828',
  errorBg: '#FDECEA',
  errorBorder: '#F5C6CB',

  successText: '#2E7D32',
  successBg: '#E8F5E9',
  successBorder: '#C8E6C9',

  warningText: '#92400E',
  warningBg: '#FFFBEB',
  warningBorder: '#FDE68A',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 20,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const radii = {
  sm: 6,
  control: 8,
  button: 10,
  pill: 10,
  card: 16,
} as const;

export const typography = {
  title: { fontSize: 32, fontWeight: '700' as const, letterSpacing: 0.5 },
  headline: { fontSize: 18, fontWeight: '700' as const },
  subhead: { fontSize: 15, fontWeight: '400' as const, lineHeight: 22 },
  body: { fontSize: 15, fontWeight: '400' as const, lineHeight: 20 },
  label: { fontSize: 13, fontWeight: '600' as const },
  button: { fontSize: 16, fontWeight: '600' as const },
  caption: { fontSize: 13, fontWeight: '400' as const, lineHeight: 18 },
} as const;

export const shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  tabActive: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 2,
  },
} as const;

export type Colors = typeof colors;
export type Spacing = typeof spacing;
export type Radii = typeof radii;
export type Typography = typeof typography;
export type Shadows = typeof shadows;
