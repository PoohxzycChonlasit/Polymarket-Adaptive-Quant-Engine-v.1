import { Link } from "react-router-dom";

import { SectionPanel } from "../../components/common/SectionPanel";

export function NotFoundPage() {
  return (
    <SectionPanel title="Dashboard page not found" subtitle="This read-only dashboard route does not exist.">
      <p className="muted-copy">Choose a page from the sidebar to return to known dashboard evidence.</p>
      <Link className="inline-link" to="/">
        Back to Overview
      </Link>
    </SectionPanel>
  );
}
