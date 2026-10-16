import { readFile, mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.join(root, "knowledge");
const data = JSON.parse(await readFile(path.join(root, "portfolio_data.json"), "utf8"));

const label = (value) => String(value)
  .replaceAll("_", " ")
  .replace(/\b\w/g, (letter) => letter.toUpperCase());

const slug = (value) => String(value)
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, "-")
  .replace(/^-|-$/g, "")
  .slice(0, 72);

function markdown(value, depth = 2) {
  if (value === null || value === undefined || value === "") return "";
  if (Array.isArray(value)) {
    if (value.every((item) => typeof item !== "object" || item === null)) {
      return value.map((item) => `- ${item}`).join("\n");
    }
    return value.map((item, index) => {
      const title = item?.title || item?.name || item?.role || item?.degree || `Entry ${index + 1}`;
      return `${"#".repeat(depth)} ${title}\n\n${markdown(item, depth + 1)}`;
    }).join("\n\n");
  }
  if (typeof value === "object") {
    return Object.entries(value).map(([key, item]) => {
      if (item === null || item === undefined || item === "") return "";
      if (typeof item === "object") {
        return `${"#".repeat(depth)} ${label(key)}\n\n${markdown(item, depth + 1)}`;
      }
      return `- **${label(key)}:** ${item}`;
    }).filter(Boolean).join("\n\n");
  }
  return String(value);
}

function document({ type, title, tags, source, body }) {
  return `---\ntype: ${JSON.stringify(type)}\ntitle: ${JSON.stringify(title)}\ntags: ${JSON.stringify(tags)}\nsource: ${JSON.stringify(source)}\n---\n\n# ${title}\n\n${body.trim()}\n`;
}

await rm(output, { recursive: true, force: true });
await mkdir(path.join(output, "projects"), { recursive: true });

const entries = [];
const write = async (relative, options) => {
  entries.push(relative.replaceAll("\\", "/"));
  await writeFile(path.join(output, relative), document(options), "utf8");
};

await write("profile.md", {
  type: "concept",
  title: "Profile and contact",
  tags: ["profile", "contact", "availability", "links"],
  source: "portfolio_data.json#personal",
  body: markdown({ ...data.personal, employer: data.employer, stats: data.stats }),
});

await write("education.md", {
  type: "reference",
  title: "Education and certifications",
  tags: ["education", "degrees", "certifications"],
  source: "portfolio_data.json#education",
  body: markdown({ education: data.education, certifications: data.certifications }),
});

await write("experience.md", {
  type: "reference",
  title: "Work experience",
  tags: ["experience", "employment", "internship", "career"],
  source: "portfolio_data.json#work_experience",
  body: markdown(data.work_experience),
});

await write("skills.md", {
  type: "reference",
  title: "Technical skills",
  tags: ["skills", "technology", "stack", "tools"],
  source: "portfolio_data.json#skills",
  body: markdown(data.skills),
});

await write("research.md", {
  type: "reference",
  title: "Research and publications",
  tags: ["research", "publications", "glycomics", "machine learning"],
  source: "portfolio_data.json#publications",
  body: markdown({ interests: data.research_interests, publications: data.publications }),
});

for (const [name, project] of Object.entries(data.projects)) {
  await write(path.join("projects", `${slug(name)}.md`), {
    type: "concept",
    title: name.replaceAll("\n", " "),
    tags: ["project", ...(project.technologies || project.tech_stack || [])].slice(0, 10),
    source: `portfolio_data.json#projects/${name.replaceAll("/", "~1")}`,
    body: markdown(project),
  });
}

const index = `---\ntitle: Vigneshwaran CJ Portfolio Knowledge\nversion: 1.0.0\nentries:\n${entries.map((entry) => `  - ${entry}`).join("\n")}\n---\n\n# Vigneshwaran CJ Portfolio Knowledge\n\nGrounded portfolio facts for assistant retrieval. Generated from portfolio_data.json with scripts/build_okf.mjs.\n`;
await writeFile(path.join(output, "index.md"), index, "utf8");
console.log(`Wrote ${entries.length} OKF entries to ${output}`);
