"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ResearchReport } from "@/types/models";

const SECTION_ORDER = ["overview", "catalysts", "risks", "valuation", "competitive_position", "outlook"];

function sectionTitle(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function ResearchTab({
  report,
  onGenerate,
  generating,
}: {
  report: ResearchReport | null;
  onGenerate: () => void;
  generating: boolean;
}) {
  const [openSections, setOpenSections] = React.useState<Set<string>>(new Set());

  if (!report) {
    return (
      <div className="text-sm text-muted">
        <p className="mb-3">No AI research report has been generated for this company yet.</p>
        <Button size="sm" onClick={onGenerate} disabled={generating}>
          {generating ? "Generating…" : "Generate Report"}
        </Button>
      </div>
    );
  }

  const keys = [
    ...SECTION_ORDER.filter((k) => k in report.sections),
    ...Object.keys(report.sections).filter((k) => !SECTION_ORDER.includes(k)),
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-muted">
          <Badge variant="accent">{report.ai_provider}</Badge>
          <span>{report.ai_model}</span>
          <span>&middot; v{report.version}</span>
          <span>&middot; {new Date(report.created_at).toLocaleDateString()}</span>
        </div>
        <Button size="sm" variant="outline" onClick={onGenerate} disabled={generating}>
          {generating ? "Regenerating…" : "Regenerate"}
        </Button>
      </div>

      <p className="rounded-md border border-border bg-panel-hover p-3 text-sm">{report.summary}</p>

      {keys.map((key) => {
        const section = report.sections[key];
        const isOpen = openSections.has(key);
        return (
          <div key={key} className="border-b border-border pb-3 last:border-0">
            <button
              className="flex w-full items-center justify-between text-left text-sm font-medium hover:text-accent"
              onClick={() =>
                setOpenSections((prev) => {
                  const next = new Set(prev);
                  if (next.has(key)) next.delete(key);
                  else next.add(key);
                  return next;
                })
              }
            >
              {sectionTitle(key)}
              <ChevronDown className={`size-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </button>
            {isOpen && (
              <div className="mt-2 text-sm text-muted">
                <p>{section.text}</p>
                {section.sources.length > 0 && (
                  <p className="mt-1 text-[11px]">Sources: {section.sources.join(", ")}</p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
