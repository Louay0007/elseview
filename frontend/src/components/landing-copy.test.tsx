import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { LogoCarousel } from "./LogoCarousel";
import { MediterraBrandStatement } from "./MediterraBrandStatement";
import { MediterraCareRelay } from "./MediterraCareRelay";
import { MediterraFaq } from "./MediterraFaq";
import { MediterraFooter } from "./MediterraFooter";
import { MediterraMinimalistHero } from "./MediterraMinimalistHero";
import { MediterraLogo } from "./MediterraLogo";
import { MediterraAnimatedNetwork } from "./MediterraAnimatedNetwork";
import { WorkflowSection } from "./WorkflowSection";
import TestimonialMarquee from "./ui/marquee-01";
import SmoothScroll from "./ui/smooth-scroll";

const state = vi.hoisted(() => ({ submitted: false }));
vi.mock("react", async (importOriginal) => {
  const react = await importOriginal<typeof import("react")>();
  return {
    ...react,
    useState: (initial: unknown) => react.useState(state.submitted && initial === false ? true : initial),
  };
});

const components = [
  LogoCarousel, MediterraBrandStatement, MediterraCareRelay, MediterraFaq,
  MediterraFooter, MediterraMinimalistHero, MediterraAnimatedNetwork,
  WorkflowSection, TestimonialMarquee, SmoothScroll,
];
const render = (component: (typeof components)[number]) => renderToStaticMarkup(createElement(component));
const readableCopy = (html: string) => html
  .replace(/<[^>]*>/g, " ")
  .replace(/\s+/g, " ");

describe("Elseview landing copy", () => {
  it("rebrands every rendered section without retaining medical service claims", () => {
    const html = components.map(render).join(" ");
    expect(readableCopy(html)).not.toMatch(/Mediterra|clinical|care network|trusted specialist|patient need/i);
    expect(html).not.toMatch(/(?:aria-label|alt)="[^"]*Mediterra/i);
    expect(readableCopy(html)).toContain("Elseview");
    // Legacy anchors and image paths deliberately stay intact.
    expect(html).toContain('id="about-mediterra"');
    expect(html).toContain("/images/hero/elseview-research-session.png");
    expect(html).toContain('width="1536" height="2304"');
    expect(html).toContain('alt="Illustrative user research session:');
  });

  it("uses the supplied Elseview mark across every brand placement", () => {
    for (const component of [MediterraMinimalistHero, MediterraFooter, MediterraBrandStatement, MediterraAnimatedNetwork]) {
      const html = render(component);
      expect(html).toContain('src="/images/brand/elseview-logo.png"');
      expect(html).not.toContain("/images/brand/mediterra-");
    }
    const compact = renderToStaticMarkup(createElement(MediterraLogo, { compact: true }));
    expect(compact).toContain('alt="Elseview"');
    expect(compact).not.toContain('aria-hidden="true"');
    const full = renderToStaticMarkup(createElement(MediterraLogo));
    expect(full).toContain('src="/images/brand/elseview-logo.png"');
    expect(readableCopy(full)).toContain("Elseview");
  });

  it("uses the role-selection CTA without a workspace preview", () => {
    const html = render(MediterraMinimalistHero);
    expect(html.match(/Get started for free/g)).toHaveLength(2);
    expect(html).toContain('type="button"');
    expect(html).not.toContain('href="/app');
    expect(readableCopy(html)).toContain("Landing &amp; authentication preview");
    expect(readableCopy(html)).toContain("AI-powered testing");
  });

  it("shows the confirmed brand heading while keeping scenarios illustrative", () => {
    const logos = readableCopy(render(LogoCarousel));
    expect(logos).toContain("Trusted by leading brands");
    expect(logos).not.toContain("No affiliation or endorsement");
    expect(readableCopy(render(MediterraFaq))).toContain("Do the displayed logos indicate available integrations?");
    const scenarios = render(TestimonialMarquee);
    expect(readableCopy(scenarios)).toContain("not customer testimonials");
    expect(readableCopy(scenarios)).toContain("Portraits are decorative");
    expect(scenarios).toContain('aria-label="Illustrative research scenario: First impressions"');
    expect(scenarios).not.toMatch(/@kmasters|@kathrun|nearly doubled|countless hours|Testimonial from/);
  });

  it("uses research icons for shortcuts and research principles", () => {
    const hero = render(MediterraMinimalistHero);
    for (const icon of ["clipboard-list", "message-circle-question", "compass"]) {
      expect(hero).toContain(`lucide-${icon}`);
    }
    expect(hero).toContain('title="Explore research use cases"');
    const principles = render(SmoothScroll);
    for (const icon of ["search", "flask-conical", "file-search", "iteration-cw"]) {
      expect(principles).toContain(`lucide-${icon}`);
    }
    expect(hero + principles).not.toMatch(/lucide-(heart-pulse|heart-handshake|map-pinned|network)/);
  });

  it("explains simulated findings and the need for human validation", () => {
    const html = render(SmoothScroll);
    expect(readableCopy(html)).toContain("not evidence of what real users think");
    expect(readableCopy(html)).toContain("AI-generated signals need human validation");
    expect(readableCopy(render(MediterraCareRelay))).toContain("not results from a live study");
  });

  it("does not promise an email subscription before or after demo submission", () => {
    const initial = render(MediterraFooter);
    expect(readableCopy(initial)).toContain("Demo form only. No subscription or email delivery.");
    expect(initial).not.toContain("mailto:");
    expect(initial).toContain('href="#faq"');
    state.submitted = true;
    try {
      const submitted = render(MediterraFooter);
      expect(readableCopy(submitted)).toContain("Your email was not saved or subscribed.");
      expect(readableCopy(submitted)).not.toMatch(/keep you informed|successfully subscribed/i);
    } finally {
      state.submitted = false;
    }
  });
});
