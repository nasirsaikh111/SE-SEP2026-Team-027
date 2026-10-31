<template>
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    
    <!-- Top Workspace Banner -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center space-x-2">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
            Active Mentorship
          </span>
          <span class="text-xs text-slate-400">Pairing #208</span>
        </div>
        <h1 class="text-2xl font-bold text-slate-900 mt-1">Mentor: {{ store.workspace.mentorName }}</h1>
        <p class="text-xs text-slate-500 mt-0.5">Senior Data Scientist @ Fractal Analytics · Data Science & ML Track</p>
      </div>

      <!-- Next Session Callout -->
      <div class="flex items-center space-x-4 bg-blue-50/70 border border-blue-100 p-4 rounded-xl">
        <div>
          <div class="text-[11px] font-semibold text-blue-700 uppercase tracking-wide">Next Session</div>
          <div class="text-sm font-bold text-slate-900">{{ store.workspace.nextSession.date }}</div>
          <div class="text-xs text-slate-500">{{ store.workspace.nextSession.time }}</div>
        </div>
        <a 
          :href="store.workspace.nextSession.link" 
          target="_blank"
          class="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 shadow-xs flex items-center space-x-1"
        >
          <span>Join Meet</span>
          <span>↗</span>
        </a>
      </div>
    </div>

    <!-- Workspace Tabs: Goals | Sessions | Shared Notes -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      
      <!-- Tab Headers -->
      <div class="flex border-b border-slate-200 bg-slate-50/50">
        <button 
          v-for="tab in ['goals', 'sessions', 'notes', 'outcomes']" 
          :key="tab"
          @click="activeTab = tab"
          class="px-6 py-3.5 text-xs font-bold uppercase tracking-wider transition-colors border-b-2"
          :class="activeTab === tab ? 'border-blue-600 text-blue-700 bg-white' : 'border-transparent text-slate-500 hover:text-slate-800'"
        >
          {{ tab === 'goals' ? `Shared Goals (${store.completedGoalsCount}/${store.totalGoalsCount})` : tab === 'sessions' ? `Session Logs (${store.workspace.sessions.length})` : tab === 'notes' ? 'Shared Notes' : 'Record Outcomes' }}
        </button>
      </div>

      <div class="p-6">
        
        <!-- Tab 1: Shared Goals (Story 4.1) -->
        <div v-if="activeTab === 'goals'" class="space-y-6">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-bold text-slate-900">Agreed Mentoring Milestones</h3>
              <p class="text-xs text-slate-500">Agree on 2 to 3 target goals with your mentor to keep mentoring focused alongside coursework.</p>
            </div>
            <button 
              @click="showAddGoal = !showAddGoal" 
              class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition-colors"
            >
              + Add Goal
            </button>
          </div>

          <!-- Add Goal Form -->
          <div v-if="showAddGoal" class="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-col sm:flex-row gap-3 items-end">
            <div class="flex-1 w-full">
              <label class="block text-xs font-semibold text-slate-700 mb-1">Goal Description</label>
              <input v-model="newGoalTitle" placeholder="e.g. Complete DSA tree problems set" class="w-full text-xs p-2 rounded-lg border border-slate-300">
            </div>
            <div class="w-full sm:w-48">
              <label class="block text-xs font-semibold text-slate-700 mb-1">Target Date</label>
              <input type="date" v-model="newGoalDate" class="w-full text-xs p-2 rounded-lg border border-slate-300">
            </div>
            <button @click="handleAddGoal" class="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg shadow-xs hover:bg-blue-700 w-full sm:w-auto">
              Save Goal
            </button>
          </div>

          <!-- Goals List -->
          <div class="space-y-3">
            <div 
              v-for="goal in store.workspace.goals" 
              :key="goal.id"
              class="p-4 rounded-xl border transition-all flex items-center justify-between"
              :class="goal.completed ? 'bg-slate-50/70 border-slate-200 opacity-80' : 'bg-white border-blue-100 shadow-xs'"
            >
              <label class="flex items-center space-x-3 cursor-pointer">
                <input 
                  type="checkbox" 
                  :checked="goal.completed" 
                  @change="store.toggleGoal(goal.id)"
                  class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer"
                >
                <span class="text-xs font-semibold" :class="goal.completed ? 'line-through text-slate-400' : 'text-slate-800'">
                  {{ goal.title }}
                </span>
              </label>

              <div class="flex items-center space-x-2 text-[11px] text-slate-400">
                <span>Target: {{ goal.targetDate }}</span>
                <span v-if="goal.completed" class="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold">Done</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab 2: Sessions Log (Story 4.2 & Privacy Guarantee) -->
        <div v-else-if="activeTab === 'sessions'" class="space-y-6">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-bold text-slate-900">Session Engagement Log</h3>
              <p class="text-xs text-slate-500">Tracks that meetings happen without storing conversational discussions.</p>
            </div>
            <button 
              @click="showRatingModal = true"
              class="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              ⭐ Rate Last Session
            </button>
          </div>

          <div class="space-y-3">
            <div 
              v-for="sess in store.workspace.sessions" 
              :key="sess.id"
              class="p-4 rounded-xl border border-slate-200 bg-white flex items-center justify-between"
            >
              <div>
                <div class="text-xs font-bold text-slate-900">{{ sess.date }}</div>
                <div class="text-[11px] text-slate-500">Duration: {{ sess.duration }}</div>
              </div>
              <div class="flex items-center space-x-3">
                <span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold uppercase">
                  {{ sess.status }}
                </span>
                <button 
                  @click="showRatingModal = true"
                  class="text-xs text-blue-600 hover:underline font-semibold"
                >
                  Rate session
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab 3: Shared Notes -->
        <div v-else-if="activeTab === 'notes'" class="space-y-4">
          <h3 class="text-sm font-bold text-slate-900">Shared Mentoring Notes & Action Items</h3>
          <p class="text-xs text-slate-500">Visible to both student and mentor. Use this for reading lists and project links.</p>
          <textarea 
            v-model="store.workspace.sharedNotes"
            rows="6"
            class="w-full text-xs p-3 rounded-xl border border-slate-300 shadow-xs focus:ring-blue-500 focus:border-blue-500"
          ></textarea>
          <div class="text-right">
            <button class="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg shadow-xs">
              Save Notes
            </button>
          </div>
        </div>

        <!-- Tab 4: Record Outcomes (Story 5.2) -->
        <div v-else-if="activeTab === 'outcomes'" class="space-y-4">
          <div class="p-4 bg-emerald-50 rounded-xl border border-emerald-200">
            <h3 class="text-sm font-bold text-emerald-900">🎯 Record Career Impact & Tangible Outcomes</h3>
            <p class="text-xs text-emerald-700 mt-1">
              Did this mentorship help you secure an internship, pass an interview round, or switch roles? Record it here to prove the platform's impact.
            </p>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Outcome Type</label>
              <select v-model="outcomeType" class="w-full text-xs p-2 rounded-lg border border-slate-300">
                <option value="internship">Internship / Full-time Offer Secured</option>
                <option value="interview">Company Technical Round Cleared</option>
                <option value="portfolio">Shipped Capstone Project</option>
                <option value="grad">Admitted to Masters / Higher Studies</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Organization / Details</label>
              <input v-model="outcomeCompany" placeholder="e.g. Cleared Amazon SDE 1 Round 2" class="w-full text-xs p-2 rounded-lg border border-slate-300">
            </div>
          </div>

          <button @click="saveOutcome" class="px-4 py-2 bg-emerald-600 text-white text-xs font-semibold rounded-lg shadow-xs hover:bg-emerald-700">
            Record Outcome
          </button>
        </div>

      </div>

    </div>

    <!-- Rating Modal (Wireframe: Rate Session) -->
    <div v-if="showRatingModal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="font-bold text-slate-900 text-base">Rate Session with {{ store.workspace.mentorName }}</h3>
          <button @click="showRatingModal = false" class="text-slate-400 hover:text-slate-600 font-bold">✕</button>
        </div>

        <div class="mt-4 space-y-4">
          <!-- Star Rating -->
          <div class="text-center">
            <label class="block text-xs font-semibold text-slate-600 mb-2">Overall session usefulness</label>
            <div class="flex items-center justify-center space-x-2 text-2xl text-amber-400 cursor-pointer">
              <span v-for="star in 5" :key="star" @click="ratingStars = star">
                {{ star <= ratingStars ? '★' : '☆' }}
              </span>
            </div>
          </div>

          <!-- Helpful Tags from Wireframe -->
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1.5">What was most helpful?</label>
            <div class="grid grid-cols-2 gap-2 text-xs">
              <label class="flex items-center space-x-2 p-2 rounded border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input type="checkbox" class="rounded text-blue-600">
                <span>Clear next steps</span>
              </label>
              <label class="flex items-center space-x-2 p-2 rounded border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input type="checkbox" class="rounded text-blue-600">
                <span>Resume tips</span>
              </label>
              <label class="flex items-center space-x-2 p-2 rounded border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input type="checkbox" class="rounded text-blue-600">
                <span>Mock interview</span>
              </label>
              <label class="flex items-center space-x-2 p-2 rounded border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input type="checkbox" class="rounded text-blue-600">
                <span>Portfolio audit</span>
              </label>
            </div>
          </div>

          <!-- Comment -->
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Optional comment for mentor</label>
            <textarea rows="3" placeholder="Arjun was very practical and gave direct feedback on my SQL schema..." class="w-full text-xs p-2 rounded-lg border border-slate-300"></textarea>
          </div>

          <div class="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
            <button @click="showRatingModal = false" class="px-4 py-2 text-xs font-semibold text-slate-600">Cancel</button>
            <button @click="submitRating" class="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg shadow-xs hover:bg-blue-700">
              Submit Feedback
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
const activeTab = ref('goals');
const showAddGoal = ref(false);
const newGoalTitle = ref('');
const newGoalDate = ref('');

const showRatingModal = ref(false);
const ratingStars = ref(5);

const outcomeType = ref('interview');
const outcomeCompany = ref('');

function handleAddGoal() {
  if (newGoalTitle.value.trim()) {
    store.addGoal(newGoalTitle.value.trim(), newGoalDate.value);
    newGoalTitle.value = '';
    showAddGoal.value = false;
  }
}

function submitRating() {
  store.submitSessionRating({
    rating: ratingStars.value,
    helpfulTags: [],
    comment: ''
  });
  showRatingModal.value = false;
  alert('Thank you! Your feedback has been sent to your mentor.');
}

function saveOutcome() {
  if (outcomeCompany.value.trim()) {
    store.addAuditLog('student (Hemant)', `Recorded career outcome: ${outcomeType.value} - ${outcomeCompany.value}`);
    alert('Outcome recorded successfully!');
    outcomeCompany.value = '';
  }
}
</script>
