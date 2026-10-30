<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
    
    <!-- Top Bar -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Mentor Dashboard</h1>
        <p class="text-sm text-slate-500">Welcome back, Arjun! Manage your active mentees and review incoming requests.</p>
      </div>

      <!-- Capacity & Pause Control (Story 2.2) -->
      <div class="flex items-center space-x-4 bg-white p-2.5 rounded-xl border border-slate-200 shadow-xs">
        <div class="text-xs">
          <span class="text-slate-500">Mentee Capacity:</span>
          <span class="font-bold text-slate-900 ml-1">1 / 3 mentees</span>
        </div>
        <button 
          @click="togglePause"
          class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
          :class="isPaused ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'"
        >
          {{ isPaused ? '⏸️ Requests Paused' : 'Active (Accepting)' }}
        </button>
      </div>
    </div>

    <!-- Impact & Metrics Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Impact</div>
        <div class="text-3xl font-extrabold text-blue-600 mt-2">11</div>
        <div class="text-xs text-slate-400 mt-1">Students mentored to graduation</div>
      </div>
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Average Mentee Rating</div>
        <div class="text-3xl font-extrabold text-amber-500 mt-2">4.7 <span class="text-base font-normal">/ 5.0</span></div>
        <div class="text-xs text-slate-400 mt-1">Based on 9 verified session ratings</div>
      </div>
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Monthly Time Committed</div>
        <div class="text-3xl font-extrabold text-emerald-600 mt-2">2.5 <span class="text-base font-normal">hrs</span></div>
        <div class="text-xs text-slate-400 mt-1">Well within 2–3 hours/month target</div>
      </div>
    </div>

    <!-- Incoming Mentorship Requests (Wireframe Artboard: Review Request) -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      <div class="p-6 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 class="text-base font-bold text-slate-900">Incoming Mentorship Requests</h2>
          <p class="text-xs text-slate-500">Students approaching graduation who requested guidance tailored to your experience.</p>
        </div>
        <span class="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
          {{ pendingRequests.length }} Pending
        </span>
      </div>

      <div v-if="pendingRequests.length === 0" class="p-10 text-center text-slate-400 text-xs">
        No pending requests at this time.
      </div>

      <div v-else class="divide-y divide-slate-100">
        <div 
          v-for="req in pendingRequests" 
          :key="req.id"
          class="p-6 flex flex-col md:flex-row md:items-start justify-between gap-6 hover:bg-slate-50/50 transition-colors"
        >
          <div class="space-y-3 max-w-3xl">
            <div class="flex items-center space-x-3">
              <h3 class="font-bold text-slate-900 text-base">{{ req.studentName }}</h3>
              <span class="text-xs text-slate-400">Roll: {{ req.studentRoll }}</span>
              <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-semibold">
                {{ req.domain }} Track
              </span>
              <span class="text-xs text-amber-600 font-medium">
                ⏱️ 5 days left to review
              </span>
            </div>

            <!-- Stated Question (Min 80 chars) -->
            <div class="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
              <div class="font-semibold text-slate-900">Mentee Question & Specific Need:</div>
              <p class="italic">“{{ req.question }}”</p>
            </div>
          </div>

          <!-- Decision Action Buttons (Story 2.3) -->
          <div class="flex sm:flex-col items-center sm:items-end justify-end space-x-2 sm:space-x-0 sm:space-y-2 min-w-[140px]">
            <button 
              @click="acceptRequest(req.id)"
              class="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              Accept Mentee
            </button>
            <button 
              @click="openDeclineModal(req)"
              class="w-full px-4 py-2 bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-700 text-xs font-semibold rounded-lg transition-colors border border-slate-200"
            >
              Decline...
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Active Mentees Snapshot -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-base font-bold text-slate-900">Current Active Mentees</h2>
          <p class="text-xs text-slate-500">Track shared goal progress and upcoming calls.</p>
        </div>
        <router-link to="/mentor/workspace" class="text-xs font-bold text-blue-600 hover:underline">
          Open Mentor Workspace →
        </router-link>
      </div>

      <div class="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 class="text-sm font-bold text-slate-900">Hemant Dhayal (Degree Student)</h3>
          <p class="text-xs text-slate-500 mt-0.5">Focus: Data Science Internship & Portfolio Project Audit</p>
          <div class="text-xs text-slate-600 mt-2 font-medium">
            Goals Progress: <span class="text-emerald-700 font-bold">2 / 4 completed</span> · Next call: <span class="font-bold">Thu, 31 Oct (6:30 PM)</span>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <router-link 
            to="/mentor/workspace"
            class="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs"
          >
            Manage Mentees
          </router-link>
        </div>
      </div>
    </div>

    <!-- Decline Reason Modal (Wireframe requirement: decline reason mandatory) -->
    <div v-if="declineModalReq" class="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
        <h3 class="font-bold text-slate-900 text-base">Decline Request</h3>
        <p class="text-xs text-slate-500 mt-1">Please provide a constructive reason so the student can find a better-suited mentor.</p>

        <div class="mt-4 space-y-3">
          <label class="block text-xs font-semibold text-slate-700">Reason</label>
          <select v-model="declineReason" class="w-full text-xs p-2 rounded-lg border border-slate-300">
            <option value="At full capacity for this term">At full capacity for this term</option>
            <option value="Request is outside my domain expertise">Request is outside my domain expertise</option>
            <option value="Stated question was too general; please refine">Stated question was too general; please refine</option>
            <option value="Timezone / office hour clash">Timezone / office hour clash</option>
          </select>

          <div class="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
            <button @click="declineModalReq = null" class="px-4 py-2 text-xs font-semibold text-slate-600">Cancel</button>
            <button @click="confirmDecline" class="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg shadow-xs">
              Confirm Decline
            </button>
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
const isPaused = ref(false);

const declineModalReq = ref(null);
const declineReason = ref('At full capacity for this term');

const pendingRequests = computed(() => {
  return store.requests.filter(r => r.mentorId === 'mentor-1' && r.status === 'PENDING');
});

function togglePause() {
  isPaused.value = !isPaused.value;
  store.addAuditLog('mentor (Arjun K.)', isPaused.value ? 'Paused new requests' : 'Resumed accepting requests');
}

function acceptRequest(id) {
  store.acceptRequest(id);
  alert('Request accepted! The student has been notified and added to your workspace.');
}

function openDeclineModal(req) {
  declineModalReq.value = req;
}

function confirmDecline() {
  if (declineModalReq.value) {
    store.declineRequest(declineModalReq.value.id, declineReason.value);
    declineModalReq.value = null;
  }
}
</script>
