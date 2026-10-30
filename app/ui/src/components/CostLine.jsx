import { costText, formatUSD, stageLabel } from './insights.js';

// Shared priced/unpriced cost wording (DESIGN.md C.2: identical text in
// ledger and Insights for the same call; unpriced is never $0.00).
export default function CostLine({ item }) {
  const cost = costText(item);
  if (!cost.priced) return <span className="muted mono">not yet priced</span>;
  return (
    <span className="mono">
      {cost.text} <span className="muted">estimated</span>
    </span>
  );
}
export function CostPill({ item }) {
  const cost = costText(item);
  const legs = Array.isArray(item.model_usage) ? item.model_usage : [];
  if (!cost.priced) {
    return (
      <div className="cost-pill-row">
        <span className="cost-pill unpriced">Cost: not yet priced</span>
      </div>
    );
  }
  return (
    <div className="cost-pill-row">
      <span className="cost-pill">Estimated Cost: {formatUSD(item.cost_cents)}</span>
      {legs.length > 0 && (
        <ul className="model-usage">
          {legs.map((leg, i) => (
            <li key={i}>
              {stageLabel(leg.stage)} ({leg.model}): {legDetail(leg)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function legDetail(leg) {
  const use =
    leg.stage === 'sam'
      ? `${leg.images} image${leg.images === 1 ? '' : 's'}`
      : `${leg.prompt_tokens} in / ${leg.completion_tokens} out`;
  return `${use} - ${formatUSD(leg.cost_cents)}${leg.cost_priced ? '' : ' (unpriced)'}`;
}
