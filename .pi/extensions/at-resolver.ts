/**
 * @-reference Resolver Extension for Pi
 *
 * Pi loads AGENTS.md OR CLAUDE.md (prefers AGENTS.md). This extension:
 * 1. Reads CLAUDE.md directly (since pi skips it when AGENTS.md exists)
 * 2. Resolves @file references in CLAUDE.md
 * 3. Appends resolved content to the system prompt
 *
 * This ensures parity with Claude Code's context loading behavior.
 *
 * Loaded from: .pi/extensions/at-resolver.ts (project-local auto-discovery)
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname, join } from "node:path";

const MAX_DEPTH = 3;
const MAX_FILE_SIZE = 50_000;

function resolveAtReferences(
  content: string,
  baseDir: string,
  projectRoot: string,
  seen: Set<string> = new Set(),
  depth: number = 0,
): string {
  if (depth >= MAX_DEPTH) return "";

  const lines = content.split("\n");
  const resolved: string[] = [];

  for (const line of lines) {
    const match = line.match(/^@([^\s@][^\s]*)\s*$/);
    if (!match) continue;

    const refPath = match[1];

    // Skip AGENTS.md/CLAUDE.md — pi already loads context files
    if (refPath === "AGENTS.md" || refPath === "CLAUDE.md") continue;

    const candidates = [
      resolve(baseDir, refPath),
      resolve(projectRoot, refPath),
    ];

    let filePath: string | null = null;
    for (const candidate of candidates) {
      if (existsSync(candidate)) {
        filePath = candidate;
        break;
      }
    }

    if (!filePath) continue;
    if (seen.has(filePath)) continue;
    seen.add(filePath);

    try {
      const fileContent = readFileSync(filePath, "utf-8");
      if (fileContent.length > MAX_FILE_SIZE) continue;

      const fileDir = dirname(filePath);
      const nestedContent = resolveAtReferences(fileContent, fileDir, projectRoot, seen, depth + 1);

      resolved.push(`\n---\n## @${refPath}\n\n${fileContent}`);
      if (nestedContent) {
        resolved.push(nestedContent);
      }
    } catch {
      // Skip unreadable files silently
    }
  }

  return resolved.join("\n");
}

function findClaudeMd(projectRoot: string): string | null {
  const candidates = [join(projectRoot, "CLAUDE.md")];

  let dir = projectRoot;
  for (let i = 0; i < 5; i++) {
    const parent = dirname(dir);
    if (parent === dir) break;
    candidates.push(join(parent, "CLAUDE.md"));
    dir = parent;
  }

  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

export default function atResolver(pi: ExtensionAPI) {
  pi.on("before_agent_start", async (event) => {
    const { systemPromptOptions } = event;
    const projectRoot = systemPromptOptions.cwd || process.cwd();
    const contextFiles = systemPromptOptions.contextFiles || [];

    // Check if CLAUDE.md was already loaded as a context file
    const claudeAlreadyLoaded = contextFiles.some(
      (f) => f.path.endsWith("CLAUDE.md")
    );

    const extraParts: string[] = [];
    const seen = new Set<string>();

    // 1. Process @ references from already-loaded context files
    for (const file of contextFiles) {
      if (!file.content) continue;
      const baseDir = dirname(file.path);
      const resolved = resolveAtReferences(file.content, baseDir, projectRoot, seen);
      if (resolved) extraParts.push(resolved);
    }

    // 2. If CLAUDE.md wasn't loaded by pi, read it directly and resolve @ refs
    if (!claudeAlreadyLoaded) {
      const claudePath = findClaudeMd(projectRoot);
      if (claudePath) {
        try {
          const claudeContent = readFileSync(claudePath, "utf-8");
          const baseDir = dirname(claudePath);
          const resolved = resolveAtReferences(claudeContent, baseDir, projectRoot, seen);

          // Add CLAUDE.md content (minus @ lines) + resolved refs
          const cleanedContent = claudeContent
            .split("\n")
            .filter((line) => !line.match(/^@[^\s@][^\s]*\s*$/))
            .join("\n");

          extraParts.push(`\n---\n## CLAUDE.md (via at-resolver)\n\n${cleanedContent}`);
          if (resolved) extraParts.push(resolved);
        } catch {
          // Skip if unreadable
        }
      }
    }

    if (extraParts.length === 0) return {};

    return {
      systemPrompt: event.systemPrompt + "\n\n" + extraParts.join("\n"),
    };
  });
}
