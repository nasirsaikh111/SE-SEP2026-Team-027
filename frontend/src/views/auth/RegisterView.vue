<template>
  <div class="min-h-[calc(100vh-4rem)] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
    <div class="max-w-md w-full bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
      
      <div class="text-center">
        <h2 class="text-2xl font-bold text-slate-900">Create an Account</h2>
        <p class="text-xs text-slate-500 mt-1">Join the IITM BS Mentoring Platform</p>
      </div>

      <form @submit.prevent="handleRegister" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Full name</label>
          <input v-model="form.name" required placeholder="e.g. Hemant Dhayal" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Email address</label>
          <input v-model="form.email" type="email" required placeholder="rollno@study.iitm.ac.in" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Password</label>
          <input v-model="form.password" type="password" required placeholder="••••••••" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
        </div>

        <!-- Role Radio Selector from Wireframe -->
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1.5">I am a :</label>
          <div class="flex items-center space-x-6 text-xs">
            <label class="flex items-center space-x-2 cursor-pointer">
              <input type="radio" v-model="form.role" value="student" class="text-blue-600">
              <span class="font-medium">Student</span>
            </label>
            <label class="flex items-center space-x-2 cursor-pointer">
              <input type="radio" v-model="form.role" value="mentor" class="text-blue-600">
              <span class="font-medium">Mentor (Alumni)</span>
            </label>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Roll No / Graduation Year</label>
          <input v-model="form.rollNo" required placeholder="e.g. 21f1001234 / 2024" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
        </div>

        <!-- Wireframe Red Hint -->
        <div v-if="form.role === 'mentor'" class="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
          ⚠️ <strong>Notice:</strong> Mentors remain hidden from search until verified against the graduate registry by the IIC Administrator (Story 2.1).
        </div>

        <button 
          type="submit" 
          class="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
        >
          Complete Registration →
        </button>
      </form>

      <div class="text-center text-xs text-slate-500 border-t border-slate-100 pt-4">
        Already registered? 
        <router-link to="/login" class="text-blue-600 font-semibold hover:underline">
          Sign in
        </router-link>
      </div>

    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue';
import { useAuthStore } from '../../stores/auth';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();

const form = reactive({
  name: '',
  email: '',
  password: '',
  role: 'student',
  rollNo: ''
});

function handleRegister() {
  auth.login(form.email, form.role);
  if (form.role === 'mentor') {
    alert('Mentor registered! Your profile is pending verification by the IIC Administrator.');
    router.push('/mentor/profile');
  } else {
    router.push('/student/dashboard');
  }
}
</script>
