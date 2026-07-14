import type { ReactNode } from 'react';

interface SectionHeaderProps {
  groupName: string;
  hasVisible: boolean;
  children: ReactNode;
}

export default function SectionHeader({
  groupName,
  hasVisible,
  children,
}: SectionHeaderProps) {
  if (!groupName || !hasVisible) return null;
  return <>{children}</>;
}
