import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type PageShellProps = {
  title: string;
  description: string;
  routePath: string;
};

export function PageShell({ title, description, routePath }: PageShellProps): JSX.Element {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl items-center justify-center px-6 py-12">
      <Card className="w-full border-white/60 bg-white/90">
        <CardHeader>
          <CardDescription>Eatit desktop scaffold</CardDescription>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="rounded-lg border bg-slate-50 p-4 text-sm text-slate-700">
            <p>{description}</p>
            <p className="mt-2 font-mono text-xs text-slate-500">{routePath}</p>
          </div>
          <Link to="/">
            <Button variant="outline">Back Home</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
