import { ArrowRight } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";
import { authRoute, routes } from "@/lib/routes";

interface RoleSelectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RoleSelectionDialog({ open, onOpenChange }: RoleSelectionDialogProps) {
  const { text } = useOptionalAuthLocale();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[688px] gap-0 overflow-hidden rounded-[24px] border-0 bg-white p-0 shadow-2xl">
        <div className="grid md:grid-cols-2">
          <section className="border-carbon/10 p-7 sm:p-9 md:border-r">
            <DialogTitle className="text-[25px] font-semibold tracking-[-0.04em] text-carbon">
              {text({ en: "I’m a", fr: "Je suis" })} <span className="text-[#183a68]">{text({ en: "researcher", fr: "chercheur" })}</span>
            </DialogTitle>
            <DialogDescription className="mt-3 max-w-[250px] text-[14px] leading-[1.55] text-carbon/75">
              {text({ en: "I want to use Elseview to publish tests and get results.", fr: "Je veux utiliser Elseview pour publier des tests et obtenir des résultats." })}
            </DialogDescription>
            <div className="mt-7 flex flex-wrap items-center gap-5">
              <Button asChild className="h-11 rounded-full bg-black px-6 text-[13px] hover:bg-carbon">
                <a href={authRoute("login", "researcher")}>{text({ en: "Sign in", fr: "Se connecter" })}</a>
              </Button>
              <a
                href={authRoute("signup", "researcher")}
                className="inline-flex min-h-11 items-center gap-1 text-[13px] font-semibold text-[#273665] transition-colors hover:text-[#183a68]"
              >
                {text({ en: "Create an account", fr: "Créer un compte" })} <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
              </a>
            </div>
          </section>

          <section className="p-7 sm:p-9">
            <DialogTitle className="text-[25px] font-semibold tracking-[-0.04em] text-carbon">
              {text({ en: "I’m a", fr: "Je suis" })} <span className="text-[#183a68]">{text({ en: "tester", fr: "testeur" })}</span>
            </DialogTitle>
            <DialogDescription className="mt-3 max-w-[250px] text-[14px] leading-[1.55] text-carbon/75">
              {text({ en: "I want to use Elseview to take tests and get paid.", fr: "Je veux utiliser Elseview pour participer à des tests et être rémunéré." })}
            </DialogDescription>
            <div className="mt-7 flex flex-wrap items-center gap-5">
              <Button asChild className="h-11 rounded-full bg-black px-6 text-[13px] hover:bg-carbon">
                <a href={authRoute("login", "tester")}>{text({ en: "Sign in", fr: "Se connecter" })}</a>
              </Button>
              <a
                href={authRoute("signup", "tester")}
                className="inline-flex min-h-11 items-center gap-1 text-[13px] font-semibold text-[#273665] transition-colors hover:text-[#183a68]"
              >
                {text({ en: "Create an account", fr: "Créer un compte" })} <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
              </a>
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
