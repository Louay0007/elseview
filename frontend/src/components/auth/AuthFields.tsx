import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useAuthLocale } from "@/components/auth/AuthLocale";

export function PasswordField({ id = "password", autoComplete = "current-password", placeholder = "", minLength = 12, hint, ...props }: InputHTMLAttributes<HTMLInputElement> & { hint?: string }) {
  const [visible, setVisible] = useState(false);
  const { text } = useAuthLocale();

  return (
    <div>
      <div className="relative">
      <Input id={id} name={id} required minLength={minLength} maxLength={256} autoComplete={autoComplete} type={visible ? "text" : "password"} placeholder={placeholder} aria-describedby={hint ? `${id}-hint` : undefined} {...props} className={`${fieldClassName} pe-12`} />
      <button type="button" onClick={() => setVisible((value) => !value)} aria-label={visible ? text({ en: "Hide password", fr: "Masquer le mot de passe" }) : text({ en: "Show password", fr: "Afficher le mot de passe" })} aria-pressed={visible} className="absolute end-1 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-[#7b7f86] hover:text-[#18181b] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
        {visible ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
      </button>
      </div>
      {hint && <p id={`${id}-hint`} className="mt-2 text-xs text-[#626870]">{hint}</p>}
    </div>
  );
}

export const fieldClassName = "h-12 rounded-lg border-[#969da7] bg-white px-3.5 text-base shadow-none focus-visible:ring-[#0a84ff] aria-[invalid=true]:border-[#b42318]";
export const labelClassName = "text-[13px] font-medium text-[#303238]";
