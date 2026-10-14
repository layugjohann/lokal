import { colors } from './tokens.ts';

export const SUPPORTED_ICON_NAMES = [
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
] as const;

export type IconName = (typeof SUPPORTED_ICON_NAMES)[number];

export interface IconConfig {
  componentName: string;
  defaultColor: string;
  defaultSize: number;
  description: string;
}

export const iconMapping: Record<IconName, IconConfig> = {
  close: {
    componentName: 'X',
    defaultColor: colors.charcoal,
    defaultSize: 20,
    description: 'Dismiss modals, sheets, and active search input',
  },
  community: {
    componentName: 'Users',
    defaultColor: colors.charcoal,
    defaultSize: 18,
    description: 'Community feed entry and discussion threads',
  },
  profile: {
    componentName: 'User',
    defaultColor: colors.charcoal,
    defaultSize: 18,
    description: 'User profile, saved collections, and account management',
  },
  location: {
    componentName: 'MapPin',
    defaultColor: colors.deepCaramel,
    defaultSize: 16,
    description: 'Geographic location, distance indicator, and shop address',
  },
  sparkles: {
    componentName: 'Sparkles',
    defaultColor: colors.warmCaramel,
    defaultSize: 16,
    description: 'AI-generated synthesis, summary highlight, and smart recommendation',
  },
  coffee: {
    componentName: 'Coffee',
    defaultColor: colors.deepCaramel,
    defaultSize: 16,
    description: 'Must-try drink badge, roast specialty, and coffee shop category',
  },
  heart: {
    componentName: 'Heart',
    defaultColor: colors.deepCaramel,
    defaultSize: 22,
    description: 'Favorite toggle for saving and bookmarking coffee shops',
  },
  share: {
    componentName: 'Share2',
    defaultColor: colors.charcoal,
    defaultSize: 20,
    description: 'Native share trigger for coffee shops and community recommendations',
  },
  edit: {
    componentName: 'Pencil',
    defaultColor: colors.deepCaramel,
    defaultSize: 16,
    description: 'Shop owner dashboard edit action for coffee shop details',
  },
  verified: {
    componentName: 'CircleCheck',
    defaultColor: colors.successText,
    defaultSize: 16,
    description: 'Owner verification status and verified shop badge',
  },
  pending: {
    componentName: 'Clock',
    defaultColor: colors.warningText,
    defaultSize: 16,
    description: 'Pending claim review status banner',
  },
  rejected: {
    componentName: 'CircleX',
    defaultColor: colors.errorText,
    defaultSize: 16,
    description: 'Rejected claim status indicator',
  },
  document: {
    componentName: 'FileText',
    defaultColor: colors.mutedGray,
    defaultSize: 20,
    description: 'Empty state illustration and document review count',
  },
  star: {
    componentName: 'Star',
    defaultColor: colors.deepCaramel,
    defaultSize: 24,
    description: 'Interactive review rating star picker and rating display',
  },
};

export const iconButtonDimensions = {
  minWidth: 48,
  minHeight: 48,
  justifyContent: 'center' as const,
  alignItems: 'center' as const,
};

export const semanticIconColors = {
  favoriteActive: colors.deepCaramel,
  favoriteInactive: colors.mutedGray,
  starActive: colors.deepCaramel,
  starInactive: colors.mutedGray,
  statusVerified: colors.successText,
  statusPending: colors.warningText,
  statusRejected: colors.errorText,
} as const;

export function getIconAccessibilityProps(options?: {
  isInteractive?: boolean;
  label?: string;
}) {
  if (options?.isInteractive) {
    return {
      accessible: true,
      accessibilityRole: 'button' as const,
      accessibilityLabel: options.label,
    };
  }
  return {
    accessible: false,
    importantForAccessibility: 'no' as const,
    accessibilityElementsHidden: true,
  };
}
