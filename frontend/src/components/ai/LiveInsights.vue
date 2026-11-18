<template>
  <div class="space-y-6">
    <div v-if="error" class="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">{{ error }}</div>
    <div v-else-if="!data" class="text-xs text-slate-500">Loading live insights…</div>

    <template v-else>
      <!-- KPI tiles from GET /admin/insights/ -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div v-for="k in kpis" :key="k.label" class="bg-white p-5 rounded-xl border border-slate-200">
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wide">{{ k.label }}</div>
          <div class="text-3xl font-bold mt-1" :class="k.color">{{ k.value }}</div>
          <div class="text-[11px] text-slate-400 mt-1">{{ k.hint }}</div>
        </div>
      </div>

      <div class="grid lg:grid-cols-2 gap-6">
        <div class="bg-white p-5 rounded-xl border border-slate-200">
          <h3 class="text-sm font-bold text-slate-900 mb-3">Effectiveness</h3>
          <dl class="text-xs space-y-2">
            <div class="flex justify-between"><dt class="text-slate-500">Meetings per mentorship</dt><dd class="font-semibold">{{ data.effectiveness.meetings_per_mentorship }}</dd></div>
            <div class="flex justify-between"><dt class="text-slate-500">Goals completed</dt><dd class="font-semibold">{{ pct(data.effectiveness.goals_completed_share) }}</dd></div>
            <div class="flex justify-between"><dt class="text-slate-500">Feedback on time</dt><dd class="font-semibold">{{ pct(data.effectiveness.feedback_on_time_share) }}</dd></div>
            <div class="flex justify-between"><dt class="text-slate-500">Mentor acceptance rate</dt><dd class="font-semibold">{{ pct(data.participation.request_acceptance_rate) }}</dd></div>
            <div class="flex justify-between"><dt class="text-slate-500">Avg days request → match</dt><dd class="font-semibold">{{ data.participation.avg_days_request_to_match ?? '—' }}</dd></div>
          </dl>
        </div>
        <div class="bg-white p-5 rounded-xl border border-slate-200">
          <h3 class="text-sm font-bold text-slate-900 mb-3">Student demand by domain</h3>
          <div v-for="d in data.participation.popular_domains.slice(0, 6)" :key="d.domain" class="mb-2">
            <div class="flex justify-between text-xs mb-1"><span>{{ d.domain }}</span><span class="text-slate-500">{{ d.count }}</span></div>
            <div class="h-2 bg-slate-100 rounded-full"><div class="h-2 bg-blue-600 rounded-full" :style="{ width: (100 * d.count / maxDomain) + '%' }"></div></div>
          </div>
        </div>
      </div>

      <!-- At-risk mentorships from GET /admin/insights/at-risk/ -->
      <div class="bg-white rounded-xl border border-slate-200">
        <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <h3 class="text-sm font-bold text-slate-900">Mentorships that may be going quiet</h3>
            <p class="text-[11px] text-slate-500">Advisory only · {{ risk?.algorithm }} · flags never change any status</p>
          </div>
          <span class="text-xs font-semibold px-2 py-1 rounded bg-rose-50 text-rose-700">{{ risk?.count ?? 0 }} flagged</span>
        </div>
        <table class="w-full text-xs">
          <thead class="bg-slate-50 text-slate-500 text-left">
            <tr><th class="px-5 py-2">Mentorship</th><th class="px-3 py-2">Risk</th><th class="px-3 py-2">Score</th><th class="px-3 py-2">Why</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in risk?.results || []" :key="r.mentorship_id" class="border-t border-slate-100 align-top">
              <td class="px-5 py-2.5 font-semibold">#{{ r.mentorship_id }}</td>
              <td class="px-3 py-2.5"><span class="px-2 py-0.5 rounded-full font-bold text-[10px]" :class="levelClass(r.risk_level)">{{ r.risk_level }}</span></td>
              <td class="px-3 py-2.5">{{ r.risk_score.toFixed(2) }}</td>
              <td class="px-3 py-2.5 text-slate-600">{{ r.reasons.join(' · ') }}</td>
            </tr>
            <tr v-if="!(risk?.results || []).length"><td colspan="4" class="px-5 py-4 text-slate-500">No mentorships flagged.</td></tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { Sangam } from '../../api/client';

const data = ref(null);
const risk = ref(null);
const error = ref('');

const pct = (x) => `${Math.round((x || 0) * 100)}%`;
const levelClass = (l) => ({ HIGH: 'bg-rose-100 text-rose-800', MEDIUM: 'bg-amber-100 text-amber-800', LOW: 'bg-emerald-100 text-emerald-800' }[l]);
const maxDomain = computed(() => Math.max(1, ...(data.value?.participation.popular_domains || []).map((d) => d.count)));
const kpis = computed(() => {
  const p = data.value.participation;
  return [
    { label: 'Open requests', value: p.open_requests, hint: `${p.total_requests} total this term`, color: 'text-blue-600' },
    { label: 'Verified mentors', value: p.verified_mentors, hint: `${p.approved_students} approved students`, color: 'text-emerald-600' },
    { label: 'Active mentorships', value: p.active_mentorships, hint: `${p.meetings_held} meetings held`, color: 'text-purple-600' },
    { label: 'At risk', value: data.value.at_risk_count, hint: 'medium or high drop-off risk', color: 'text-rose-600' },
  ];
});

onMounted(async () => {
  try {
    [data.value, risk.value] = await Promise.all([Sangam.insights(), Sangam.atRisk('MEDIUM')]);
  } catch (e) {
    error.value = `Could not load insights: ${e.message}`;
  }
});
</script>
