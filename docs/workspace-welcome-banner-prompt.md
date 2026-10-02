# Workspace welcome banner — image generation prompt

Save the generated image as `frontend/public/images/workspace/welcome-banner-blue.png`
(1800×700 recommended), then swap the CSS gradient in
`src/components/workspace/WelcomeDialog.css` for:
`background-image: url("/images/workspace/welcome-banner-blue.png")`.

## Prompt (paste into your image generator)

> Soft abstract gradient banner background, wide rounded rectangle, perfectly smooth and seamless — deep Elseview blue theme: blend of periwinkle blue (#8b9cf0), sky blue (#a9c6f7), pale ice blue (#c9d8f5) with subtle warm peach (#f6c9a8) and soft pink (#f9a8c8) clouds drifting across the middle, dreamy mesh-gradient style, gentle grain texture overlay, airy and premium SaaS onboarding aesthetic, no text, no logos, no people, no objects, no shadows, flat even lighting, ultra clean, high resolution, 3:1 landscape aspect ratio

## Negative prompt

> text, letters, words, logos, watermarks, people, faces, hands, objects, icons, buttons, borders, frames, sharp edges, dark vignette, noise artifacts, pixelation, low resolution

## Notes

- Keep the title "Welcome to Elseview" as HTML text on top (not baked into the image) so EN/FR copy stays crisp.
- If the generator supports it: `style: mesh gradient, soft grain, pastel SaaS banner --ar 3:1 --v 6`.