<template>
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Program Audit Log</h1>
        <p class="text-sm text-slate-500">Read-only immutable log of all status transitions, verifications, and pairings.</p>
      </div>
      <div class="text-xs bg-slate-100 text-slate-700 font-semibold px-3 py-1.5 rounded-lg border border-slate-200">
        {{ store.auditLogs.length }} Events Recorded
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
      <div class="flex items-center space-x-3 text-xs">
        <label class="font-bold text-slate-600">Filter by Actor:</label>
        <select v-model="actorFilter" class="p-1.5 border border-slate-300 rounded-lg">
          <option value="All">All Actors (Admin, Students, Mentors, System)</option>
          <option value="admin">Admin Actions Only</option>
          <option value="student">Student Actions</option>
          <option value="mentor">Mentor Actions</option>
          <option value="system">System Auto-Events</option>
        </select>
      </div>
      <span class="text-xs text-slate-400">Chronological Order (Newest First)</span>
    </div>

    <!-- Audit Table (From Wireframe) -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      <div class="p-4 bg-slate-50 border-b border-slate-200 grid grid-cols-12 text-xs font-bold text-slate-500 uppercase tracking-wider">
        <div class="col-span-3">Timestamp</div>
        <div class="col-span-3">Actor</div>
        <div class="col-span-6">Status Change / Action Details</div>
      </div>

      <div class="divide-y divide-slate-100">
        <div 
          v-for="log in filteredLogs" 
          :key="log.id"
          class="p-4 grid grid-cols-12 text-xs hover:bg-slate-50/70 items-center"
        >
          <div class="col-span-3 text-slate-500 font-medium">
            {{ log.date }}
          </div>
          <div class="col-span-3">
            <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-mono font-bold text-[11px]">
              {{ log.actor }}
            </span>
          </div>
          <div class="col-span-6">
            <div class="font-bold text-slate-900">{{ log.action }}</div>
            <div v-if="log.details" class="text-[11px] text-slate-500 mt-0.5">{{ log.details }}</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useMentorshipStore } from '../../stores/mentorship';

const store = useMentorshipStore();
const actorFilter = ref('All');

const filteredLogs = computed(() => {
  if (actorFilter.value === 'All') return store.auditLogs;
  return store.auditLogs.filter(l => l.actor.toLowerCase().includes(actorFilter.value.toLowerCase()));
});
</script>
