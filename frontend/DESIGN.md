---
name: A.I.G Pro
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#464555'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#767586'
  outline-variant: '#c7c4d7'
  surface-tint: '#4849da'
  primary: '#4343d5'
  on-primary: '#ffffff'
  primary-container: '#5d5fef'
  on-primary-container: '#faf7ff'
  inverse-primary: '#c1c1ff'
  secondary: '#5a5e68'
  on-secondary: '#ffffff'
  secondary-container: '#dfe2ee'
  on-secondary-container: '#60646e'
  tertiary: '#4345d1'
  on-tertiary: '#ffffff'
  tertiary-container: '#5d60eb'
  on-tertiary-container: '#faf6ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c1c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2e2bc2'
  secondary-fixed: '#dfe2ee'
  secondary-fixed-dim: '#c3c6d2'
  on-secondary-fixed: '#171c24'
  on-secondary-fixed-variant: '#434750'
  tertiary-fixed: '#e1e0ff'
  tertiary-fixed-dim: '#c0c1ff'
  on-tertiary-fixed: '#07006c'
  on-tertiary-fixed-variant: '#2f2ebe'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The brand personality is professional, authoritative, and forward-thinking, tailored for a high-tech security and AI-focused audience. It conveys a sense of "technological sophistication" through a clean, modern aesthetic that balances technical precision with user-friendly accessibility.

The design style is **Corporate Modern with subtle Glassmorphism**. It utilizes a light-mode default with high-clarity interfaces, featuring translucent background blurs on secondary elements to add depth without sacrificing performance or readability. The visual mood is calm yet energetic, achieved through vibrant indigo-purple accents set against expansive white and soft gray surfaces.

## Colors

The palette is anchored by a vibrant indigo (#5D5FEF), which serves as the primary action color and brand identifier. This is supported by a secondary soft blue-gray tint used for background surfaces and card containers to provide gentle contrast against pure white.

*   **Primary:** Used for main CTAs, active states, and brand-critical iconography.
*   **Surface:** A range of ultra-light grays and soft blues ensure the interface feels airy and organized.
*   **Functional:** Success, warning, and error states should follow standard semantic patterns but remain slightly desaturated to fit the professional tone.

## Typography

The typographic system utilizes **Hanken Grotesk** for headlines to provide a sharp, contemporary edge that feels tech-oriented. **Inter** is used for body text and functional labels to ensure maximum legibility and a neutral, systematic feel.

Visual hierarchy is established through significant weight contrast. Headlines should be bold and tightly spaced, while body copy maintains generous line heights for readability. Labels and "overlines" (like product feature tags) use medium to semi-bold weights in uppercase or sentence case to differentiate themselves from narrative text.

## Layout & Spacing

This design system uses a **Fluid Grid** model with high-density internal spacing and expansive external margins. The content is primarily centered or aligned to a 12-column grid to maintain a structured, professional appearance.

*   **Desktop:** 12 columns with 24px gutters. Wide 64px horizontal margins to create focus.
*   **Tablet:** 8 columns with 20px gutters. 32px horizontal margins.
*   **Mobile:** 4 columns with 16px gutters. 16px horizontal margins.

Layouts should favor vertical stacks with generous whitespace ("breathability") between distinct sections. Features and cards should utilize a consistent padding scale (usually 24px or 32px) to maintain a cohesive internal rhythm.

## Elevation & Depth

Hierarchy is achieved through **Tonal Layering** and **Ambient Shadows**. Instead of deep, harsh shadows, the system employs very soft, multi-layered blurs with a slight primary-color tint (#5D5FEF at 5-10% opacity) to make components feel like they are floating just above the surface.

**Glassmorphism** is applied to secondary surfaces like sidebars, navigation headers, or modal backdrops. Use a `backdrop-filter: blur(12px)` and a semi-transparent white fill (`rgba(255, 255, 255, 0.7)`) to create a sense of lightness and technical sophistication.

## Shapes

The shape language is defined by large, friendly corner radii that soften the technical nature of the product. 

*   **Base Radius (0.5rem):** Used for standard inputs, small buttons, and tags.
*   **Large Radius (1rem):** The default for cards, primary feature containers, and larger buttons.
*   **Extra Large Radius (1.5rem):** Used for major layout sections or "Hero" components to create a soft, modern frame.

## Components

### Buttons
Primary buttons should have a solid indigo background with high-contrast white text and a 1rem corner radius. Secondary buttons use a light indigo tint (#F0F3FF) with indigo text. Ghost buttons use a subtle gray outline or no border at all.

### Cards
Cards are the primary container. They feature a white background, a very thin (1px) border in a light gray (#E2E8F0), and a soft ambient shadow. For "Pro" features, cards may use a very subtle gradient border or a glassmorphic fill.

### Input Fields
Inputs should be clean and spacious with a 0.5rem radius. The focus state must be clearly indicated with a 2px indigo ring and a subtle glow.

### Chips & Tags
Used for categories (like "GitHub 3.6k+ Stars"). These should be pill-shaped with a light gray or primary-tint background and semi-bold typography.

### Lists
Lists in technical sections should use monospaced fonts for data-heavy strings, but retain Inter for descriptions. Use 1px dividers in light gray to separate items without creating visual noise.