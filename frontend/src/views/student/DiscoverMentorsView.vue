<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Discover Mentors</h1>
        <p class="text-sm text-slate-500">Filter verified alumni by domain, role, and current open mentee capacity.</p>
      </div>
      <div class="flex items-center space-x-2 text-xs text-slate-500 bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-100">
        <span>Active Pending Requests:</span>
        <span class="font-bold text-blue-800">{{ store.activePendingRequestsCount }}/3 max</span>
      </div>
    </div>

    <!-- Filter Bar (Directly from Wireframe) -->
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
      
      <div class="flex flex-wrap items-center gap-4">
        <!-- Pathway Filter -->
        <div class="flex items-center space-x-2">
          <label class="text-xs font-semibold text-slate-600">Pathway:</label>
          <select v-model="selectedPathway" class="text-xs rounded-lg border-slate-300 shadow-xs p-1.5 border">
            <option value="All">All Pathways</option>
            <option value="Industry">Industry</option>
            <option value="Higher Studies">Higher Studies</option>
            <option value="Venture">Venture / Startup</option>
          </select>
        </div>

        <!-- Domain Filter -->
        <div class="flex items-center space-x-2">
          <label class="text-xs font-semibold text-slate-600">Domain:</label>
          <select v-model="selectedDomain" class="text-xs rounded-lg border-slate-300 shadow-xs p-1.5 border">
            <option value="All">All Domains</option>
            <option value="Data & ML">Data & ML</option>
            <option value="Analytics">Analytics</option>
            <option value="Software">Software Engineering</option>
          </select>
        </div>

        <!-- Open Slot Checkbox -->
        <label class="flex items-center space-x-2 text-xs font-semibold text-slate-700 cursor-pointer select-none">
          <input type="checkbox" v-model="onlyOpenSlots" class="rounded text-blue-600 focus:ring-blue-500">
          <span>Open slot available only</span>
        </label>
      </div>

      <!-- Result Count -->
      <div class="text-xs font-medium text-slate-500">
        Showing {{ filteredMentors.length }} verified mentors
      </div>
    </div>

    <!-- Mentors Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div 
        v-for="mentor in filteredMentors" 
        :key="mentor.id"
        class="bg-white rounded-xl border border-slate-200 shadow-xs p-5 flex flex-col justify-between hover:shadow-md transition-shadow relative"
      >
        <!-- Card Top -->
        <div>
          <div class="flex items-start justify-between gap-2 mb-3">
            <div>
              <div class="flex items-center space-x-1.5">
                <h3 class="font-bold text-slate-900 text-base">{{ mentor.name }}</h3>
                <span v-if="mentor.verified" class="text-blue-600 text-xs" title="Verified Alumni">✓</span>
              </div>
              <div class="text-xs text-slate-500 font-medium">{{ mentor.role }} @ {{ mentor.company }}</div>
              <div class="text-[11px] text-slate-400">Class of {{ mentor.gradYear }} · IITM BS</div>
            </div>

            <!-- Match Score Badge -->
            <div class="px-2 py-1 rounded-md bg-blue-50 text-blue-700 font-bold text-xs border border-blue-100 flex flex-col items-center">
              <span>{{ mentor.matchScore }}%</span>
              <span class="text-[9px] font-normal text-slate-400">match</span>
            </div>
          </div>

          <!-- Headline & Reason -->
          <p class="text-xs text-slate-600 mb-3 line-clamp-2">
            {{ mentor.headline }}
          </p>

          <!-- "Why this match" Pill -->
          <div class="mb-4 p-2 rounded-md bg-slate-50 border border-slate-100 text-[11px] text-slate-500">
            <span class="font-semibold text-slate-700">Why this match:</span> {{ mentor.matchReason }}
          </div>

          <!-- Expertise Chips -->
          <div class="flex flex-wrap gap-1.5 mb-4">
            <span 
              v-for="skill in mentor.expertise" 
              :key="skill"
              class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px] font-medium"
            >
              {{ skill }}
            </span>
          </div>
        </div>

        <!-- Card Bottom -->
        <div class="pt-4 border-t border-slate-100 flex items-center justify-between">
          <div class="text-xs">
            <div class="font-semibold" :class="mentor.activeMentees >= mentor.capacity ? 'text-amber-600' : 'text-slate-700'">
              Capacity: {{ mentor.activeMentees }}/{{ mentor.capacity }}
              <span v-if="mentor.activeMentees >= mentor.capacity" class="text-[10px] font-bold text-amber-600">(Full)</span>
            </div>
            <div class="text-[11px] text-slate-400">{{ mentor.officeHours.join(', ') }}</div>
          </div>

          <button 
            @click="openRequestModal(mentor)"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-xs transition-colors"
            :class="mentor.activeMentees >= mentor.capacity 
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
              : 'bg-blue-600 text-white hover:bg-blue-700'"
            :disabled="mentor.activeMentees >= mentor.capacity"
          >
            {{ mentor.activeMentees >= mentor.capacity ? 'Full / Waitlist' : 'Send Request' }}
          </button>
        </div>

      </div>
    </div>

    <!-- Request Modal (Artboard: Mentor Profile + Request) -->
    <div v-if="activeModalMentor" class="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
        
        <div class="flex items-start justify-between pb-4 border-b border-slate-100">
          <div>
            <h2 class="text-lg font-bold text-slate-900">Request Mentorship with {{ activeModalMentor.name }}</h2>
            <p class="text-xs text-slate-500">{{ activeModalMentor.role }} · {{ activeModalMentor.domain }}</p>
          </div>
          <button @click="activeModalMentor = null" class="text-slate-400 hover:text-slate-600 text-lg font-bold">✕</button>
        </div>

        <form @submit.prevent="submitMentorshipRequest" class="mt-4 space-y-4">
          
          <div class="p-3 bg-blue-50/70 border border-blue-100 rounded-lg text-xs text-blue-800 space-y-1">
            <div class="font-bold">Important Guidelines:</div>
            <div>• Requests auto-expire after 7 days without a response (Story 1.4).</div>
            <div>• Maximum 3 pending requests allowed concurrently.</div>
          </div>

          <div>
            <div class="flex justify-between items-center mb-1">
              <label class="text-xs font-semibold text-slate-700">Intro message & Specific question</label>
              <span class="text-xs" :class="reqQuestion.length >= 80 ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                {{ reqQuestion.length }} / 80 min characters
              </span>
            </div>
            <textarea
              v-model="reqQuestion"
              rows="4"
              placeholder="Explain your background, target companies or roles, and the specific 1-2 questions you'd like to work on together..."
              class="w-full text-xs rounded-lg border-slate-300 shadow-xs focus:border-blue-500 focus:ring-blue-500 p-3 border"
            ></textarea>
            <p v-if="modalError" class="text-xs text-red-600 font-medium mt-1">{{ modalError }}</p>
          </div>

          <div class="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
            <button 
              type="button" 
              @click="activeModalMentor = null" 
              class="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              class="px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs"
            >
              Send Request
            </button>
          </div>

        </form>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useMentorshipStore } from '../../stores/mentorship';
import { useRoute, useRouter } from 'vue-router';

const store = useMentorshipStore();
const route = useRoute();
const router = useRouter();

const selectedPathway = ref(route.query.pathway || 'All');
const selectedDomain = ref(route.query.domain || 'All');
const onlyOpenSlots = ref(false);

const activeModalMentor = ref(null);
const reqQuestion = ref(route.query.q || '');
const modalError = ref('');

const filteredMentors = computed(() => {
  return store.verifiedMentors.filter(m => {
    if (selectedPathway.value !== 'All' && m.pathway !== selectedPathway.value) return false;
    if (selectedDomain.value !== 'All' && m.domain !== selectedDomain.value) return false;
    if (onlyOpenSlots.value && m.activeMentees >= m.capacity) return false;
    return true;
  });
});

function openRequestModal(mentor) {
  activeModalMentor.value = mentor;
  modalError.value = '';
}

function submitMentorshipRequest() {
  try {
    store.submitRequest({
      mentorId: activeModalMentor.value.id,
      domain: activeModalMentor.value.domain,
      pathway: activeModalMentor.value.pathway,
      urgency: 'Medium',
      question: reqQuestion.value
    });
    activeModalMentor.value = null;
    router.push('/student/requests');
  } catch (err) {
    modalError.value = err.message;
  }
}
</script>
