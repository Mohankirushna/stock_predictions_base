import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { NewsItem } from "@/types/models";

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diffMs / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function SentimentDot({ sentiment }: { sentiment: number | null }) {
  const color = sentiment === null ? "bg-muted" : sentiment > 0.15 ? "bg-bull" : sentiment < -0.15 ? "bg-bear" : "bg-warning";
  return <span className={cn("mt-1 size-2 shrink-0 rounded-full", color)} />;
}

export function NewsFeed({ items }: { items: NewsItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Trending News</CardTitle>
      </CardHeader>
      <CardContent className="max-h-[32rem] space-y-3 overflow-y-auto">
        {items.length === 0 && <p className="text-sm text-muted">No analyzed news yet.</p>}
        {items.map((item) => (
          <a
            key={item.id}
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-start gap-2 rounded-md p-1 -m-1 hover:bg-panel-hover"
          >
            <SentimentDot sentiment={item.sentiment} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">{item.title}</p>
              <div className="mt-0.5 flex items-center gap-2 text-[11px] text-muted">
                <span>{item.source}</span>
                <span>&middot;</span>
                <span>{timeAgo(item.published_at)}</span>
                {item.importance !== null && item.importance >= 7 && (
                  <Badge variant="warning" className="ml-auto">
                    High impact
                  </Badge>
                )}
              </div>
            </div>
          </a>
        ))}
      </CardContent>
    </Card>
  );
}
