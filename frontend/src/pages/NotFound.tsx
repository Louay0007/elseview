import { useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";
import { Home, ArrowLeft } from "lucide-react";

const NotFound = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { text } = useOptionalAuthLocale();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname,
    );
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white px-6">
      <div className="w-full max-w-md text-center">
        {/* 404 number */}
        <p className="text-[140px] font-black leading-none tracking-[-0.04em] text-black">404</p>
        
        {/* Heading */}
        <h1 className="mt-6 text-[28px] font-bold tracking-[-0.02em] text-black">
          {text({ en: "Page not found", fr: "Page introuvable" })}
        </h1>
        
        {/* Description */}
        <p className="mt-3 text-[16px] leading-relaxed text-[#6d6d70]">
          {text({ 
            en: "The page you're looking for doesn't exist or has been moved.", 
            fr: "La page que vous recherchez n'existe pas ou a été déplacée." 
          })}
        </p>
        
        {/* Actions */}
        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-full border border-[#18181b] px-6 text-[15px] font-medium text-black transition-colors hover:bg-[#f7f8fa] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
          >
            <ArrowLeft className="size-[18px]" strokeWidth={1.6} aria-hidden="true" />
            {text({ en: "Go back", fr: "Retour" })}
          </button>
          
          <button
            onClick={() => navigate("/dashboard?role=researcher")}
            className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-full bg-[#1d4ed8] px-6 text-[15px] font-medium text-white transition-colors hover:bg-[#1e40af] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
          >
            <Home className="size-[18px]" strokeWidth={1.6} aria-hidden="true" />
            {text({ en: "Go to dashboard", fr: "Tableau de bord" })}
          </button>
        </div>
        
        {/* Path indicator */}
        <div className="mt-12 rounded-xl border border-[#e8e8ec] bg-[#fafafa] px-4 py-3">
          <p className="truncate text-[13px] text-[#6d6d70]">
            <span className="font-medium text-[#52525b]">{text({ en: "Requested:", fr: "Demandé :" })}</span>{" "}
            {location.pathname}
          </p>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
