import { InternalMessagesWorkspace } from "@/components/InternalMessagesWorkspace";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function MessagesPage() {
  return (
    <ProtectedRoute requiredPermission="communications.read">
      <InternalMessagesWorkspace />
    </ProtectedRoute>
  );
}
