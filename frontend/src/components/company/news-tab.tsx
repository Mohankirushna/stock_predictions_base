import { Badge } from "@/components/ui/badge";
import type { NewsItem } from "@/types/models";

function sentimentBadge(sentiment: number | null) {
  if (sentiment === null) return <Badge variant="outline">Neutral</Badge>;
  if (sentiment > 0.15) return <Badge variant="bull">Positive</Badge>;
  if (sentiment < -0.15) return <Badge variant="bear">Negative</Badge>;
  return <Badge variant="outline">Neutral</Badge>;
}

export function NewsTab({ items }: { items: NewsItem[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">No news articles for this company yet.</p>;
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <a
          key={item.id}
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="block rounded-md border border-border p-3 hover:bg-panel-hover"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="font-medium">{item.title}</p>
            {sentimentBadge(item.sentiment)}
          </div>
          <p className="mt-1 text-xs text-muted">
            {item.source} &middot; {item.published_at ? new Date(item.published_at).toLocaleDateString() : "unknown date"}
          </p>
          {item.summary && <p className="mt-2 text-sm text-muted">{item.summary}</p>}
          {(item.risks.length > 0 || item.opportunities.length > 0) && (
            <div className="mt-2 grid grid-cols-2 gap-3 text-xs">
              {item.opportunities.length > 0 && (
                <ul className="list-disc space-y-0.5 pl-4 text-bull">
                  {item.opportunities.map((o) => (
                    <li key={o}>{o}</li>
                  ))}
                </ul>
              )}
              {item.risks.length > 0 && (
                <ul className="list-disc space-y-0.5 pl-4 text-bear">
                  {item.risks.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </a>
      ))}
    </div>
  );
}
