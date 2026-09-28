import { useState } from "react";
import { BadgeDollarSign, ChevronDown, Info, LifeBuoy } from "lucide-react";
import { useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { PUBLISHING_FEE_CREDITS, panelCredits } from "@/lib/pricing";

type OrderSidebarProps = {
  participants: number;
  panelLabel: string;
  speed: number;
  feesOpen?: boolean;
};

export function OrderSidebar({ participants, panelLabel, speed, feesOpen = false }: OrderSidebarProps) {
  const nav = useWorkspaceNav();
  const [open, setOpen] = useState(feesOpen);
  const panel = panelCredits(participants);
  const total = panel;

  return (
    <aside aria-label="Order summary" className="h-fit rounded-2xl border border-[#e4e4e7] bg-white p-5 lg:sticky lg:top-6">
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-bold text-black">Estimated panel size</h2>
        <span className="grid size-6 place-items-center text-[#8e8e93]"><Info className="size-4" strokeWidth={1.6} aria-hidden="true" /></span>
      </div>
      <p className="mt-2 text-[40px] font-bold leading-none tracking-tight text-black">{panelLabel}</p>
      <div className="mt-3" aria-hidden="true">
        <div className="h-1.5 overflow-hidden rounded-full bg-gradient-to-r from-[#e11d48] via-[#f59e0b] to-[#16a34a]"><div className="h-full rounded-full bg-black/70" style={{ width: `${speed}%` }} /></div>
        <div className="mt-1.5 flex justify-between text-[11.5px] font-medium text-[#6d6d70]"><span>Slow responses</span><span>Fast responses</span></div>
      </div>

      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="order-test-fees"
        className="mt-4 flex w-full items-center justify-between rounded-xl bg-[#f7f7f8] px-4 py-3 text-left text-[14px] font-medium text-black hover:bg-[#efeff1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
        <span className="flex items-center gap-2"><BadgeDollarSign className="size-4" strokeWidth={1.6} aria-hidden="true" />Test fees</span>
        <ChevronDown className={`size-4 text-[#6d6d70] transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>
      {open && (
        <dl id="order-test-fees" className="mt-2 divide-y divide-[#f0f0f2] rounded-xl border border-[#f0f0f2] px-4 text-[13.5px]">
          <div className="flex items-center justify-between gap-3 py-2.5">
            <dt className="text-[#3a3a3c]">Test publishing fee</dt>
            <dd className="flex items-center gap-1.5 font-semibold text-black">
              <span className="rounded bg-[#eef6ee] px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-[#1d5c1d]">Free</span>
              <s className="font-normal text-[#8e8e93]">{PUBLISHING_FEE_CREDITS} credits</s>
            </dd>
          </div>
          <div className="flex items-center justify-between gap-3 py-2.5">
            <dt className="text-[#3a3a3c]">{participants} {participants === 1 ? "participant" : "participants"} - Elseview panel</dt>
            <dd className="font-semibold text-black">{panel} credits</dd>
          </div>
        </dl>
      )}

      <h3 className="mt-5 text-[14px] font-bold text-black">Order Summary</h3>
      <dl className="mt-2 divide-y divide-[#f0f0f2] text-[13.5px]">
        <div className="flex items-center justify-between py-2.5"><dt className="text-[#3a3a3c]">Total credits required</dt><dd className="font-semibold text-black">{total} credits</dd></div>
        <div className="flex items-center justify-between py-2.5"><dt className="text-[#3a3a3c]">Available in your wallet</dt><dd className="font-semibold text-black">0 credits</dd></div>
        <div className="flex items-center justify-between py-2.5"><dt className="text-[#3a3a3c]">Order total</dt><dd className="font-semibold text-black">{total} credits</dd></div>
      </dl>
      <div className="mt-2 flex items-center justify-between rounded-xl bg-[#f7f7f8] px-4 py-3">
        <span className="text-[15px] font-bold text-black">Payment Total</span>
        <span className="text-[20px] font-bold text-black">${total}</span>
      </div>
      <p className="mt-3 text-center text-[12.5px] text-[#6d6d70]">Save up to 20% when you <button type="button" onClick={() => nav.goWithParams("/workspace/credits/buy")} className="font-semibold text-[#1d4ed8] underline underline-offset-2">buy in bulk</button></p>
      <button type="button" onClick={() => nav.goWithParams("/support")} className="mt-4 flex w-full items-center justify-center gap-2 rounded-full border border-[#e4e4e7] px-4 py-2.5 text-[13.5px] font-medium text-[#18181b] hover:bg-[#f7f7f8]">
        <LifeBuoy className="size-4" strokeWidth={1.6} aria-hidden="true" />Support
      </button>
    </aside>
  );
}
