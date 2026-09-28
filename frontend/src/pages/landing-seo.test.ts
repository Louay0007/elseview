import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const read = (path: string) => readFileSync(resolve(process.cwd(), path), "utf8");
const title = "Elseview — User Research &amp; AI-Powered Testing";
const description = "See beyond assumptions with Elseview. Explore user research, usability testing, and AI-assisted analysis to turn better questions into clearer product decisions.";

describe("landing SEO", () => {
  it("provides consistent search and social copy before JavaScript runs", () => {
    const html = read("index.html");
    expect(html).toContain(`<title>${title}</title>`);
    expect(html).toContain(`property="og:title" content="${title}"`);
    expect(html).toContain(`name="twitter:title" content="${title}"`);
    expect(html.match(new RegExp(description.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g"))).toHaveLength(3);
    expect(read("src/pages/Index.tsx")).toContain(description);
    expect(read("src/pages/Index.tsx")).toContain(title.replace("&amp;", "&"));
  });

  it("describes Elseview without inventing contact, location, or rating claims", () => {
    const html = read("index.html");
    const script = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
    expect(script).not.toBeNull();
    expect(JSON.parse(script![1])).toEqual({
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "Elseview",
      description: "User research and AI-powered testing for clearer product decisions.",
    });
    expect(JSON.parse(read("public/site.webmanifest")).short_name).toBe("Elseview");
  });

  it("does not direct search crawlers to the previous brand's domain", () => {
    for (const path of ["index.html", "public/robots.txt", "public/sitemap.xml", "public/site.webmanifest", "src/pages/Index.tsx"]) {
      expect(read(path)).not.toContain("mediterra.care");
    }
    expect(read("index.html")).not.toContain('rel="canonical"');
    expect(read("public/sitemap.xml")).not.toContain("<loc>");
  });

  it("uses the Elseview logo for browser and installed-app icons", () => {
    const html = read("index.html");
    const manifest = JSON.parse(read("public/site.webmanifest"));
    const browserIcons = [...html.matchAll(/<link rel="(?:icon|apple-touch-icon)"[^>]*href="([^"]+)"/g)].map((match) => match[1]);
    expect(browserIcons).toEqual([
      "/images/brand/elseview-favicon.png",
      "/images/brand/elseview-apple-touch-icon.png",
    ]);
    expect(manifest.icons.map((icon: { sizes: string }) => icon.sizes)).toEqual(["192x192", "512x512"]);
    for (const path of [...browserIcons, ...manifest.icons.map((icon: { src: string }) => icon.src)]) {
      expect(path).toContain("/images/brand/elseview-");
      expect(existsSync(resolve(process.cwd(), "public", path.slice(1)))).toBe(true);
    }
  });

  it("keeps social-preview image references resolvable", () => {
    const html = read("index.html");
    const image = html.match(/property="og:image" content="([^"]+)"/);
    expect(image).not.toBeNull();
    expect(existsSync(resolve(process.cwd(), "public", image![1].slice(1)))).toBe(true);
    expect(html).toContain(`name="twitter:image" content="${image![1]}"`);
  });
});
