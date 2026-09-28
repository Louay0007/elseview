import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Copy, Download, ShieldCheck } from "lucide-react";
import { REGEXP_ONLY_DIGITS } from "input-otp";
import { QRCodeSVG } from "qrcode.react";
import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { useAuthSession } from "@/components/auth/AuthSession";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";

const setupKey = "JBSW Y3DP EHPK 3PXP";
const recoveryCodes = ["MTR-84PL-2K9D", "MTR-73QX-8H2C", "MTR-91NV-4A6F", "MTR-26TK-7W3B", "MTR-58RC-1Y9M", "MTR-40JD-6P8S"];

export default function MfaEnrollmentPage() {
  const navigate = useNavigate();
  const { completeSession } = useAuthSession();
  const [code, setCode] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [copied, setCopied] = useState<"key" | "codes" | null>(null);
  const [downloaded, setDownloaded] = useState(false);

  const copy = async (value: string, type: "key" | "codes") => {
    await navigator.clipboard.writeText(value);
    setCopied(type);
    window.setTimeout(() => setCopied(null), 1800);
  };

  const download = () => {
    const blob = new Blob([`Elseview recovery codes\n\n${recoveryCodes.join("\n")}\n`], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "elseview-recovery-codes.txt";
    anchor.click();
    URL.revokeObjectURL(url);
    setDownloaded(true);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (code.length === 6) setConfirmed(true);
  };

  if (confirmed) {
    return (
      <AuthShell wide eyebrow="Keep these somewhere safe" title="Save your recovery codes." description="Each code can help you sign in once if you lose access to your authenticator app. They are shown only now.">
        <div className="rounded-2xl border border-[#dfe5ec] bg-[#f8fafc] p-5 sm:p-6">
          <div className="grid grid-cols-2 gap-3 font-mono text-[14px] text-[#202124] sm:grid-cols-3">{recoveryCodes.map((item) => <span key={item} className="rounded-lg bg-white px-3 py-2.5 text-center ring-1 ring-[#e3e7eb]">{item}</span>)}</div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2"><Button variant="outline" type="button" className="h-11 rounded-xl" onClick={() => copy(recoveryCodes.join("\n"), "codes")}>{copied === "codes" ? <Check /> : <Copy />}{copied === "codes" ? "Copied" : "Copy codes"}</Button><Button variant="outline" type="button" className="h-11 rounded-xl" onClick={download}>{downloaded ? <Check /> : <Download />}{downloaded ? "Downloaded" : "Download codes"}</Button></div>
        </div>
        <Button type="button" onClick={() => { completeSession(); navigate("/", { replace: true }); }} className="mt-5 h-12 w-full rounded-xl bg-[#07172f] text-base text-white hover:bg-[#0a2d5c]">I saved my recovery codes</Button>
      </AuthShell>
    );
  }

  return (
    <AuthShell wide eyebrow="Protect your account" title="Set up your authenticator app." description="Your authenticator app creates a new sign-in code every 30 seconds, even when your phone is offline.">
      <form onSubmit={submit} className="space-y-6">
        <div className="grid items-center gap-6 rounded-2xl border border-[#dfe5ec] p-5 sm:grid-cols-[180px_1fr] sm:p-6">
          <div className="mx-auto rounded-2xl border border-[#e1e6eb] bg-white p-3"><QRCodeSVG value={`otpauth://totp/Elseview:account?secret=${setupKey.split(" ").join("")}&issuer=Elseview`} size={152} fgColor="#07172f" level="M" /></div>
          <div><h2 className="text-[18px] font-semibold text-[#202124]">Scan the QR code</h2><p className="mt-2 text-[14px] leading-relaxed text-[#60656d]">In Google Authenticator or another authenticator app, add an account and scan this code.</p><div className="mt-4"><p className="text-[12px] font-medium text-[#60656d]">Can’t scan it? Enter this setup key:</p><div className="mt-2 flex items-center gap-2"><code className="min-w-0 flex-1 rounded-lg bg-[#f3f6f9] px-3 py-2.5 text-center text-[13px] font-semibold tracking-[0.12em] text-[#07172f]">{setupKey}</code><Button type="button" variant="outline" size="icon" className="size-11 shrink-0 rounded-xl" onClick={() => copy(setupKey.split(" ").join(""), "key")} aria-label="Copy setup key">{copied === "key" ? <Check /> : <Copy />}</Button></div><span className="sr-only" aria-live="polite">{copied === "key" ? "Setup key copied" : ""}</span></div></div>
        </div>

        <div className="text-center"><span className="mx-auto flex size-10 items-center justify-center rounded-full bg-[#eaf4ff] text-[#0a67c7]"><ShieldCheck className="size-5" aria-hidden="true" /></span><h2 className="mt-3 text-[17px] font-semibold text-[#202124]">Enter the code you see</h2><InputOTP value={code} onChange={setCode} maxLength={6} pattern={REGEXP_ONLY_DIGITS} containerClassName="mt-4 justify-center" aria-label="Six-digit authenticator code"><InputOTPGroup>{Array.from({ length: 6 }, (_, index) => <InputOTPSlot key={index} index={index} className="h-12 w-11 bg-white text-base sm:w-12" />)}</InputOTPGroup></InputOTP></div>
        <Button type="submit" disabled={code.length !== 6} className="h-12 w-full rounded-xl bg-[#07172f] text-base text-white hover:bg-[#0a2d5c]">Finish setup</Button>
      </form>
    </AuthShell>
  );
}
