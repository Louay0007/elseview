import { User } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { cn } from "@/lib/utils";

type WelcomeDialogProps = {
  open: boolean;
  workspaceName: string;
  onGoToDashboard: () => void;
};

export function WelcomeDialog({ open, workspaceName, onGoToDashboard }: WelcomeDialogProps) {
  const { text } = useAuthLocale();
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-dialog-title"
    >
      <div className="w-full max-w-[760px] rounded-[28px] bg-white p-4 shadow-2xl sm:p-5">
        <div
          className={cn(
            "welcome-banner flex min-h-[190px] items-center justify-center rounded-[20px] px-6 py-12 text-center sm:min-h-[210px]",
          )}
          aria-hidden="true"
        >
          <p className="text-[30px] font-bold tracking-[-0.02em] text-white sm:text-[36px]">
            {text({ en: "Welcome to Elseview", fr: "Bienvenue sur Elseview" })}
          </p>
        </div>

        <div className="px-4 pb-6 pt-6 text-center sm:px-10">
          <div className="mx-auto flex w-fit max-w-full items-center gap-4 rounded-[16px] bg-[#f5f5f6] px-5 py-4 text-left">
            <span className="grid size-[60px] shrink-0 place-items-center rounded-[14px] bg-black text-white">
              <User className="size-6" strokeWidth={1.8} aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[19px] font-medium text-black">{workspaceName}</span>
              <span className="mt-1 block text-[15px] text-[#6d6d70]">
                {text({ en: "Individual workspace", fr: "Espace de travail individuel" })}
              </span>
            </span>
          </div>

          <p className="mx-auto mt-7 max-w-[560px] text-[17px] leading-[1.65] text-[#6d6d70]">
            {text({
              en: "You can start running tests straight away. Remember, you only need to pay for what you use, and there are no publishing fees for the first 30 days.",
              fr: "Vous pouvez lancer des tests immédiatement. Vous ne payez que ce que vous utilisez, sans frais de publication pendant les 30 premiers jours.",
            })}
          </p>

          <button
            id="welcome-dialog-title"
            type="button"
            onClick={onGoToDashboard}
            autoFocus
            className="mx-auto mt-7 flex min-h-[58px] items-center justify-center rounded-full bg-black px-12 text-[19px] font-medium text-white transition-colors hover:bg-[#1a1a1a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-4"
          >
            {text({ en: "Go to dashboard", fr: "Accéder au tableau de bord" })}
          </button>

          <p className="mt-6">
            <a
              href="/dashboard"
              onClick={(event) => {
                event.preventDefault();
                onGoToDashboard();
              }}
              className="text-[15px] text-[#1d4ed8] underline underline-offset-2 hover:text-[#1e40af]"
            >
              {text({
                en: "Upgrade to Team plan for instant collaboration",
                fr: "Passez au forfait Équipe pour collaborer instantanément",
              })}
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
