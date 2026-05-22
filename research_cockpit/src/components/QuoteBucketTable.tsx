import type { QuoteBucket } from "../types";
import { TrafficLight } from "./TrafficLight";

interface QuoteBucketTableProps {
  buckets: QuoteBucket[];
}

export function QuoteBucketTable({ buckets }: QuoteBucketTableProps) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Bucket</th>
            <th>Fills</th>
            <th>Trades</th>
            <th>TP</th>
            <th>SL</th>
            <th>Mean PnL</th>
            <th>State</th>
          </tr>
        </thead>
        <tbody>
          {buckets.map((bucket) => (
            <tr key={bucket.bucket}>
              <td>{bucket.bucket}</td>
              <td>{bucket.fills}</td>
              <td>{bucket.trades}</td>
              <td>{bucket.tp}</td>
              <td>{bucket.sl}</td>
              <td>{bucket.meanPnl}</td>
              <td>
                <TrafficLight state={bucket.state} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
