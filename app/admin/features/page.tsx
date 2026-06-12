'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api-fetch';

interface FeatureItem {
  id: string;
  title: string;
  status: string;
  mode: string;
  origin: string;
  createdAt: string;
  updatedAt: string;
  planningRunsCount: number;
  currentStage?: string;
}

interface CreateFormData {
  title: string;
  description: string;
  mode: 'draft_plan' | 'auto_queue';
  origin: string;
}

export default function AdminFeaturesPage() {
  const [features, setFeatures] = useState<FeatureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState<CreateFormData>({
    title: '',
    description: '',
    mode: 'draft_plan',
    origin: 'business',
  });
  const [creating, setCreating] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState<string | null>(null);
  const [planningState, setPlanningState] = useState<any>(null);
  const [planningLoading, setPlanningLoading] = useState(false);

  const loadFeatures = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiFetch('GET /api/admin/features', '/api/admin/features');
      if (!res.ok) {
        setError(`Failed to load features: ${res.status}`);
        return;
      }
      const body = await res.json();
      setFeatures(body.data ?? []);
    } catch (e: any) {
      setError(e.message ?? 'Failed to load features');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFeatures();
  }, [loadFeatures]);

  const loadPlanningState = useCallback(async (featureId: string) => {
    try {
      setPlanningLoading(true);
      const res = await apiFetch(
        `GET /api/features/${featureId}/planning`,
        `/api/features/${featureId}/planning`,
      );
      if (!res.ok) {
        console.error('Failed to load planning state:', res.status);
        return;
      }
      const body = await res.json();
      setPlanningState(body.data ?? null);
    } catch (e: any) {
      console.error('Failed to load planning state:', e);
    } finally {
      setPlanningLoading(false);
    }
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) return;

    try {
      setCreating(true);
      const res = await apiFetch('POST /api/features', '/api/features', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const err = await res.text();
        setError(`Create failed: ${err}`);
        return;
      }

      setShowCreateForm(false);
      setFormData({ title: '', description: '', mode: 'draft_plan', origin: 'business' });
      await loadFeatures();
    } catch (e: any) {
      setError(e.message ?? 'Create failed');
    } finally {
      setCreating(false);
    }
  };

  const handleApprovePlan = async (featureId: string) => {
    try {
      const res = await apiFetch(
        `POST /api/features/${featureId}/approve-plan`,
        `/api/features/${featureId}/approve-plan`,
        { method: 'POST' },
      );
      if (!res.ok) {
        const err = await res.text();
        setError(`Approve failed: ${err}`);
        return;
      }
      await loadFeatures();
      if (selectedFeature === featureId) {
        await loadPlanningState(featureId);
      }
    } catch (e: any) {
      setError(e.message ?? 'Approve failed');
    }
  };

  const handleRegeneratePlan = async (featureId: string) => {
    try {
      const res = await apiFetch(
        `POST /api/features/${featureId}/regenerate-plan`,
        `/api/features/${featureId}/regenerate-plan`,
        { method: 'POST' },
      );
      if (!res.ok) {
        const err = await res.text();
        setError(`Regenerate failed: ${err}`);
        return;
      }
      await loadFeatures();
      if (selectedFeature === featureId) {
        await loadPlanningState(featureId);
      }
    } catch (e: any) {
      setError(e.message ?? 'Regenerate failed');
    }
  };

  const selectFeature = (featureId: string) => {
    setSelectedFeature(featureId);
    setPlanningState(null);
    loadPlanningState(featureId);
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      NOT_STARTED: 'bg-gray-500',
      PLANNING: 'bg-blue-500',
      PLAN_READY: 'bg-green-500',
      PLAN_FAILED: 'bg-red-500',
      QUEUED: 'bg-yellow-500',
      ACTIVE: 'bg-purple-500',
      DONE: 'bg-green-700',
      ARCHIVED: 'bg-gray-400',
    };
    return (
      <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium text-white ${colors[status] ?? 'bg-gray-500'}`}>
        {status}
      </span>
    );
  };

  const stageStatusIcon = (status: string) => {
    switch (status) {
      case 'done': return '✅';
      case 'running': return '🔄';
      case 'pending': return '⏳';
      case 'failed': return '❌';
      case 'skipped': return '⏭️';
      default: return '⬜';
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Features</h1>
          <p className="text-sm text-muted-foreground">
            Business features and their planning status
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {showCreateForm ? 'Cancel' : 'New Feature'}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {/* Create Form */}
      {showCreateForm && (
        <form onSubmit={handleCreate} className="mt-6 rounded-lg border p-4">
          <h2 className="mb-4 font-semibold">New Business Feature</h2>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium">Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                placeholder="e.g. Add dark mode"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                rows={3}
                placeholder="Describe the business requirement..."
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium">Mode</label>
                <select
                  value={formData.mode}
                  onChange={(e) => setFormData({ ...formData, mode: e.target.value as any })}
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                >
                  <option value="draft_plan">Draft Plan</option>
                  <option value="auto_queue">Auto Queue</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium">Origin</label>
                <select
                  value={formData.origin}
                  onChange={(e) => setFormData({ ...formData, origin: e.target.value })}
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                >
                  <option value="business">Business</option>
                  <option value="self_evolution">Self Evolution</option>
                  <option value="api">API</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={creating || !formData.title.trim()}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create Feature'}
            </button>
          </div>
        </form>
      )}

      {/* Feature List */}
      {loading ? (
        <div className="mt-6 flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : features.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          No features yet. Create one to get started.
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {features.map((feature) => (
            <div key={feature.id}>
              <button
                onClick={() => selectFeature(feature.id)}
                className={`w-full rounded-lg border p-4 text-left transition-colors hover:border-primary ${
                  selectedFeature === feature.id ? 'border-primary ring-1 ring-primary' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{feature.title}</span>
                      {statusBadge(feature.status)}
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                      <span>{feature.mode}</span>
                      <span>{feature.origin}</span>
                      <span>{feature.planningRunsCount} runs</span>
                      <span>{new Date(feature.createdAt).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </button>

              {/* Planning Detail */}
              {selectedFeature === feature.id && (
                <div className="mt-2 rounded-lg border border-t-0 p-4">
                  {planningLoading ? (
                    <div className="flex justify-center py-4">
                      <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    </div>
                  ) : planningState ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-3 gap-3 text-sm">
                        <div>
                          <span className="text-muted-foreground">Status: </span>
                          {statusBadge(planningState.status)}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Stage: </span>
                          <span className="font-medium">{planningState.currentStage ?? '—'}</span>
                        </div>
                      </div>

                      {/* Stage Timeline */}
                      <div className="space-y-2">
                        <h3 className="text-sm font-medium">Planning Stages</h3>
                        {planningState.runs?.map((run: any) => (
                          <div key={run.id} className="flex items-center gap-3 rounded-md border px-3 py-2 text-sm">
                            <span>{stageStatusIcon(run.status)}</span>
                            <span className="w-36 font-medium">{run.stage}</span>
                            <span className="text-muted-foreground">{run.status}</span>
                            {run.durationMs != null && (
                              <span className="text-xs text-muted-foreground">
                                {(run.durationMs / 1000).toFixed(1)}s
                              </span>
                            )}
                            {run.executorId && (
                              <span className="text-xs text-muted-foreground">{run.executorId}</span>
                            )}
                            {run.error && (
                              <span className="ml-auto text-xs text-red-500" title={run.error}>
                                Error
                              </span>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Plan Actions */}
                      {planningState.status === 'PLAN_READY' && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleApprovePlan(feature.id)}
                            className="rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
                          >
                            Approve Plan
                          </button>
                          <button
                            onClick={() => handleRegeneratePlan(feature.id)}
                            className="rounded bg-yellow-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-yellow-700"
                          >
                            Regenerate
                          </button>
                        </div>
                      )}

                      {planningState.status === 'PLAN_FAILED' && (
                        <div>
                          <button
                            onClick={() => handleRegeneratePlan(feature.id)}
                            className="rounded bg-yellow-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-yellow-700"
                          >
                            Retry (Regenerate)
                          </button>
                        </div>
                      )}

                      {planningState.status === 'QUEUED' && (
                        <p className="text-sm text-muted-foreground">
                          Feature is queued. Worker pipeline will pick it up.
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Failed to load planning state.</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
