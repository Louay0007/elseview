import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Mail } from "lucide-react";
import { AuthShell } from "@/components/auth/AuthShell";
import { fieldClassName, labelClassName } from "@/components/auth/AuthFields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function RecoverPage() {
  const [sent, setSent] = useState(false);
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setSent(true); };

  return (
    <AuthShell eyebrow="Account recovery" title="Reset your password." description="Enter your verified work email. Recovery instructions are separate from authenticator codes.">
      {sent ? (
        <div className="rounded-2xl border border-[#cce3fb] bg-[#f3f9ff] p-6 text-center"><CheckCircle2 className="mx-auto size-8 text-[#0a84ff]" aria-hidden="true" /><h2 className="mt-4 text-lg font-semibold text-[#18181b]">Check your email</h2><p className="mt-2 text-sm leading-relaxed text-[#686b70]">If that address belongs to an active Elseview account, password recovery instructions are on their way.</p><Button asChild className="mt-6 h-11 rounded-xl bg-[#07172f] text-white"><Link to="/auth/login">Return to sign in</Link></Button></div>
      ) : (
        <form onSubmit={submit} className="space-y-5"><div><Label className={labelClassName} htmlFor="recovery-email">Work email</Label><div className="relative mt-2"><Input id="recovery-email" name="email" type="email" required autoComplete="email" placeholder="you@organization.com" className={`${fieldClassName} pl-10`} /><Mail className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-[#92969d]" aria-hidden="true" /></div></div><Button type="submit" className="h-12 w-full rounded-xl bg-[#07172f] text-white hover:bg-[#0a2d5c]">Send recovery instructions <ArrowRight className="size-4" aria-hidden="true" /></Button><p className="text-center text-[14px] text-[#747981]"><Link to="/auth/login" className="font-semibold text-[#0a84ff] hover:underline">Back to sign in</Link></p></form>
      )}
    </AuthShell>
  );
}
