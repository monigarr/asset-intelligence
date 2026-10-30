export default function NextStepCta({ text }) {
  if (!text) return null;
  return (
    <div className="panel nextstep-cta">
      <h2>Recommended next step</h2>
      <p className="nextstep-text">{text}</p>
      <p className="hint">Act on it in Human review below: accept, correct, or reject.</p>
    </div>
  );
}