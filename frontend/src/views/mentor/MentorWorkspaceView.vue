<template>
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
    
    <!-- Top Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Mentee Workspace & Sessions</h1>
        <p class="text-sm text-slate-500">Track goal progress, keep shared notes, and log completed session hours.</p>
      </div>

      <button 
        @click="showLogSessionModal = true"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5"
      >
        <span>📅 Log Mentoring Session</span>
      </button>
    </div>

    <!-- Active Mentees Roster from Wireframe -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
      <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">My Mentees Roster</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Mentee 1 (Active) -->
        <div class="p-4 rounded-xl border border-blue-200 bg-blue-50/40 flex items-center justify-between">
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-bold text-slate-900 text-sm">Hemant Dhayal</span>
              <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-[10px] font-bold">Active</span>
            </div>
            <div class="text-xs text-slate-500 mt-1">Goals: 2/4 completed · Next: Thu 6:30 PM</div>
          </div>
          <span class="px-3 py-1 bg-white border border-slate-200 text-xs font-semibold rounded-lg text-blue-600">
            Selected
          </span>
        </div>

        <!-- Mentee 2 (Idle > 21 days - Nudge feature from Wireframe) -->
        <div class="p-4 rounded-xl border border-amber-200 bg-amber-50/30 flex items-center justify-between">
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-bold text-slate-900 text-sm">Karthik P.</span>
              <span class="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-bold">Needs Check-in</span>
            </div>
            <div class="text-xs text-slate-500 mt-1">Goals: 1/3 completed · No session in 21 days</div>
          </div>
          <button 
            @click="nudgeMentee('Karthik P.')"
            class="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-lg shadow-xs"
          >
            Nudge Mentee
          </button>
        </div>
      </div>
    </div>

    <!-- Main Workspace Pane (For selected mentee: Hemant Dhayal) -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      
      <div class="flex border-b border-slate-200 bg-slate-50/50">
        <button 
          v-for="tab in ['goals', 'sessions', 'notes']" 
          :key="tab"
          @click="activeTab = tab"
          class="px-6 py-3.5 text-xs font-bold uppercase tracking-wider transition-colors border-b-2"
          :class="activeTab === tab ? 'border-blue-600 text-blue-700 bg-white' : 'border-transparent text-slate-500 hover:text-slate-800'"
        >
          {{ tab === 'goals' ? 'Mentoring Goals' : tab === 'sessions' ? 'Logged Sessions' : 'Private & Shared Notes' }}
        </button>
      </div>

      <div class="p-6">
        
        <!-- Tab 1: Goals -->
        <div v-if="activeTab === 'goals'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-slate-900">Student Career Milestones</h3>
            <span class="text-xs text-slate-500">2 of 4 milestones marked complete</span>
          </div>

          <div class="space-y-3">
            <div 
              v-for="goal in store.workspace.goals" 
              :key="goal.id"
              class="p-4 rounded-xl border border-slate-200 flex items-center justify-between"
              :class="goal.completed ? 'bg-slate-50 text-slate-400' : 'bg-white text-slate-800'"
            >
              <div class="flex items-center space-x-3">
                <input 
                  type="checkbox" 
                  :checked="goal.completed" 
                  @change="store.toggleGoal(goal.id)"
                  class="w-4 h-4 rounded text-blue-600 cursor-pointer"
                >
                <span class="text-xs font-medium" :class="{'line-through': goal.completed}">
                  {{ goal.title }}
                </span>
              </div>
              <span class="text-[11px] text-slate-400">Target: {{ goal.targetDate }}</span>
            </div>
          </div>
        </div>

        <!-- Tab 2: Sessions -->
        <div v-else-if="activeTab === 'sessions'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-slate-900">Past Verified Sessions</h3>
            <span class="text-xs text-slate-500">Total hours logged: 1 hr 45 mins</span>
          </div>

          <div class="space-y-3">
            <div 
              v-for="sess in store.workspace.sessions" 
              :key="sess.id"
              class="p-4 rounded-xl border border-slate-200 flex items-center justify-between"
            >
              <div>
                <div class="text-xs font-bold text-slate-900">{{ sess.date }} · {{ sess.duration }}</div>
                <div class="text-[11px] text-slate-500">{{ sess.notes }}</div>
              </div>
              <span class="px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                {{ sess.status }}
              </span>
            </div>
          </div>
        </div>

        <!-- Tab 3: Notes (Dual View: Shared vs Private) -->
        <div v-else-if="activeTab === 'notes'" class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Shared Notes -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-xs font-bold text-slate-900">Shared Notes (Mentee sees)</label>
              <span class="text-[10px] text-slate-400">Visible to Hemant</span>
            </div>
            <textarea 
              v-model="store.workspace.sharedNotes" 
              rows="6"
              class="w-full text-xs p-3 rounded-xl border border-slate-300 shadow-xs focus:ring-blue-500 focus:border-blue-500"
            ></textarea>
          </div>

          <!-- Private Notes -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-xs font-bold text-slate-900">Private Notes (Only you)</label>
              <span class="text-[10px] text-amber-600 font-semibold">🔒 Private to Mentor</span>
            </div>
            <textarea 
              v-model="store.workspace.privateNotes" 
              rows="6"
              class="w-full text-xs p-3 rounded-xl border border-amber-200 bg-amber-50/20 shadow-xs focus:ring-amber-500 focus:border-amber-500"
            ></textarea>
          </div>
        </div>

      </div>
    </div>

    <!-- Log Session Modal (Wireframe Artboard: Log Session) -->
    <div v-if="showLogSessionModal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="font-bold text-slate-900 text-base">Log Mentoring Session</h3>
          <button @click="showLogSessionModal = false" class="text-slate-400 hover:text-slate-600 font-bold">✕</button>
        </div>

        <form @submit.prevent="submitSessionLog" class="mt-4 space-y-4">
          <div class="p-3 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-800">
            🔒 <strong>Strict Privacy Notice:</strong> Per program policy, no field is provided for conversation contents. Only session occurrence and duration are logged.
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Session Date</label>
            <input type="date" v-model="sessionForm.date" class="w-full text-xs p-2 rounded-lg border border-slate-300" required>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Duration</label>
            <select v-model="sessionForm.duration" class="w-full text-xs p-2 rounded-lg border border-slate-300">
              <option value="30 mins">30 mins</option>
              <option value="45 mins">45 mins</option>
              <option value="60 mins">60 mins</option>
              <option value="90 mins">90 mins</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Status</label>
            <div class="flex space-x-4 text-xs">
              <label class="flex items-center space-x-1.5 cursor-pointer">
                <input type="radio" v-model="sessionForm.status" value="DONE" class="text-blue-600">
                <span>Done</span>
              </label>
              <label class="flex items-center space-x-1.5 cursor-pointer">
                <input type="radio" v-model="sessionForm.status" value="NO_SHOW" class="text-blue-600">
                <span>No-show</span>
              </label>
              <label class="flex items-center space-x-1.5 cursor-pointer">
                <input type="radio" v-model="sessionForm.status" value="CANCELLED" class="text-blue-600">
                <span>Cancelled</span>
              </label>
            </div>
          </div>

          <div class="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
            <button type="button" @click="showLogSessionModal = false" class="px-4 py-2 text-xs font-semibold text-slate-600">Cancel</button>
            <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs">
              Log Session
            </button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useMentorshipStore } from '../../stores/mentorship';

const store = useMentorshipStore();
const activeTab = ref('goals');
const showLogSessionModal = ref(false);

const sessionForm = reactive({
  date: new Date().toISOString().split('T')[0],
  duration: '45 mins',
  status: 'DONE'
});

function nudgeMentee(name) {
  store.addAuditLog('mentor (Arjun K.)', `Sent inactivity nudge to ${name}`);
  alert(`Inactivity reminder email sent to ${name} (Story 5.3).`);
}

function submitSessionLog() {
  store.logSession({
    date: sessionForm.date,
    duration: sessionForm.duration,
    status: sessionForm.status
  });
  showLogSessionModal.value = false;
  alert('Session logged successfully!');
}
</script>
