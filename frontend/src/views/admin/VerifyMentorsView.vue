<template>
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
      <div>
        <div class="flex items-center space-x-2">
          <h1 class="text-2xl font-bold text-slate-900">Alumni Verification Queue</h1>
          <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-xs font-bold">
            Story 3.3
          </span>
        </div>
        <p class="text-sm text-slate-500 mt-0.5">
          Verify alumni identity against the IITM BS graduate roll number database before profiles appear in search.
        </p>
      </div>
      <div class="text-xs bg-amber-50 text-amber-800 font-semibold px-3 py-1.5 rounded-lg border border-amber-200">
        {{ store.pendingVerificationMentors.length }} Profiles Awaiting Verification
      </div>
    </div>

    <!-- Table of Pending Verifications -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      <div class="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
        <span>Mentor Candidate & Submitted Credentials</span>
        <span>Institute Alumni DB Match</span>
      </div>

      <div v-if="store.pendingVerificationMentors.length === 0" class="p-12 text-center text-slate-400 text-xs">
        ✅ All alumni registrations are verified. No pending profiles.
      </div>

      <div v-else class="divide-y divide-slate-100">
        <div 
          v-for="mentor in store.pendingVerificationMentors" 
          :key="mentor.id"
          class="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/50 transition-colors"
        >
          <div class="space-y-1">
            <div class="flex items-center space-x-2">
              <h3 class="font-bold text-slate-900 text-sm">{{ mentor.name }}</h3>
              <span class="text-xs text-slate-500">{{ mentor.role }} @ {{ mentor.company }}</span>
            </div>
            <div class="text-xs text-slate-600 flex items-center space-x-3">
              <span>Roll No: <code class="bg-slate-100 px-1.5 py-0.5 rounded font-mono">{{ mentor.rollNo }}</code></span>
              <span>•</span>
              <span>Graduation Year: <strong>{{ mentor.gradYear }}</strong></span>
              <span>•</span>
              <span class="text-blue-600">LinkedIn: verified_alumni_link</span>
            </div>
            <div class="text-[11px] text-slate-400">
              Expertise: {{ mentor.expertise.join(', ') }}
            </div>
          </div>

          <div class="flex items-center space-x-4">
            <!-- Simulated Institute DB Check Pill -->
            <div class="text-right">
              <span class="px-2.5 py-1 rounded text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center space-x-1">
                <span>✓</span>
                <span>DB MATCH CONFIRMED</span>
              </span>
              <div class="text-[10px] text-slate-400 mt-1">Found in Convocation 2024 List</div>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center space-x-2">
              <button 
                @click="verify(mentor.id)"
                class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
              >
                Verify & Publish
              </button>
              <button 
                @click="reject(mentor.id)"
                class="px-3 py-2 bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-700 text-xs font-semibold rounded-lg transition-colors border border-slate-200"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Verified Mentors Roster (Read-only list) -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
      <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">Live & Verified Alumni Mentors ({{ store.verifiedMentors.length }})</h2>
      
      <div class="divide-y divide-slate-100">
        <div v-for="m in store.verifiedMentors" :key="m.id" class="py-3 flex items-center justify-between text-xs">
          <div>
            <span class="font-bold text-slate-900">{{ m.name }}</span>
            <span class="text-slate-500 ml-2">({{ m.role }} @ {{ m.company }})</span>
            <span class="text-slate-400 ml-2">Roll: {{ m.rollNo }}</span>
          </div>
          <span class="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold text-[11px]">
            Verified
          </span>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { useMentorshipStore } from '../../stores/mentorship';

const store = useMentorshipStore();

function verify(id) {
  store.verifyMentor(id);
  alert('Mentor successfully verified! Their profile is now live in Discover Mentors.');
}

function reject(id) {
  if (confirm('Are you sure you want to reject this profile?')) {
    store.rejectMentor(id);
  }
}
</script>
