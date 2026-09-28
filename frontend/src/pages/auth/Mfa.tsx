import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, RefreshCw, ShieldCheck } from "lucide-react";
import { REGEXP_ONLY_DIGITS } from "input-otp";
import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { useAuthSession } from "@/components/auth/AuthSession";

type MfaLocationState = { email?: string; setup?: boolean } | null;

export default function MfaPage() {
  const navigate = useNavigate();
  const { completeSession } = useAuthSession();
  const { state } = useLocation();
  const authState = state as MfaLocationState;
  const [code, setCode] = useState("");
  const [seconds, setSeconds] = useState(30);

  useEffect(() => {
    const timer = window.setInterval(() => setSeconds((value) => (value <= 1 ? 30 : value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (code.length === 6) { completeSession(); navigate("/", { replace: true }); }
  };

  return (
    <AuthShell eyebrow="Authenticator verification" title={authState?.setup ? "Secure your account." : "Confirm it’s you."} description="Open your authenticator app and enter the current code for Elseview.">
      <form onSubmit={submit} className="space-y-6">
        <div className="rounded-2xl border border-[#dfe9f5] bg-[#f7fbff] p-5">
          <div className="flex items-center gap-3"><span className="flex size-10 items-center justify-center rounded-full bg-[#0a84ff] text-white"><ShieldCheck className="size-5" aria-hidden="true" /></span><div><p className="text-[14px] font-semibold text-[#202124]">6-digit authenticator code</p>{authState?.email && <p className="mt-0.5 text-[12px] text-[#747981]">Account: {authState.email}</p>}</div></div>
          <InputOTP value={code} onChange={setCode} maxLength={6} pattern={REGEXP_ONLY_DIGITS} containerClassName="mt-6 justify-center" aria-label="Six-digit authenticator code" autoFocus>
            <InputOTPGroup>{Array.from({ length: 6 }, (_, index) => <InputOTPSlot key={index} index={index} className="h-12 w-11 bg-white text-base sm:w-12" />)}</InputOTPGroup>
          </InputOTP>
          <div className="mt-5 flex items-center justify-center gap-2 text-[12px] text-[#747981]"><RefreshCw className="size-3.5" aria-hidden="true" /><span className="tabular-nums">A new code appears every {seconds} seconds</span></div>
        </div>

        <div className="rounded-xl border border-[#eceef1] px-4 py-3 text-[13px] leading-relaxed text-[#686b70]">Codes are generated only by authenticator apps such as Google Authenticator. Elseview does not send OTP codes through SMS or email.</div>

        <Button type="submit" disabled={code.length !== 6} className="h-12 w-full rounded-xl bg-[#07172f] text-white hover:bg-[#0a2d5c]">Verify and continue <ArrowRight className="size-4" aria-hidden="true" /></Button>
        <p className="text-center text-[14px] text-[#747981]">Having trouble? <Link to="/auth/login" className="font-semibold text-[#0a84ff] hover:underline">Return to sign in</Link></p>
      </form>
    </AuthShell>
  );
}
