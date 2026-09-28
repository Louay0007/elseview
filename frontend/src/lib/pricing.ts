export const CREDITS_PER_PARTICIPANT = 4;
export const PUBLISHING_FEE_CREDITS = 29;

export function panelCredits(participants: number) {
  return Math.max(0, Math.round(participants)) * CREDITS_PER_PARTICIPANT;
}

export function totalCredits(participants: number) {
  return panelCredits(participants);
}

export function panelSizeLabel(size: number) {
  return size >= 1000 ? `~${(size / 1000).toFixed(1)}K` : `~${Math.round(size)}`;
}
