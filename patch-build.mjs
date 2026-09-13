import fs from "node:fs";

function replaceInFile(path, replacer) {
  if (!fs.existsSync(path)) return;
  const before = fs.readFileSync(path, "utf8");
  const after = replacer(before);
  if (after !== before) fs.writeFileSync(path, after, "utf8");
}

// 1) Disable Next.js typedRoutes so internal href literals don't block compilation.
replaceInFile("next.config.ts", (s) =>
  s.replace(/typedRoutes:\s*true/g, "typedRoutes: false")
);

// 2) Next.js 16: useSearchParams() can be null in type checking.
replaceInFile("components/bazi-mode-tabs.tsx", (s) => {
  const oldLine =
    'const currentHref = useMemo(() => `${pathname}?${searchParams.toString()}`, [pathname, searchParams]);';

  if (s.includes(oldLine)) {
    return s.replace(
      oldLine,
      `const currentHref = useMemo(() => {
        const query = searchParams?.toString() ?? "";
        const basePath = pathname ?? "/bazi";
        return \`\${basePath}\${query ? \`?\${query}\` : ""}\`;
    }, [pathname, searchParams]);`
    );
  }
  return s;
});

// 3) Narrow normalizedChart before passing it to buildBaziReadingBundle().
replaceInFile("lib/bazi-provider.ts", (s) =>
  s.replace(
    'const readingBundle = chart?.status === "ready"\\n        ? buildBaziReadingBundle({\\n              chart: normalizedChart,',
    'const readingBundle = normalizedChart?.status === "ready"\\n        ? buildBaziReadingBundle({\\n              chart: normalizedChart,'
  )
);

console.log("WEB2 build patch v2 applied.");
