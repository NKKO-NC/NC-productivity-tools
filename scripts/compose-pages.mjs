import { cp, mkdir, readdir, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).map((entry) => {
    const [key, value] = entry.split("=");
    return [key.replace(/^--/, ""), value];
  })
);

const currentRef = args.currentRef;
const previewBranch = args.previewBranch;
const currentDir = path.resolve(args.currentDir);
const mainDir = args.mainDir ? path.resolve(args.mainDir) : null;
const stablePreviewDir = args.stablePreviewDir ? path.resolve(args.stablePreviewDir) : null;
const outDir = path.resolve(args.outDir);

const rootEntries = ["assets", "index.html", "manifest.webmanifest", "sw.js", "tools"];

async function exists(target) {
  try {
    await stat(target);
    return true;
  } catch {
    return false;
  }
}

async function copyEntry(sourceRoot, relativePath, destinationRoot) {
  const source = path.join(sourceRoot, relativePath);
  if (!(await exists(source))) {
    return;
  }

  const destination = path.join(destinationRoot, relativePath);
  await mkdir(path.dirname(destination), { recursive: true });
  await cp(source, destination, { recursive: true });
}

async function copyRootSite(sourceRoot, destinationRoot) {
  for (const entry of rootEntries) {
    await copyEntry(sourceRoot, entry, destinationRoot);
  }
}

async function copyPreviewSite(sourceRoot, destinationRoot) {
  const previewSource = path.join(sourceRoot, "preview");
  if (!(await exists(previewSource))) {
    return false;
  }

  const previewTarget = path.join(destinationRoot, "preview");
  await cp(previewSource, previewTarget, { recursive: true });
  return true;
}

async function main() {
  if (!currentRef) {
    throw new Error("Missing --currentRef");
  }

  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });

  const productionSource = currentRef === "main" ? currentDir : mainDir;
  if (!productionSource || !(await exists(productionSource))) {
    throw new Error("Production source is not available.");
  }

  await copyRootSite(productionSource, outDir);

  const previewSource =
    currentRef !== "main"
      ? currentDir
      : stablePreviewDir && (await exists(stablePreviewDir))
        ? stablePreviewDir
        : null;

  if (previewSource) {
    await copyPreviewSite(previewSource, outDir);
  }

  await writeFile(path.join(outDir, ".nojekyll"), "");

  const publishedEntries = await readdir(outDir);
  console.log(
    JSON.stringify(
      {
        currentRef,
        previewBranch,
        publishedEntries
      },
      null,
      2
    )
  );
}

await main();
