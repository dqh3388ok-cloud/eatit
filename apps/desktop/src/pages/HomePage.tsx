import { Link } from "react-router-dom";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const links = [
  { label: "Upload Page", to: "/upload" },
  { label: "Config Page", to: "/config" },
  { label: "Interview Page", to: "/interview/demo-session" },
  { label: "History Page", to: "/history" },
  { label: "Report Page", to: "/report/demo-session" },
];

export function HomePage(): JSX.Element {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl items-center justify-center px-6 py-12">
      <Card className="w-full border-white/70 bg-white/90 shadow-xl">
        <CardHeader className="space-y-3">
          <CardDescription>Stage one hello world scaffold</CardDescription>
          <CardTitle className="text-3xl">Eatit Desktop Debug Home</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="max-w-3xl text-sm text-slate-600">
            This screen exists only for development. Use the buttons below to jump to the five
            required routes while the real product flow is still under construction.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {links.map((link) => (
              <Link key={link.to} to={link.to}>
                <Button className="w-full justify-start">{link.label}</Button>
              </Link>
            ))}
          </div>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">What is in this scaffold?</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Stage one scope</DialogTitle>
                <DialogDescription>
                  Desktop routing, shared providers, Tailwind styling, and Tauri shell are wired in.
                  Business logic and backend integration come next.
                </DialogDescription>
              </DialogHeader>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  );
}
