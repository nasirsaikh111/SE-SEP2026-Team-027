<template>
  <div class="min-h-[calc(100vh-4rem)] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
    <div class="max-w-md w-full bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
      
      <div class="text-center">
        <h2 class="text-2xl font-bold text-slate-900">Sign in to Sangam</h2>
        <p class="text-xs text-slate-500 mt-1">Student Mentoring & Career Support Platform</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Email address</label>
          <input 
            v-model="email" 
            type="email" 
            required 
            placeholder="rollno@study.iitm.ac.in" 
            class="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:ring-blue-500 focus:border-blue-500"
          >
        </div>

        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-xs font-semibold text-slate-700">Password</label>
            <a href="#" class="text-[11px] text-blue-600 hover:underline">Forgot password?</a>
          </div>
          <input 
            v-model="password" 
            type="password" 
            required 
            placeholder="••••••••" 
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
              class="py-1.5 px-2 rounded-md font-medium border text-center transition-all"
              :class="selectedRole === 'student' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-200'"
            >
              Student
            </button>
            <button 
              type="button" 
              @click="selectedRole = 'mentor'"
              class="py-1.5 px-2 rounded-md font-medium border text-center transition-all"
              :class="selectedRole === 'mentor' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-200'"
            >
              Mentor
            </button>
            <button 
              type="button" 
              @click="selectedRole = 'admin'"
              class="py-1.5 px-2 rounded-md font-medium border text-center transition-all"
              :class="selectedRole === 'admin' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-200'"
            >
              Admin
            </button>
          </div>
        </div>

        <button 
          type="submit" 
          class="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
        >
          Sign In →
        </button>
      </form>

      <div class="text-center text-xs text-slate-500 border-t border-slate-100 pt-4">
        Don't have an account? 
        <router-link to="/register" class="text-blue-600 font-semibold hover:underline">
          Register here
        </router-link>
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

const email = ref('hemant@study.iitm.ac.in');
const password = ref('password123');
const selectedRole = ref('student');

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
