<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    <div class="border-b border-slate-200 pb-5">
      <div class="flex items-center space-x-2">
        <h1 class="text-2xl font-bold text-slate-900">AI Matching Assistant</h1>      </div>
      <p class="text-sm text-slate-500">Suggested priorities and mentors for open requests. Everything here is advisory: IIC sends the
        availability check and approves the match.</p>
    </div>

    <div v-if="!auth.isLive" class="p-4 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-800">
      Sign in with an IIC account to use live AI suggestions.
    </div>
    <div v-else-if="error" class="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">{{ error }}</div>

    <div v-else class="grid lg:grid-cols-5 gap-6">
      <!-- Open requests with AI priority -->
      <div class="lg:col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div class="px-4 py-3 border-b border-slate-100">
          <div class="text-sm font-bold">Open requests ({{ open.length }})</div>
          <div class="text-[11px] text-slate-500 mt-0.5">Sangam is open to IITM BS Degree-level students only, so every request here is from a Degree-level student.</div>
        </div>
        <div class="max-h-[640px] overflow-y-auto divide-y divide-slate-100">
          <button v-for="r in open" :key="r.id" @click="select(r)"
                  class="w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors"
                  :class="selected?.id === r.id ? 'bg-blue-50' : ''">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-slate-900">#{{ r.id }} · {{ r.domain }}</span>
              <span v-if="priorities[r.id]" class="px-2 py-0.5 rounded-full text-[10px] font-bold" :class="prioClass(priorities[r.id].effective_priority)">
                {{ priorities[r.id].effective_priority }}
              </span>
            </div>
            <div class="text-[11px] text-slate-500 mt-0.5">{{ pathway(r.pathway) }} · {{ r.status.replace('_', ' ').toLowerCase() }}</div>
            <div class="text-[11px] text-slate-600 mt-1 line-clamp-2">{{ r.problem_statement }}</div>
          </button>
        </div>
      </div>

      <!-- Selected request: priority + suggestions -->
      <div class="lg:col-span-3 space-y-4">
        <div v-if="!selected" class="p-6 bg-white rounded-xl border border-dashed border-slate-300 text-sm text-slate-500 text-center">
          Pick a request to see its suggested priority and mentors.
        </div>
        <template v-else>
          <div class="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="text-xs text-slate-500">Request #{{ selected.id }} · {{ pathway(selected.pathway) }} · {{ selected.domain }}</div>
                <p class="text-sm text-slate-800 mt-1">{{ selected.problem_statement }}</p>
              </div>
            </div>
            <div v-if="prio" class="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
              <div class="flex items-center justify-between">
                <span>Suggested priority: <b>{{ prio.suggested_priority }}</b>
                  <span v-if="prio.override_priority"> · overridden to <b>{{ prio.override_priority }}</b> ({{ prio.override_reason }})</span></span>
                <span class="text-slate-400">{{ prio.algorithm }} · confidence {{ prio.confidence }}</span>
              </div>
              <div class="text-slate-600 mt-1">Why: {{ prio.explanation }}</div>
              <form class="flex gap-2 mt-2" @submit.prevent="override">
                <select v-model="ovr.priority" class="text-xs border border-slate-300 rounded px-2 py-1">
                  <option>HIGH</option><option>MEDIUM</option><option>LOW</option>
                </select>
                <input v-model="ovr.reason" placeholder="Reason for override" class="flex-1 text-xs border border-slate-300 rounded px-2 py-1" />
                <button class="text-xs px-3 py-1 rounded bg-slate-800 text-white disabled:opacity-50" :disabled="!ovr.reason">Override</button>
              </form>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200">
            <div class="flex items-center justify-between px-5 py-3 border-b border-slate-100">
              <span class="text-sm font-bold">Suggested mentors</span>
              <span v-if="sugg" class="text-[11px] px-2 py-0.5 rounded font-semibold"
                    :class="sugg.fallback ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'">
                {{ sugg.algorithm }}{{ sugg.fallback ? ' (fallback)' : '' }}{{ sugg.llm_explanations_used ? ' · Gemini explanations' : '' }}
              </span>
            </div>
            <div v-if="loadingSugg" class="px-5 py-6 text-xs text-slate-500">Ranking eligible mentors…</div>
            <div v-else class="divide-y divide-slate-100">
              <div v-for="(c, i) in sugg?.candidates || []" :key="c.mentor_id" class="px-5 py-4">
                <div class="flex items-center justify-between">
                  <div>
                    <span class="text-xs text-slate-400 mr-1">#{{ i + 1 }}</span>
                    <span class="text-sm font-bold text-slate-900">{{ c.name }}</span>
                    <span class="text-xs text-slate-500"> · {{ c.headline }}</span>
                  </div>
                  <span class="text-sm font-bold text-blue-700">{{ Math.round(c.score * 100) }}%</span>
                </div>
                <div class="text-[11px] text-slate-500">{{ c.specialty }} · {{ c.experience_years }} yrs</div>
                <p class="text-xs text-slate-700 mt-1.5">{{ c.explanation }}</p>
                <div class="flex flex-wrap gap-1.5 mt-2">
                  <span v-for="r in c.reasons" :key="r" class="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700">{{ r }}</span>
                </div>
              </div>
              <div v-if="sugg && !sugg.candidates.length" class="px-5 py-6 text-xs text-slate-500">No eligible mentors right now.</div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useAuthStore } from '../../stores/auth';
import { Sangam } from '../../api/client';

const auth = useAuthStore();
const requests = ref([]);
const priorities = reactive({});
const selected = ref(null);
const prio = ref(null);
const sugg = ref(null);
const loadingSugg = ref(false);
const error = ref('');
const ovr = reactive({ priority: 'HIGH', reason: '' });

const open = computed(() => requests.value.filter((r) => ['SUBMITTED', 'UNDER_REVIEW', 'WAITING'].includes(r.status)));
const pathway = (p) => ({ JOB: 'Job', HIGHER_STUDIES: 'Higher studies', VENTURE: 'Venture', UNSURE: 'Unsure' }[p] || p);
const prioClass = (p) => ({ HIGH: 'bg-rose-100 text-rose-800', MEDIUM: 'bg-amber-100 text-amber-800', LOW: 'bg-slate-100 text-slate-700' }[p]);

async function select(r) {
  selected.value = r;
  sugg.value = null;
  prio.value = priorities[r.id] || null;
  loadingSugg.value = true;
  try {
    const [p, s] = await Promise.all([prio.value ? Promise.resolve(prio.value) : Sangam.priority(r.id), Sangam.suggestions(r.id, 5)]);
    priorities[r.id] = p;
    prio.value = p;
    sugg.value = s;
  } catch (e) {
    error.value = e.message;
  } finally {
    loadingSugg.value = false;
  }
}

async function override() {
  prio.value = await Sangam.overridePriority(selected.value.id, ovr.priority, ovr.reason);
  priorities[selected.value.id] = prio.value;
  ovr.reason = '';
}

onMounted(async () => {
  if (!auth.isLive) return;
  try {
    requests.value = await Sangam.requests();
    // Load priority badges for the first few requests so the list is useful at a glance
    for (const r of open.value.slice(0, 12)) {
      Sangam.priority(r.id).then((p) => { priorities[r.id] = p; }).catch(() => {});
    }
  } catch (e) {
    error.value = `Could not load requests: ${e.message}`;
  }
});
</script>
