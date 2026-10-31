<template>
  <div class="min-h-[calc(100vh-4rem)] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-blue-50/50 to-slate-50">
    <div class="max-w-4xl mx-auto text-center">
      
      <!-- Pill -->
      <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-xs font-semibold mb-6">
        <span>🎓 IITM BS Degree Program · Problem Statement 2</span>
      </div>

      <h1 class="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight mb-4">
        Welcome to <span class="text-blue-600">Sangam</span>
      </h1>
      
      <p class="text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto mb-10">
        Connecting IITM BS students with verified alumni mentors for career pathways, project audits, interview prep, and structured guidance.
      </p>

      <!-- 3 Role Portals from Wireframe -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 text-left max-w-4xl mx-auto mb-12">
        
        <!-- Student Card -->
        <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-xs hover:border-blue-400 hover:shadow-md transition-all flex flex-col justify-between">
          <div>
            <div class="w-12 h-12 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-2xl font-bold mb-4">
              👨‍🎓
            </div>
            <h3 class="text-lg font-bold text-slate-900 mb-1">Student Portal</h3>
            <p class="text-sm text-slate-500 mb-4">
              Submit your career needs, discover verified mentors by domain, and track structured goals.
            </p>
          </div>
          <button 
            @click="enterRole('student', '/student/dashboard')"
            class="w-full py-2.5 px-4 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 transition-colors shadow-xs text-center"
          >
            Enter as Student →
          </button>
        </div>

        <!-- Mentor Card -->
        <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-xs hover:border-emerald-400 hover:shadow-md transition-all flex flex-col justify-between">
          <div>
            <div class="w-12 h-12 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center text-2xl font-bold mb-4">
              💼
            </div>
            <h3 class="text-lg font-bold text-slate-900 mb-1">Mentor (Alumni)</h3>
            <p class="text-sm text-slate-500 mb-4">
              Set your capacity (1–3 mentees), review specific requests, log session hours, and share notes.
            </p>
          </div>
          <button 
            @click="enterRole('mentor', '/mentor/dashboard')"
            class="w-full py-2.5 px-4 rounded-lg bg-emerald-600 text-white font-semibold text-sm hover:bg-emerald-700 transition-colors shadow-xs text-center"
          >
            Enter as Mentor →
          </button>
        </div>

        <!-- Admin Card -->
        <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-xs hover:border-purple-400 hover:shadow-md transition-all flex flex-col justify-between">
          <div>
            <div class="w-12 h-12 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center text-2xl font-bold mb-4">
              🏛️
            </div>
            <h3 class="text-lg font-bold text-slate-900 mb-1">IIC Placement Admin</h3>
            <p class="text-sm text-slate-500 mb-4">
              Verify alumni roll numbers, review system-recommended pairings, and monitor program analytics.
            </p>
          </div>
          <button 
            @click="enterRole('admin', '/admin/insights')"
            class="w-full py-2.5 px-4 rounded-lg bg-purple-600 text-white font-semibold text-sm hover:bg-purple-700 transition-colors shadow-xs text-center"
          >
            Enter as Admin →
          </button>
        </div>

      </div>

      <!-- Footer Specs note -->
      <div class="flex items-center justify-center space-x-6 text-xs text-slate-400 border-t border-slate-200 pt-6">
        <span>🔒 Zero Chat Logging for Privacy</span>
        <span>•</span>
        <span>⏱️ Max 3 Open Requests (7-Day Expiry)</span>
        <span>•</span>
        <span>✅ Verified Alumni Only</span>
      </div>

    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../../stores/auth';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();

function enterRole(role, targetPath) {
  auth.switchRole(role);
  router.push(targetPath);
}
</script>
