import { useState, type SyntheticEvent } from "react";
import styles from "./MediterraCareRelay.module.css";

const chapters = [
  { title: "Find the real question", body: "Start where certainty ends: an untested idea, a confusing moment, or a user need you want to understand." },
  { title: "Give curiosity a plan", body: "Choose who to learn from, what to ask, and the evidence that would change your mind." },
  { title: "Look from another angle", body: "Explore sample tasks and simulated findings to see how AI-assisted testing could challenge your first take." },
  { title: "Question the takeaway", body: "Look beyond the neat summary. Review sample observations, consider other explanations, and flag what needs proof." },
  { title: "Make the next test count", body: "Take your strongest open question back to real participants. Let what you learn shape what comes next." },
];

const assets = {
  landscape: { src: "/images/care-relay/mediterranean-landscape.png", file: "mediterranean-landscape.png", width: 1600, height: 1200 },
  clinic: { src: "/images/care-relay/local-clinic.png", file: "local-clinic.png", width: 768, height: 768 },
  documents: { src: "/images/care-relay/case-documents.png", file: "case-documents.png", width: 1024, height: 768 },
  specialist: { src: "/images/care-relay/specialist-node.png", file: "specialist-node.png", width: 768, height: 768 },
  outcome: { src: "/images/care-relay/outcome-loop.png", file: "outcome-loop.png", width: 768, height: 768 },
};

type AssetKey = keyof typeof assets;

function RelayAsset({ name, className, eager = false }: { name: AssetKey; className: string; eager?: boolean }) {
  const asset = assets[name];
  const [missing, setMissing] = useState(false);
  const handleError = (event: SyntheticEvent<HTMLImageElement>) => {
    event.currentTarget.style.display = "none";
    setMissing(true);
  };

  return (
    <div className={`${styles.asset} ${className}`} data-layer={name} aria-hidden="true">
      {!missing && (
        <img
          src={asset.src}
          width={asset.width}
          height={asset.height}
          alt=""
          className={styles.imageFade}
          loading={eager ? "eager" : "lazy"}
          onError={handleError}
        />
      )}
      {missing && (
        <div className={styles.fallback}>
          <strong>Illustration unavailable</strong>
          <span>{asset.width} × {asset.height}px</span>
        </div>
      )}
    </div>
  );
}

function RelayVisual({ mobile = false }: { mobile?: boolean }) {
  return (
    <div className={`${styles.visual} ${mobile ? styles.mobileVisual : styles.desktopVisual}`} role="img" aria-label="Illustrative research journey from a question to a study, findings, and a next step. Medical imagery is decorative, not an Elseview service.">
      <RelayAsset name="landscape" className={styles.landscape} eager />
      <svg className={styles.route} viewBox="0 0 1600 1200" aria-hidden="true">
        <path className={styles.routeBase} pathLength="1" d="M210 930 C360 795 445 760 590 700 C790 615 840 310 1190 270 C1370 250 1360 510 1165 650 C1005 765 980 930 1100 1010" />
        <path className={styles.routeActive} pathLength="1" d="M210 930 C360 795 445 760 590 700 C790 615 840 310 1190 270 C1370 250 1360 510 1165 650 C1005 765 980 930 1100 1010" />
        <circle className={styles.signalDot} cx="1100" cy="1010" r="11" />
      </svg>
      <RelayAsset name="clinic" className={styles.clinic} />
      <RelayAsset name="documents" className={styles.documents} />
      <div className={`${styles.asset} ${styles.specialist}`} data-layer="specialist" aria-hidden="true">
        <span data-halo className={styles.halo} />
        <RelayAsset name="specialist" className="!inset-0 !h-full !w-full" />
      </div>
      <RelayAsset name="outcome" className={styles.outcome} />
      <svg data-confirmation className={styles.confirmation} viewBox="0 0 34 34" aria-hidden="true">
        <circle cx="17" cy="17" r="15" />
        <path d="m10.5 17 4.2 4.2 8.8-9" />
      </svg>
    </div>
  );
}

export function MediterraCareRelay() {
  return (
    <section className={styles.section} aria-labelledby="care-relay-heading">
      <div className={styles.pinnedStage}>
        <div className={styles.container}>
          <div className={styles.grid}>
            <div>
              <p className={styles.eyebrow}>Follow your curiosity</p>
              <h2 id="care-relay-heading" className={styles.heading}>Big ideas start with better questions.</h2>
              <p className={styles.intro}>Follow an idea from the first “what if?” to a focused research plan. Explore the journey with sample data, not results from a live study.</p>
            </div>
            <RelayVisual />
          </div>

          <div className={styles.storyArea}>
            <div className={styles.chapterStack}>
              {chapters.map((chapter, index) => (
                <article key={chapter.title} className={styles.chapter}>
                  <span className={styles.chapterNumber}>0{index + 1}</span>
                  <h3>{chapter.title}</h3>
                  <p>{chapter.body}</p>
                </article>
              ))}
            </div>
            <div className={styles.ctaRow}>
              <a className={styles.cta} href="#future-content">Explore research principles</a>
            </div>
          </div>

          <div className={styles.mobileStories}>
            {chapters.map((chapter, index) => (
              <article key={chapter.title} className={styles.mobileChapter}>
                <div className={styles.mobileCopy}>
                  <span className={styles.chapterNumber}>0{index + 1}</span>
                  <h3>{chapter.title}</h3>
                  <p>{chapter.body}</p>
                </div>
                <RelayVisual mobile />
              </article>
            ))}
          </div>
          <div className={styles.mobileCtaRow}>
            <a className={`${styles.cta} ${styles.mobileCta}`} href="#future-content">Explore research principles</a>
          </div>
        </div>
      </div>
    </section>
  );
}
