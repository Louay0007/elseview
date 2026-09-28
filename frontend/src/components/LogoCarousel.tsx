import { useState } from "react";
import { Pause, Play } from "lucide-react";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";
import "./LogoCarousel.css";

const rows = [
  [
    { name: "First Abu Dhabi Bank", file: "fab" },
    { name: "FinFlx", file: "finflx" },
    { name: "Mashreq", file: "mashreq" },
    { name: "CAFU", file: "cafu" },
    { name: "The Giving Movement", file: "giving-movement" },
    { name: "Banque Saudi Fransi", file: "bsf" },
    { name: "Property Finder", file: "property-finder" },
  ],
  [
    { name: "PwC", file: "pwc" },
    { name: "RAKBANK", file: "rakbank" },
    { name: "AW Rostamani", file: "aw-rostamani" },
    { name: "Majid Al Futtaim", file: "majid-al-futtaim" },
    { name: "ADGM", file: "adgm" },
    { name: "QIC Digital Venture Partners", file: "qic" },
  ],
];

export function LogoCarousel() {
  const [paused, setPaused] = useState(false);
  const { text } = useOptionalAuthLocale();

  return (
    <section className="brand-showcase overflow-hidden bg-white" aria-labelledby="partners-heading">
      <h2 id="partners-heading">{text({ en: "Trusted by leading brands", fr: "La confiance des grandes marques" })}</h2>
      <div className="brand-showcase__rows" data-paused={paused}>
        {rows.map((brands, rowIndex) => (
          <div className="brand-showcase__row overflow-hidden" key={rowIndex}>
            <div className="brand-showcase__track" style={{ animationDirection: rowIndex ? "reverse" : "normal" }}>
              {[0, 1].map((copy) => (
                <div className="brand-showcase__sequence" key={copy} aria-hidden={copy === 1 ? true : undefined}>
                  {brands.map((brand) => (
                    <div className="brand-showcase__logo" key={brand.file}>
                      <img src={`/images/partners/mena/${brand.file}.jpg`} alt={copy === 0 ? brand.name : ""} width="280" height="160" loading="lazy" decoding="async" />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="brand-showcase__caption">
        <button type="button" className="brand-showcase__toggle" onClick={() => setPaused(!paused)} aria-label={text(paused ? { en: "Play logo scrolling", fr: "Reprendre le défilement des logos" } : { en: "Pause logo scrolling", fr: "Mettre en pause le défilement des logos" })} title={text(paused ? { en: "Play logo scrolling", fr: "Reprendre le défilement des logos" } : { en: "Pause logo scrolling", fr: "Mettre en pause le défilement des logos" })}>
          {paused ? <Play size={16} aria-hidden="true" /> : <Pause size={16} aria-hidden="true" />}
        </button>
      </div>
    </section>
  );
}
