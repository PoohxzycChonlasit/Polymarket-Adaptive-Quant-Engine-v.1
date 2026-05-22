import type { CockpitData } from "../types";
import { MetricCard } from "../components/MetricCard";
import { QuoteBucketTable } from "../components/QuoteBucketTable";

interface QuoteAgeProps {
  data: CockpitData;
}

export function QuoteAge({ data }: QuoteAgeProps) {
  return (
    <section className="page-section" id="quote-age">
      <div className="section-heading">
        <p className="eyebrow">Quote Age</p>
        <h2>Freshness bucket view</h2>
      </div>
      <div className="card-grid two-up">
        <MetricCard title="quote_age_at_submit_ms" value={`${data.quoteAge.meanSubmitMs} ms`} detail="mean submit quote age" state="blue" />
        <MetricCard title="quote_age_at_fill_ms" value={`${data.quoteAge.meanFillMs} ms`} detail="mean fill quote age" state="blue" />
      </div>
      <QuoteBucketTable buckets={data.quoteAge.buckets} />
    </section>
  );
}
