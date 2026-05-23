"use client";

type PageFeedbackProps = {
  title: string;
  message: string;
};

export function LoadingCard({ title, message }: PageFeedbackProps) {
  return (
    <div className="glass-card rounded-xl p-6">
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

export function ErrorCard({ title, message }: PageFeedbackProps) {
  return (
    <div className="glass-card rounded-xl border border-red-500/20 p-6">
      <p className="text-sm font-medium text-red-300">{title}</p>
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
