import { Menu } from "lucide-react";
import { BluecrestButton } from "./BluecrestButton";

export function TopNavigation() {
  return (
    <nav className="absolute inset-x-0 top-4 z-20 text-white" aria-label="Main navigation">
      <div className="bluecrest-container liquid-glass-dark flex h-[64px] items-center justify-between rounded-full px-4 sm:px-5">
        <a href="#top" className="bluecrest-focus rounded-full px-2 text-[19px] font-semibold tracking-[-0.035em]">Bluecrest</a>
        <BluecrestButton size="sm" className="hidden bg-white text-signal-blue shadow-[inset_0_1px_0_rgba(255,255,255,.8),0_8px_20px_rgba(0,30,90,.15)] hover:bg-white sm:inline-flex" onClick={() => document.querySelector("#preview")?.scrollIntoView({ behavior: "smooth", block: "center" })}>View preview</BluecrestButton>
        <a className="bluecrest-focus rounded-full bg-white/15 p-2.5 sm:hidden" aria-label="Jump to preview" href="#preview"><Menu className="h-5 w-5" /></a>
      </div>
    </nav>
  );
}
