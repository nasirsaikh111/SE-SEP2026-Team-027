<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
    
    <!-- Header with Welcome -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Student Dashboard</h1>
        <p class="text-sm text-slate-500">Track your mentoring goals, browse verified alumni, and submit structured requests.</p>
      </div>
      <div class="flex items-center space-x-3">
        <router-link 
          to="/student/discover" 
          class="inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 shadow-xs transition-colors"
        >
          🔍 Browse Mentors
        </router-link>
      </div>
    </div>

    <!-- Active Mentorship Card (From Wireframe) -->
    <div class="bg-gradient-to-r from-blue-900 to-slate-900 rounded-xl p-6 text-white shadow-md">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-200 text-xs font-semibold mb-2 border border-blue-400/30">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>ACTIVE MENTORSHIP</span>
          </div>
          <h2 class="text-xl font-bold text-white">Mentor: {{ store.workspace.mentorName }}</h2>
          <p class="text-sm text-blue-200 mt-1">
            Progress: <span class="font-bold text-white">{{ store.completedGoalsCount }}/{{ store.totalGoalsCount }} goals completed</span> · Next session: <span class="font-bold text-white">{{ store.workspace.nextSession.date }} ({{ store.workspace.nextSession.time }})</span>
          </p>
        </div>
        <div class="flex items-center space-x-3">
          <router-link 
            to="/student/workspace" 
            class="px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition-colors shadow-xs"
          >
            Open Workspace →
          </router-link>
        </div>
      </div>
    </div>

    <!-- 2 Column Layout: Pathway Compass (Record Need) + Quick Stats & Requests -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      
      <!-- Pathway Compass / Record Mentoring Need (2 Columns) -->
      <div class="lg:col-span-2 bg-white rounded-xl p-6 border border-slate-200 shadow-xs">
        <div class="border-b border-slate-100 pb-4 mb-6">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-bold text-slate-900">🧭 Pathway Compass · Record a Mentoring Need</h3>
              <p class="text-xs text-slate-500 mt-0.5">Specify your concrete career question. Minimum 80 characters required to avoid vague requests.</p>
            </div>
            <span class="text-xs font-semibold px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded">
              Story 1.1
            </span>
          </div>
        </div>

        <form @submit.prevent="handleQuickNeedSubmit" class="space-y-5">
          
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <!-- Pathway -->
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1.5">Pathway</label>
              <select v-model="form.pathway" class="w-full text-sm rounded-lg border-slate-300 shadow-xs focus:border-blue-500 focus:ring-blue-500 p-2 border">
                <option value="Industry">Industry / Job</option>
                <option value="Higher Studies">Higher Studies (MS/PhD)</option>
                <option value="Venture">Startup / Venture</option>
                <option value="Unsure">Undecided / Exploring</option>
              </select>
            </div>

            <!-- Domain -->
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1.5">Target Domain</label>
              <select v-model="form.domain" class="w-full text-sm rounded-lg border-slate-300 shadow-xs focus:border-blue-500 focus:ring-blue-500 p-2 border">
                <option value="Data & ML">Data Science & ML</option>
                <option value="Analytics">Analytics & BI</option>
                <option value="Software">Software Engineering (SDE)</option>
                <option value="Product">Product Management</option>
              </select>
            </div>

            <!-- Urgency -->
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1.5">Urgency</label>
              <select v-model="form.urgency" class="w-full text-sm rounded-lg border-slate-300 shadow-xs focus:border-blue-500 focus:ring-blue-500 p-2 border">
                <option value="High">High (Graduating this term)</option>
                <option value="Medium">Medium (Internship prep)</option>
                <option value="Low">Low (Long-term exploration)</option>
              </select>
            </div>
          </div>

          <!-- Specific Question with min 80 chars validation -->
          <div>
            <div class="flex justify-between items-center mb-1.5">
              <label class="text-xs font-semibold text-slate-700">My Specific Question / Goal</label>
              <span class="text-xs" :class="form.question.length >= 80 ? 'text-emerald-600 font-semibold' : 'text-slate-400'">
                {{ form.question.length }} / 80 min chars
              </span>
            </div>
            <textarea
              v-model="form.question"
              rows="4"
              placeholder="e.g. I am entering term 6 of IITM BS and confused whether I should apply for non-tech data analyst internships now or complete all ML electives and build 2 full-stack portfolio projects before applying."
              class="w-full text-sm rounded-lg border-slate-300 shadow-xs focus:border-blue-500 focus:ring-blue-500 p-3 border"
              :class="{'border-red-300 focus:border-red-500 focus:ring-red-500': formError}"
            ></textarea>
            <p v-if="formError" class="text-xs text-red-600 mt-1 font-medium">{{ formError }}</p>
            <p v-else class="text-[11px] text-slate-500 mt-1">
              Mentors give 2–3 hours/month. Specific questions receive 3x faster acceptances than open-ended "please guide me" messages.
            </p>
          </div>

          <!-- Action buttons -->
          <div class="flex items-center justify-between pt-2">
            <span class="text-xs text-slate-500">
              Active pending requests: <span class="font-bold">{{ store.activePendingRequestsCount }}/3 max</span>
            </span>
            <button 
              type="submit" 
              class="px-5 py-2.5 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 transition-colors shadow-xs"
            >
              Find Matching Mentors →
            </button>
          </div>

        </form>
      </div>

      <!-- Right Column: My Requests Snapshot & Tips -->
      <div class="space-y-6">
        
        <!-- Requests Snapshot Card -->
        <div class="bg-white rounded-xl p-6 border border-slate-200 shadow-xs">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-bold text-slate-900">My Requests Snapshot</h3>
            <router-link to="/student/requests" class="text-xs font-semibold text-blue-600 hover:text-blue-800">
              View All ({{ store.myStudentRequests.length }})
            </router-link>
          </div>

          <div v-if="store.myStudentRequests.length === 0" class="text-center py-6 text-slate-400 text-xs">
            No active requests. Submit a need to get matched!
          </div>

          <div v-else class="space-y-3">
            <div 
              v-for="req in store.myStudentRequests.slice(0, 3)" 
              :key="req.id" 
              class="p-3 rounded-lg border border-slate-100 bg-slate-50/70 text-xs flex items-center justify-between"
            >
              <div>
                <div class="font-bold text-slate-900">{{ req.mentorName }}</div>
                <div class="text-[11px] text-slate-500 truncate max-w-[140px]">{{ req.domain }} · {{ req.urgency }}</div>
              </div>
              <span 
                class="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                :class="{
                  'bg-emerald-100 text-emerald-800': req.status === 'ACCEPTED',
                  'bg-amber-100 text-amber-800': req.status === 'PENDING',
                  'bg-red-100 text-red-800': req.status === 'DECLINED'
                }"
              >
                {{ req.status }}
              </span>
            </div>
          </div>
        </div>

        <!-- Wireframe Guidelines Card -->
        <div class="bg-slate-50 rounded-xl p-5 border border-slate-200 text-xs text-slate-600 space-y-2">
          <div class="font-bold text-slate-900 flex items-center space-x-1.5">
            <span>🛡️ Sangam Privacy Commitment</span>
          </div>
          <p>
            Your private 1-on-1 conversations with alumni are never stored or read by administrators. Only session dates, durations, and goals are recorded to measure program success.
          </p>
        </div>

      </div>

    </div>

  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useMentorshipStore } from '../../stores/mentorship';
import { useRouter } from 'vue-router';

const store = useMentorshipStore();
const router = useRouter();

const form = reactive({
  pathway: 'Industry',
  domain: 'Data & ML',
  urgency: 'High',
  question: ''
});

const formError = ref('');

function handleQuickNeedSubmit() {
  if (form.question.trim().length < 80) {
    formError.value = `Your question has ${form.question.trim().length} characters. Please provide at least 80 characters for specific context.`;
    return;
  }
  formError.value = '';
  // Navigate to discover mentors with domain pre-selected
  router.push({
    path: '/student/discover',
    query: {
      domain: form.domain,
      pathway: form.pathway,
      q: form.question
    }
  });
}
</script>
