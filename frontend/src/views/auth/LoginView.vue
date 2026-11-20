<template>
  <div class="min-h-[calc(100vh-4rem)] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
    <div class="max-w-md w-full bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
      
      <div class="text-center">
        <div class="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-xl mx-auto mb-3 shadow-sm">
          S
        </div>
        <h2 class="text-2xl font-bold text-slate-900">Sign in to Sangam</h2>
        <p class="text-xs text-slate-500 mt-1">Student Mentoring & Career Support Platform · IITM BS</p>
      </div>

      <!-- Quick Fill Test Accounts (From Production Seed) -->
      <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-100 text-xs">
        <div class="text-[11px] font-bold text-blue-900 mb-1.5 flex items-center justify-between">
          <span>⚡ Quick Fill Demo Accounts:</span>
          <span class="text-[10px] font-mono text-blue-700 bg-blue-100/70 px-1.5 py-0.5 rounded">Pass: SangamDemo!2026</span>
        </div>
        <div class="grid grid-cols-3 gap-1.5 text-center">
          <button 
            type="button" 
            @click="fillAccount('hemant@ds.study.iitm.ac.in', 'student')"
            class="py-1 px-1.5 rounded-md text-[11px] font-medium border transition-all cursor-pointer"
            :class="selectedRole === 'student' ? 'bg-white text-blue-700 border-blue-300 font-bold shadow-2xs' : 'bg-white/60 text-slate-700 border-slate-200 hover:bg-white'"
          >
            👨‍🎓 Student
          </button>
          <button 
            type="button" 
            @click="fillAccount('arjun.k@alumni.example.org', 'mentor')"
            class="py-1 px-1.5 rounded-md text-[11px] font-medium border transition-all cursor-pointer"
            :class="selectedRole === 'mentor' ? 'bg-white text-blue-700 border-blue-300 font-bold shadow-2xs' : 'bg-white/60 text-slate-700 border-slate-200 hover:bg-white'"
          >
            🧑‍💼 Mentor
          </button>
          <button 
            type="button" 
            @click="fillAccount('iic.admin@iitm.ac.in', 'admin')"
            class="py-1 px-1.5 rounded-md text-[11px] font-medium border transition-all cursor-pointer"
            :class="selectedRole === 'admin' ? 'bg-white text-blue-700 border-blue-300 font-bold shadow-2xs' : 'bg-white/60 text-slate-700 border-slate-200 hover:bg-white'"
          >
            🏛️ IIC Admin
          </button>
        </div>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Email address</label>
          <input 
            v-model="email" 
            type="email" 
            required 
            placeholder="hemant@ds.study.iitm.ac.in" 
            class="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:ring-blue-500 focus:border-blue-500"
          >
        </div>

        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-xs font-semibold text-slate-700">Password</label>
            <span class="text-[11px] text-slate-400">Demo: SangamDemo!2026</span>
          </div>
          <input 
            v-model="password" 
            type="password" 
            required 
            placeholder="SangamDemo!2026" 
            class="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:ring-blue-500 focus:border-blue-500"
          >
        </div>

        <!-- Role Selector for Login Flow (From Wireframe: Which role? from JWT) -->
        <div class="p-3 bg-slate-50 rounded-lg border border-slate-200">
          <label class="block text-xs font-bold text-slate-700 mb-1.5">Sign in as (Simulated JWT Claim):</label>
          <div class="grid grid-cols-3 gap-2 text-xs">
            <button 
              type="button" 
              @click="selectedRole = 'student'"
              class="py-1.5 px-2 rounded-md font-medium border text-center transition-all cursor-pointer"
              :class="selectedRole === 'student' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-200'"
            >
              Student
            </button>
            <button 
              type="button" 
              @click="selectedRole = 'mentor'"
              class="py-1.5 px-2 rounded-md font-medium border text-center transition-all cursor-pointer"
              :class="selectedRole === 'mentor' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-200'"
            >
              Mentor
            </button>
            <button 
              type="button" 
              @click="selectedRole = 'admin'"
              class="py-1.5 px-2 rounded-md font-medium border text-center transition-all cursor-pointer"
              :class="selectedRole === 'admin' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-200'"
            >
              Admin
            </button>
          </div>
        </div>

        <button 
          type="submit" 
          class="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
        >
          Sign In →
        </button>
      </form>

      <div class="text-center text-xs text-slate-500 border-t border-slate-100 pt-4">
        IITM BS Student Mentoring System · 
        <span class="text-blue-600 font-semibold">Production Ready</span>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '../../stores/auth';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();

const email = ref('hemant@ds.study.iitm.ac.in');
const password = ref('SangamDemo!2026');
const selectedRole = ref('student');

function fillAccount(accEmail, role) {
  email.value = accEmail;
  password.value = 'SangamDemo!2026';
  selectedRole.value = role;
}

function handleLogin() {
  auth.login(email.value, selectedRole.value);
  if (selectedRole.value === 'student') {
    router.push('/student/dashboard');
  } else if (selectedRole.value === 'mentor') {
    router.push('/mentor/dashboard');
  } else {
    router.push('/admin/insights');
  }
}
</script>
