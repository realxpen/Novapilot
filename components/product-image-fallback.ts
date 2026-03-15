const REPRESENTATIVE_IMAGE_BY_KEYWORD: Array<{ keywords: string[]; image: string }> = [
  {
    keywords: [
      "iphone",
      "samsung",
      "galaxy",
      "pixel",
      "redmi",
      "xiaomi",
      "infinix",
      "tecno",
      "oppo",
      "vivo",
      "realme",
      "phone",
      "smartphone",
    ],
    image:
      "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
  },
  {
    keywords: [
      "laptop",
      "notebook",
      "thinkpad",
      "latitude",
      "elitebook",
      "inspiron",
      "ideapad",
      "probook",
      "zenbook",
      "macbook",
      "dell",
      "lenovo",
      "hp",
      "asus",
      "acer",
      "msi",
    ],
    image:
      "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?auto=format&fit=crop&w=1200&q=80",
  },
  {
    keywords: ["ipad", "tablet", "tab ", "pad "],
    image:
      "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1200&q=80",
  },
  {
    keywords: ["headphone", "earbud", "earphone", "jbl", "sony", "soundcore", "buds", "wh-"],
    image:
      "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=80",
  },
];

const DEFAULT_IMAGE =
  "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?auto=format&fit=crop&w=1200&q=80";

function isLikelyHttpImage(url: string | null | undefined): boolean {
  if (!url) {
    return false;
  }
  const value = url.trim().toLowerCase();
  return value.startsWith("https://") || value.startsWith("http://");
}

export function getRepresentativeProductImage(name: string): string {
  const normalized = (name || "").toLowerCase();
  for (const option of REPRESENTATIVE_IMAGE_BY_KEYWORD) {
    if (option.keywords.some((keyword) => normalized.includes(keyword))) {
      return option.image;
    }
  }
  return DEFAULT_IMAGE;
}

export function resolveProductImage(primaryUrl: string | null | undefined, name: string): string {
  if (isLikelyHttpImage(primaryUrl)) {
    return primaryUrl!.trim();
  }
  return getRepresentativeProductImage(name);
}

export function resolveLiveProductImage(primaryUrl: string | null | undefined): string | null {
  if (isLikelyHttpImage(primaryUrl)) {
    return primaryUrl!.trim();
  }
  return null;
}
