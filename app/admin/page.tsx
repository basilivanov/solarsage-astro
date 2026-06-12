'use client';

import Link from 'next/link';

export default function AdminPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold">GRACE Admin</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Business feature intake and planning pipeline
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Link
          href="/admin/features"
          className="rounded-lg border p-4 transition-colors hover:border-primary"
        >
          <h2 className="font-semibold">Features</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Create and manage business features
          </p>
        </Link>

        <div className="rounded-lg border border-dashed p-4 opacity-50">
          <h2 className="font-semibold">Workers</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Coming soon
          </p>
        </div>
      </div>
    </div>
  );
}
