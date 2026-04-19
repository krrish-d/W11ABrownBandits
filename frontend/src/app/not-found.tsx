import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function NotFound() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Page not found</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="muted-text">The route does not exist in this frontend build.</p>
        <Link href="/">
          <Button>Go to dashboard</Button>
        </Link>
      </CardContent>
    </Card>
  );
}
