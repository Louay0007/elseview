import { useId } from "react";

export function VisaLogo({ className = "h-7 w-auto" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} role="img" aria-label="Visa">
      <path
        fill="currentColor"
        d="M9.112 8.262 5.97 15.758H3.92L2.374 9.775c-.094-.368-.175-.503-.461-.658C1.447 8.864.677 8.627 0 8.479l.046-.217h3.3a.904.904 0 0 1 .894.764l.817 4.338 2.018-5.102h2.037zm8.033 5.049c.008-1.979-2.736-2.088-2.717-2.972.006-.269.262-.555.822-.628a3.66 3.66 0 0 1 1.913.336l.34-1.59a5.207 5.207 0 0 0-1.814-.333c-1.917 0-3.266 1.02-3.278 2.479-.012 1.079.963 1.68 1.698 2.04.756.367 1.01.603 1.006.931-.005.504-.602.725-1.16.734-.975.015-1.54-.263-1.992-.473l-.351 1.642c.453.208 1.289.39 2.156.398 2.037 0 3.37-1.006 3.377-2.564m5.061 2.447H24l-1.565-7.496h-1.656a.883.883 0 0 0-.826.55l-2.909 6.946h2.036l.405-1.12h2.488l-.767 1.12zm-2.163-2.656 1.02-2.815.588 2.815h-1.608zm-8.16-4.84-1.603 7.496H8.34l1.605-7.496h1.938z"
      />
    </svg>
  );
}

export function MastercardLogo({ className = "h-7 w-auto" }: { className?: string }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const clipId = `mc-lens-${uid}`;
  const maskId = `mc-ring-${uid}`;
  return (
    <svg viewBox="0 0 36 22" className={className} role="img" aria-label="Mastercard">
      <defs>
        <clipPath id={clipId}>
          <circle cx="13" cy="11" r="8.5" />
        </clipPath>
        <mask id={maskId}>
          <rect x="0" y="0" width="36" height="22" fill="#fff" />
          <circle cx="13" cy="11" r="8.5" fill="#000" />
        </mask>
      </defs>
      <circle cx="13" cy="11" r="8.5" fill="#EB001B" />
      <circle cx="23" cy="11" r="8.5" fill="#F79E1B" mask={`url(#${maskId})`} />
      <g clipPath={`url(#${clipId})`}>
        <circle cx="23" cy="11" r="8.5" fill="#FF5F00" />
      </g>
    </svg>
  );
}
