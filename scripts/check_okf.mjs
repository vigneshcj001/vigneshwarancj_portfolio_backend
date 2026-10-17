import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const bundle = path.join(root, "knowledge");
const index = (await readFile(path.join(bundle, "index.md"), "utf8")).replaceAll("\r\n", "\n");
const frontmatterEnd = index.indexOf("\n---\n", 4);
if (!index.startsWith("---\n") || frontmatterEnd < 0) throw new Error("Invalid OKF index frontmatter");

const entries = index.slice(4, frontmatterEnd)
  .split("\n")
  .filter((line) => /^\s*-\s+/.test(line))
  .map((line) => line.replace(/^\s*-\s+/, "").trim());

if (!entries.length) throw new Error("OKF index contains no entries");
if (new Set(entries).size !== entries.length) throw new Error("OKF index contains duplicate entries");

for (const entry of entries) {
  const resolved = path.resolve(bundle, entry);
  if (!resolved.startsWith(`${path.resolve(bundle)}${path.sep}`) || path.extname(resolved) !== ".md") {
    throw new Error(`Unsafe OKF entry: ${entry}`);
  }
  const content = (await readFile(resolved, "utf8")).replaceAll("\r\n", "\n");
  if (!content.startsWith("---\n") || !content.includes("\ntype:") || !content.includes("\ntitle:")) {
    throw new Error(`Invalid OKF document: ${entry}`);
  }
}

for (const expected of ["projects/pocketpet.md", "projects/syncly.md", "research/interests.md", "skills.md"]) {
  if (!entries.includes(expected)) throw new Error(`Missing required OKF entry: ${expected}`);
}

console.log(`OKF bundle valid: ${entries.length} indexed documents`);
