import { ModelCatalogWorkspace } from "@/components/ModelCatalogWorkspace";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function ModelCatalogPage() {
  return (
    <ProtectedRoute requiredPermission="catalog.models.read">
      <ModelCatalogWorkspace />
    </ProtectedRoute>
  );
}
