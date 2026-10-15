import React from 'react';
import { View, StyleProp, ViewStyle } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';
import { colors } from '../theme/tokens';

export interface LokalLogoProps {
  size?: number;
  style?: StyleProp<ViewStyle>;
  color?: string;
  accentColor?: string;
  accessible?: boolean;
  accessibilityLabel?: string;
}

export const LokalLogo: React.FC<LokalLogoProps> = ({
  size = 36,
  style,
  color = colors.deepCaramel,
  accentColor = colors.warmCaramel,
  accessible = false,
  accessibilityLabel = 'LOKAL brand logo',
}) => {
  return (
    <View
      style={style}
      accessible={accessible}
      accessibilityRole={accessible ? 'image' : undefined}
      accessibilityLabel={accessible ? accessibilityLabel : undefined}
      importantForAccessibility={accessible ? 'yes' : 'no-hide-descendants'}
      accessibilityElementsHidden={!accessible}
    >
      <Svg
        width={size}
        height={size}
        viewBox="0 0 72 72"
        fill="none"
        accessible={false}
        importantForAccessibility="no-hide-descendants"
        accessibilityElementsHidden={true}
      >
        {/* Cup Outline */}
        <Path
          d="M14 30 C14 62 50 62 50 30 Z"
          stroke={color}
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Cup Rim */}
        <Path
          d="M10 30 L54 30"
          stroke={color}
          strokeWidth="3.5"
          strokeLinecap="round"
        />
        {/* Cup Handle */}
        <Path
          d="M50 36 C58 36 63 41 63 47 C63 53 57 56 49 56"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
        />
        {/* Cup Saucer Base */}
        <Path
          d="M19 66 L45 66"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
        />
        {/* Rising Steam Arc */}
        <Path
          d="M25 22 C25 17 31 14 31 9"
          stroke={accentColor}
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        {/* AI Steam Spark (4-point sparkle) */}
        <Path
          d="M40 9 C40 13 44 15 46 15 C44 15 40 17 40 21 C40 17 36 15 34 15 C36 15 40 13 40 9 Z"
          fill={accentColor}
        />
        {/* Subtle Steam Dot */}
        <Circle cx="21" cy="8" r="1.5" fill={accentColor} />
      </Svg>
    </View>
  );
};

export default LokalLogo;
