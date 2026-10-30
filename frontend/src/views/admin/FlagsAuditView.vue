<template>
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Safety & Flagged Incident Reports</h1>
        <p class="text-sm text-slate-500">Review reported messages and misconduct incidents without exposing unrelated private conversations.</p>
      </div>
      <div class="text-xs bg-rose-50 text-rose-800 font-semibold px-3 py-1.5 rounded-lg border border-rose-200">
        {{ store.flags.length }} Incidents On File
      </div>
    </div>

    <!-- Flags Table (From Wireframe) -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      <div class="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
        <span>Reporter & Target Entity</span>
        <span>Reason & Action</span>
      </div>

      <div class="divide-y divide-slate-100">
        <div 
          v-for="flag in store.flags" 
          :key="flag.id"
          class="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/50"
        >
          <div class="space-y-1">
            <div class="flex items-center space-x-2">
              <span class="font-bold text-slate-900 text-sm">Reported by: {{ flag.reporterName }} ({{ flag.reporterRole }})</span>
              <span 
                class="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                :class="flag.status === 'OPEN' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-600'"
              >
                {{ flag.status }}
              </span>
            </div>
            <div class="text-xs text-slate-600">
              Target: <strong class="text-slate-800">{{ flag.targetType }}</strong> · {{ flag.reportedAt }}
            </div>
            <div class="text-xs text-rose-700 font-medium">
              Flagged for: “{{ flag.reason }}”
            </div>
          </div>

          <button 
            @click="activeFlag = flag"
            class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg shadow-xs"
          >
            Review Incident Details →
          </button>
        </div>
      </div>
    </div>

    <!-- Flag Detail Modal (Wireframe Artboard: Flag Detail) -->
    <div v-if="activeFlag" class="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
        
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 class="font-bold text-slate-900 text-base">Incident Investigation</h3>
            <p class="text-xs text-slate-400">ID: {{ activeFlag.id }} · Target: {{ activeFlag.targetType }}</p>
          </div>
          <button @click="activeFlag = null" class="text-slate-400 hover:text-slate-600 font-bold">✕</button>
        </div>

        <div class="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 space-y-1">
          <div class="font-bold">Flagged Content Snippet:</div>
          <p class="italic">“{{ activeFlag.context }}”</p>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Administrator Resolution Note</label>
          <textarea 
            v-model="resolutionNote"
            rows="3" 
            placeholder="Document action taken (e.g. Issued official policy warning to user for off-platform solicitation)..."
            class="w-full text-xs p-2.5 rounded-lg border border-slate-300"
          ></textarea>
        </div>

        <div class="flex items-center justify-between pt-3 border-t border-slate-100">
          <button 
            @click="resolve(activeFlag.id, 'Suspended User')"
            class="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg shadow-xs"
          >
            Suspend User
          </button>

          <div class="flex space-x-2">
            <button @click="activeFlag = null" class="px-3 py-2 text-xs text-slate-600">Cancel</button>
            <button 
              @click="resolve(activeFlag.id, 'Warned & Resolved')"
              class="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs"
            >
              Warn & Resolve
            </button>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useMentorshipStore } from '../../stores/mentorship';

const store = useMentorshipStore();
const activeFlag = ref(null);
const resolutionNote = ref('');

function resolve(flagId, action) {
  store.resolveFlag(flagId, action + (resolutionNote.value ? `: ${resolutionNote.value}` : ''));
  activeFlag.value = null;
  resolutionNote.value = '';
  alert(`Incident resolved with action: ${action}`);
}
</script>
