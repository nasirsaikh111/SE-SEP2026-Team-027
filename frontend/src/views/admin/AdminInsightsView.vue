<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
    
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
      <div>
        <div class="flex items-center space-x-2">
          <h1 class="text-2xl font-bold text-slate-900">IIC Program Insights & Oversight</h1>
          <span class="px-2 py-0.5 rounded bg-purple-100 text-purple-800 text-xs font-bold">
            Story 5.4
          </span>
        </div>
        <p class="text-sm text-slate-500 mt-0.5">Aggregate outcomes, engagement funnels, and domain demand without exposing private conversations.</p>
      </div>

      <button 
        @click="exportCSV"
        class="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5"
      >
        <span>📥 Export Program CSV</span>
      </button>
    </div>

    <!-- Top Key Metrics Cards (From Wireframe) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Mentorship Needs</div>
        <div class="text-3xl font-extrabold text-blue-600 mt-2">{{ store.requests.length }}</div>
        <div class="text-xs text-slate-400 mt-1">Total student requests this term</div>
      </div>
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider">Verified Alumni Mentors</div>
        <div class="text-3xl font-extrabold text-emerald-600 mt-2">{{ store.verifiedMentors.length }}</div>
        <div class="text-xs text-slate-400 mt-1">{{ store.pendingVerificationMentors.length }} awaiting roll verification</div>
      </div>
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider">Average Program Rating</div>
        <div class="text-3xl font-extrabold text-amber-500 mt-2">4.8 <span class="text-sm font-normal text-slate-400">/ 5.0</span></div>
        <div class="text-xs text-slate-400 mt-1">Based on student session feedback</div>
      </div>
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider">Goal Completion Rate</div>
        <div class="text-3xl font-extrabold text-purple-600 mt-2">78%</div>
        <div class="text-xs text-slate-400 mt-1">Agreed milestones marked done</div>
      </div>
    </div>

    <!-- Funnel & Demand Visualizations (Wireframe Artboard: Admin Insights) -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      
      <!-- Mentoring Funnel -->
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 class="text-sm font-bold text-slate-900">Program Funnel: Sent → Done</h2>
          <span class="text-xs text-slate-400">Current Term</span>
        </div>

        <div class="space-y-4 pt-2">
          <div>
            <div class="flex justify-between text-xs font-semibold mb-1">
              <span>1. Requests Sent</span>
              <span>142 requests (100%)</span>
            </div>
            <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
              <div class="bg-blue-600 h-full rounded-full" style="width: 100%"></div>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-xs font-semibold mb-1">
              <span>2. Accepted by Mentors</span>
              <span>118 accepted (83%)</span>
            </div>
            <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
              <div class="bg-emerald-500 h-full rounded-full" style="width: 83%"></div>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-xs font-semibold mb-1">
              <span>3. Sessions Logged</span>
              <span>102 pairs held ≥1 session (72%)</span>
            </div>
            <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
              <div class="bg-amber-500 h-full rounded-full" style="width: 72%"></div>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-xs font-semibold mb-1">
              <span>4. Closed with Positive Outcome</span>
              <span>89 students (62%)</span>
            </div>
            <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
              <div class="bg-purple-600 h-full rounded-full" style="width: 62%"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Domain Demand Breakdown -->
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 class="text-sm font-bold text-slate-900">Student Demand by Domain</h2>
          <span class="text-xs text-slate-400">IITM BS Tracks</span>
        </div>

        <div class="space-y-3 pt-2">
          <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100">
            <div>
              <div class="text-xs font-bold text-slate-900">Data Science & Machine Learning</div>
              <div class="text-[11px] text-slate-500">62 requests · 5 verified mentors available</div>
            </div>
            <span class="px-2.5 py-1 rounded bg-blue-100 text-blue-800 text-xs font-bold">44%</span>
          </div>

          <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100">
            <div>
              <div class="text-xs font-bold text-slate-900">Software Engineering (SDE)</div>
              <div class="text-[11px] text-slate-500">46 requests · 4 verified mentors available</div>
            </div>
            <span class="px-2.5 py-1 rounded bg-blue-100 text-blue-800 text-xs font-bold">32%</span>
          </div>

          <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100">
            <div>
              <div class="text-xs font-bold text-slate-900">Business Analytics & BI</div>
              <div class="text-[11px] text-slate-500">22 requests · 3 verified mentors available</div>
            </div>
            <span class="px-2.5 py-1 rounded bg-blue-100 text-blue-800 text-xs font-bold">16%</span>
          </div>

          <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100">
            <div>
              <div class="text-xs font-bold text-slate-900">Higher Studies (MS/PhD in Europe/US)</div>
              <div class="text-[11px] text-slate-500">12 requests · 2 verified mentors available</div>
            </div>
            <span class="px-2.5 py-1 rounded bg-blue-100 text-blue-800 text-xs font-bold">8%</span>
          </div>
        </div>
      </div>

    </div>

    <!-- Quick Navigation Callout -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
      <router-link to="/admin/verify" class="p-5 rounded-xl border border-slate-200 bg-white hover:border-blue-400 hover:shadow-xs transition-all flex items-center justify-between">
        <div>
          <div class="text-sm font-bold text-slate-900">Alumni Verification Queue</div>
          <div class="text-xs text-slate-500 mt-0.5">{{ store.pendingVerificationMentors.length }} mentors pending check</div>
        </div>
        <span class="text-slate-400">→</span>
      </router-link>

      <router-link to="/admin/flags" class="p-5 rounded-xl border border-slate-200 bg-white hover:border-amber-400 hover:shadow-xs transition-all flex items-center justify-between">
        <div>
          <div class="text-sm font-bold text-slate-900">Safety & Flagged Reports</div>
          <div class="text-xs text-slate-500 mt-0.5">{{ store.flags.length }} reports requiring review</div>
        </div>
        <span class="text-slate-400">→</span>
      </router-link>

      <router-link to="/admin/audit" class="p-5 rounded-xl border border-slate-200 bg-white hover:border-purple-400 hover:shadow-xs transition-all flex items-center justify-between">
        <div>
          <div class="text-sm font-bold text-slate-900">System Audit Trail</div>
          <div class="text-xs text-slate-500 mt-0.5">{{ store.auditLogs.length }} logged state changes</div>
        </div>
        <span class="text-slate-400">→</span>
      </router-link>
    </div>

  </div>
</template>

<script setup>
import { useMentorshipStore } from '../../stores/mentorship';

const store = useMentorshipStore();

function exportCSV() {
  const csvContent = "data:text/csv;charset=utf-8," 
    + "Metric,Value\n"
    + `Total Requests,${store.requests.length}\n`
    + `Verified Mentors,${store.verifiedMentors.length}\n`
    + "Average Rating,4.8\n"
    + "Goal Completion Rate,78%\n";
  
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "sangam_program_metrics.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
</script>
