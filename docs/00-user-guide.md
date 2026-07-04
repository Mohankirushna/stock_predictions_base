# User Guide — What This Platform Is and How It Works

This is a plain-language walkthrough of the AI Investment Research Platform: what it's
for, how it behaves day to day, and what happens on every page. No code, no architecture
diagrams — just what you'd need to know to actually use it. For technical documentation
see the other files in this `docs/` folder.

## What This Is, In One Paragraph

This is a research desk for Indian stocks (NSE and BSE listings only), built to do the
work an analyst would do — pull real prices and news, run technical and fundamental
analysis, read the news and judge whether it's good or bad for the company, and then
write up a plain-English recommendation with a suggested entry price, a stop-loss, profit
targets, and an honest explanation of what could go wrong. It watches your portfolio and
watchlist, sends alerts when something notable happens, and keeps score of its own past
predictions so you can see whether its calls have actually been any good.

It is explicitly **not** a trading bot. It never places an order, never touches your
money, and every recommendation is labeled "research guidance" with a confidence score
that's mathematically capped below 100% — the platform is built to never claim certainty
about the market, because nobody honestly can.

## The Core Idea

Nobody has time to read every earnings call, every news article, and every candlestick
chart for more than a couple of stocks. This platform does that reading and charting
continuously, in the background, for whichever stocks you care about — and only bothers
you with a summary: here's the current price, here's what the news has been saying,
here's what the chart is doing, and here's what an AI model concludes when it looks at
all three at once, in writing you can actually follow.

## How Data Gets Onto the Platform

Nothing on this platform is hand-entered or hardcoded. Every number you see traces back
to a real source:

- **Prices and company info** come live from Yahoo Finance — real NSE/BSE quotes, real
  historical daily price bars, real company names and sectors.
- **News** comes from a live financial news search (marketaux) — real articles, always
  less than 30 days old, searched by the company's actual name (not just its ticker, so
  "HDFC Bank" news is found even though the raw ticker is `HDFCBANK.NS`).
- **The macro snapshot** (Fear & Greed, VIX, Oil, Gold, Bitcoin) comes from real ETF and
  index proxies, refreshed periodically — these are the only figures shown in US dollars,
  since they're global benchmarks, not Indian equities.
- **The AI reasoning** comes from a real language model reading the real data above and
  writing an actual response — never a canned template.

If a number can't be honestly sourced right now — say, a company's fundamentals aren't
available, or nobody's written news about a smaller company recently — the platform shows
that as an explicit gap ("no fundamentals computed yet," "no news articles for this
company yet") instead of inventing a plausible-looking substitute. That's a deliberate
design choice: an honest blank is more useful than a confident-looking guess.

## Any Indian Stock, Not Just a Fixed List

You can search for **any real NSE- or BSE-listed company** by name or symbol — not just
the handful the platform happens to already have data for. Type "Wipro," "Hero MotoCorp,"
or a ticker like "TCS" into the search bar, and if it isn't already tracked, the platform
will offer to fetch it on the spot: real company details and price history land within a
few seconds, and a technical read-out plus an AI recommendation follow shortly after in
the background (that part takes a bit longer because it involves an actual AI model
reading through everything). Once fetched, that company behaves exactly like any other —
it shows up in search, can be added to a watchlist, tracked in your portfolio, and so on.

## A Typical Session

1. **Open the Dashboard.** You get an immediate snapshot: the day's macro mood (bullish,
   neutral, risk-off), a couple of AI-surfaced opportunities the system thinks are worth a
   look, the most recent relevant news, and a quick list of today's biggest movers among
   the stocks the platform is actively tracking.
2. **Search for a stock you're curious about.** Type a name or symbol. If it's new to the
   platform, confirm you want it fetched — a few seconds later you're looking at real data
   for it.
3. **Open the company page.** See the price chart with the AI's suggested entry zone,
   stop-loss, and profit targets drawn right on it, the recommendation card with its
   reasoning, and tabs for news, technicals, financials, AI research, competitors, and
   past predictions for that stock.
4. **Add it to a watchlist** if you want to keep an eye on it without buying, or **record
   a transaction** in your portfolio if you're tracking a real (or paper) position.
5. **Set an alert** — get notified if the price breaks support/resistance, a volume spike
   hits, or sentiment shifts sharply.
6. **Come back later** and check the Leaderboard to see how accurate the platform's past
   predictions have actually been, broken down by sector and by how far out the
   prediction was (next day vs. next quarter).

## Page-by-Page

### Dashboard

Your morning briefing. Four things live here:

- **AI Opportunities** — a short list of stocks the AI has flagged as worth a look right
  now, each with its reasoning, a confidence percentage, a catalyst (why now), the key
  risk, and a suggested entry price range. This list is short on purpose — if nothing
  genuinely stands out, it says so rather than padding itself with weak picks.
- **Trending News** — the most recent real news across everything you're tracking, each
  tagged with a sentiment read and an impact level where the AI has had a chance to
  analyze it yet.
- **Top Gainers / Top Losers** — today's biggest real movers. If only two stocks are
  actually down today, only two show up under "Losers" — it won't pad the list with
  stocks that are actually up just to fill space.
- **Upcoming Earnings** — anything on the macro calendar in the near term.

### Markets

The wider view: sector-by-sector heat (which sectors are up or down and by how much),
the full gainers/losers list, and the macro calendar. Good for "what's happening across
the market today" rather than "what's happening with one stock."

### Companies

A browsable, searchable directory of every company the platform has data for. Search
here works the same way as the global search bar — type a name, and if it isn't tracked
yet you'll be offered the option to fetch it live.

### Company Page

The detailed view for one stock. At the top: current price, today's change, exchange, and
sector, plus buttons to add it to a watchlist or set an alert. Below that:

- **Price chart** — real daily candles, with the AI's entry zone, stop-loss, and three
  profit targets overlaid directly on the chart so you can see at a glance where the
  current price sits relative to the plan, plus volume and RSI underneath.
- **AI Recommendation card** — the headline call (strong buy / buy / hold / reduce /
  avoid), a 0–100 "master score," the entry zone and stop-loss and targets in actual
  numbers, a risk/reward ratio, how long the idea is meant to play out over (days, weeks,
  months, or a year+), and a confidence percentage that can never reach 100%. Expand "Why
  this recommendation?" for the plain-English reasoning, a list of pros and cons, and —
  importantly — an uncertainty note spelling out what would prove this call wrong. If
  there's no active recommendation yet (a newly-fetched stock, for instance), it says so
  rather than showing something stale or made up.
- **Tabs**: News (real recent articles about this specific company), Technicals (moving
  averages, RSI, momentum readings), Financials (fundamentals when available — margins,
  growth, debt, valuation), AI Research (a longer-form written report you can generate
  on demand), Competitors (other companies in the same sector), and Predictions (this
  stock's history of past AI predictions and how they turned out).

### Portfolio

Track real or paper positions. Record a buy or sell, and the platform keeps a running
tally: total value, cash balance, unrealized profit/loss, a portfolio health grade,
a diversification score, a risk score, and — when it's genuinely useful — rebalancing
suggestions if your holdings have drifted too concentrated in one stock or sector. The
holdings table shows quantity, average cost, current price, market value, and P&L for
everything you hold, all in Indian rupees.

### Watchlist

A lighter-weight version of the portfolio — stocks you want to keep an eye on without
recording a position. Each row shows the current price, today's change, and — if one
exists — the AI's current recommendation score and action for that stock at a glance.

### Research

Home of the AI Opportunities feed in its full form (the Dashboard shows a preview), plus
where on-demand AI research reports live once generated from a company page.

### Alerts & Notifications

Set rules per stock — sentiment shift, breakout, support/resistance break, volume spike —
and get notified in-app when the underlying condition is actually met by real data. No
alert fires on a guess; each one is backed by whatever the technical or news pipeline
just genuinely observed.

### Predictions

Every time the AI issues a recommendation, it also quietly commits to four testable
predictions — what it expects the price to do over the next day, week, month, and
quarter. This page lets you see those predictions and, once enough time has passed for
them to resolve, whether they were right.

### Leaderboard

The platform's own accountability page. Once predictions have had time to resolve (a day
old, a week old, and so on), their outcomes get scored and rolled up here by sector and by
time horizon — rolling accuracy percentages with the sample size behind each one. If there
simply aren't enough resolved predictions yet to say anything meaningful, it says exactly
that instead of showing a hollow number.

### Settings

Account details, notification preferences, and connected auth (email/password or Google).

### Admin

(Visible only to admin accounts.) Lets you tune how heavily each factor — news,
technicals, fundamentals, momentum, institutional signals, risk, and macro conditions —
contributes to the overall master score, watch a live console of the background agents
running and trigger one on demand, and review how much has been spent on AI usage.

## How a Recommendation Actually Gets Written

Worth walking through once, since it explains why the platform behaves the way it does:

1. A background process fetches the latest real price history and news for a stock.
2. A technical analysis pass computes real indicators — trend direction, RSI, moving
   averages, momentum — from the real price history.
3. A fundamental analysis pass computes real financial ratios when the data source
   actually has them available for that company (smaller companies sometimes don't, and
   the platform says so rather than filling in a placeholder).
4. Each fresh news article gets read by an AI model, which judges its sentiment,
   importance, and likely near-term impact.
5. All of that — technicals, fundamentals, news sentiment, institutional signals, broad
   market conditions — feeds a scoring formula that produces the 0–100 master score you
   see on the company page. That score is calculated in plain arithmetic, not guessed by
   the AI, so it's consistent and explainable.
6. Finally, an AI model is handed all of the above and asked to write the actual
   recommendation: the action, the entry zone, stop-loss, three profit targets, a holding
   period, pros, cons, a plain-English explanation, and a mandatory note on what would
   invalidate the call. If the model's proposed numbers don't make internal sense — for
   instance, a stop-loss that isn't actually below the entry price — the platform notices
   and asks it to try again rather than saving a self-contradictory recommendation.

Nothing in that chain is templated text. If the AI can't produce something sound, the
company simply shows no active recommendation rather than a fake one.

## Design Principles Worth Knowing

- **Real data or an honest gap — never a plausible-looking fake.** If fundamentals,
  news, or a recommendation aren't available, the platform says so directly.
- **Never certainty.** Every confidence score is mathematically prevented from reaching
  100%, and every recommendation is required to include a note on what could go wrong.
- **Research, not trading.** The platform can't and won't place a trade. It's built to
  inform a decision you make yourself.
- **Self-grading.** The Leaderboard exists specifically so the platform's own track
  record is visible and checkable, not just its opinions.

## Frequently Asked

**Why does a stock I just searched for show "no recommendation yet"?** Fetching a new
stock's price history is quick (a few seconds), but the AI analysis and recommendation
step takes longer and runs in the background — check back shortly after.

**Why is the Financials tab empty for some companies?** The underlying data source's
fundamentals endpoint is occasionally unavailable (an anti-automation layer on the
provider's side, not something the platform controls) — rather than guess at margins or
growth rates, it shows the gap honestly.

**Why does "Top Losers" sometimes show fewer stocks than "Top Gainers"?** Because it only
ever lists stocks that are genuinely down today. If most of what you're tracking happened
to be up, there just aren't many real losers to show.

**Is this financial advice?** No. It's research guidance, clearly labeled as such
throughout, with an uncertainty note attached to every call. Investment decisions, and
any trades, are entirely yours to make.
