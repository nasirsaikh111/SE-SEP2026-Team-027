<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    
    <!-- Title -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">My Mentorship Requests</h1>
        <p class="text-sm text-slate-500">Track current review status, acceptances, and expiration countdowns.</p>
      </div>
      <div class="text-xs bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
        Active limit: <span class="font-bold text-slate-900">{{ store.activePendingRequestsCount }}/3 pending</span>
      </div>
    </div>

    <!-- Requests List -->
    <div v-if="store.myStudentRequests.length === 0" class="text-center py-16 bg-white rounded-xl border border-slate-200">
      <div class="text-3xl mb-2">📬</div>
      <h3 class="text-base font-bold text-slate-700">No requests submitted yet</h3>
      <p class="text-xs text-slate-500 mt-1 max-w-sm mx-auto">Browse verified mentors and send specific requests for structured guidance.</p>
      <router-link to="/student/discover" class="inline-block mt-4 px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg shadow-xs hover:bg-blue-700">
        Browse Mentors →
      </router-link>
    </div>

    <div v-else class="space-y-4">
      <div 
        v-for="req in store.myStudentRequests" 
        :key="req.id"
        class="bg-white rounded-xl border border-slate-200 shadow-xs p-5 hover:border-slate-300 transition-all"
      >
        <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          
          <div class="space-y-2 max-w-2xl">
            <!-- Mentor Name and Status Pill -->
            <div class="flex items-center space-x-3">
              <h3 class="text-base font-bold text-slate-900">{{ req.mentorName }}</h3>
              <span 
                class="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider"
                :class="{
                  'bg-emerald-100 text-emerald-800 border border-emerald-200': req.status === 'ACCEPTED',
                  'bg-amber-100 text-amber-800 border border-amber-200': req.status === 'PENDING',
                  'bg-rose-100 text-rose-800 border border-rose-200': req.status === 'DECLINED',
                  'bg-slate-100 text-slate-600 border border-slate-200': req.status === 'EXPIRED'
                }"
              >
                {{ req.status }}
              </span>
              <span v-if="req.status === 'PENDING' && req.expiryDaysLeft" class="text-xs text-amber-600 font-medium">
                ⏱️ {{ req.expiryDaysLeft }} days remaining
              </span>
            </div>

            <!-- Tags -->
            <div class="flex items-center space-x-2 text-xs text-slate-500">
              <span class="px-2 py-0.5 rounded bg-slate-100 font-medium">{{ req.domain }}</span>
              <span>•</span>
              <span>Pathway: {{ req.pathway }}</span>
              <span>•</span>
              <span>Submitted on {{ req.submittedAt }}</span>
            </div>

            <!-- Stated Question -->
            <div class="p-3 bg-slate-50 rounded-lg text-xs text-slate-700 border border-slate-100">
              <span class="font-semibold text-slate-900">Stated Question:</span> “{{ req.question }}”
            </div>

            <!-- Decline Reason if any -->
            <div v-if="req.status === 'DECLINED'" class="p-2.5 bg-rose-50 rounded-lg text-xs text-rose-700 border border-rose-100">
              <span class="font-bold">Mentor Note:</span> {{ req.declineReason }}
            </div>
          </div>

          <!-- Actions -->
          <div class="flex sm:flex-col items-center sm:items-end justify-end space-x-2 sm:space-x-0 sm:space-y-2">
            <template v-if="req.status === 'ACCEPTED'">
              <router-link 
                to="/student/workspace" 
                class="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 shadow-xs text-center min-w-[120px]"
              >
                Open Workspace →
              </router-link>
            </template>
            <template v-else-if="req.status === 'PENDING'">
              <button 
                @click="store.withdrawRequest(req.id)"
                class="px-4 py-2 bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-700 text-xs font-semibold rounded-lg transition-colors min-w-[120px]"
              >
                Withdraw Request
              </button>
            </template>
            <template v-else-if="req.status === 'DECLINED'">
              <router-link 
                to="/student/discover" 
                class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg text-center min-w-[120px]"
              >
                Find Similar Mentors
              </router-link>
            </template>
          </div>

        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { useMentorshipStore } from '../../stores/mentorship';

const store = useMentorshipStore();
</script>
