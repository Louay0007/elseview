import { ArrowUpRight } from "lucide-react";

export function AnnouncementBar() {
  return (
    <aside className="relative z-30 border-b border-black/[0.06] bg-white/80 px-5 py-2.5 text-carbon backdrop-blur-2xl">
      <div className="mx-auto flex max-w-page items-center justify-center gap-3 text-center text-[13px] font-medium tracking-[-0.01em]">
        <span>Bluecrest now speaks the language of spatial interfaces.</span>
        <a href="#components" className="bluecrest-focus inline-flex items-center gap-1 rounded-full bg-black/[0.06] px-3 py-1.5 text-xs font-semibold text-signal-blue transition hover:bg-black/[0.1]">
          Explore <ArrowUpRight className="h-3 w-3" />
        </a>
      </div>
    </aside>
  );
}
