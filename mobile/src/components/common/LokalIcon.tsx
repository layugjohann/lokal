import React from 'react';
import { StyleProp, ViewStyle, View } from 'react-native';
import {
  X,
  Users,
  User,
  MapPin,
  Sparkles,
  Coffee,
  Heart,
  Share2,
  Pencil,
  CircleCheck,
  Clock,
  CircleX,
  FileText,
  Star,
  LucideIcon,
} from 'lucide-react-native';
import {
  IconName,
  iconMapping,
  getIconAccessibilityProps,
} from '../../theme/icons';

const ICON_COMPONENTS: Record<IconName, LucideIcon> = {
  close: X,
  community: Users,
  profile: User,
  location: MapPin,
  sparkles: Sparkles,
  coffee: Coffee,
  heart: Heart,
  share: Share2,
  edit: Pencil,
  verified: CircleCheck,
  pending: Clock,
  rejected: CircleX,
  document: FileText,
  star: Star,
};

export interface LokalIconProps {
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
  fill?: string;
  style?: StyleProp<ViewStyle>;
}

export const LokalIcon: React.FC<LokalIconProps> = ({
  name,
  size,
  color,
  strokeWidth = 2,
  fill,
  style,
}) => {
  const IconComponent = ICON_COMPONENTS[name];
  const config = iconMapping[name];

  if (!IconComponent) {
    return null;
  }

  const iconColor = color || config.defaultColor;
  const iconSize = size ?? config.defaultSize;
  const accessibilityProps = getIconAccessibilityProps();

  return (
    <View style={style} {...accessibilityProps}>
      <IconComponent
        size={iconSize}
        color={iconColor}
        strokeWidth={strokeWidth}
        fill={fill ?? 'none'}
      />
    </View>
  );
};

export default LokalIcon;
