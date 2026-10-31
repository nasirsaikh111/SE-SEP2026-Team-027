<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    
    <div class="border-b border-slate-200 pb-5">
      <div class="flex items-center space-x-2">
        <h1 class="text-2xl font-bold text-slate-900">Mentor Profile & Availability</h1>
        <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
          Verified Alumni
        </span>
      </div>
      <p class="text-sm text-slate-500 mt-1">Configure your industry background, volunteer capacity, and weekly office hours.</p>
    </div>

    <!-- Verification Notice Banner (Wireframe) -->
    <div class="p-4 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-800 flex items-start space-x-3">
      <span class="text-lg">🛡️</span>
      <div>
        <span class="font-bold">IITM Graduate Verification Active:</span> Your profile is verified against IITM roll number <code>21f1001234</code> (Class of 2024). Verified mentors are displayed with a verified badge in student search.
      </div>
    </div>

    <form @submit.prevent="saveProfile" class="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-6">
      
      <!-- Headline & Role -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-bold text-slate-700 mb-1">Current Job Title / Role</label>
          <input v-model="profile.role" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
        </div>
        <div>
          <label class="block text-xs font-bold text-slate-700 mb-1">Company / Organization</label>
          <input v-model="profile.company" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
        </div>
      </div>

      <div>
        <label class="block text-xs font-bold text-slate-700 mb-1">Profile Headline</label>
        <input v-model="profile.headline" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
      </div>

      <!-- Domain & Pathway -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-bold text-slate-700 mb-1">Primary Domain</label>
          <select v-model="profile.domain" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
            <option value="Data & ML">Data Science & Machine Learning</option>
            <option value="Analytics">Data Analytics & BI</option>
            <option value="Software">Software Engineering (Backend/Fullstack)</option>
            <option value="Product">Product Management</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-bold text-slate-700 mb-1">Career Pathway</label>
          <select v-model="profile.pathway" class="w-full text-xs p-2.5 rounded-lg border border-slate-300">
            <option value="Industry">Industry Placement</option>
            <option value="Higher Studies">Higher Studies (MS/PhD)</option>
            <option value="Venture">Venture / Entrepreneurship</option>
          </select>
        </div>
      </div>

      <!-- Capacity Control (Wireframe: Capacity: 3 mentees / term) -->
      <div class="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
        <div class="flex items-center justify-between">
          <label class="text-xs font-bold text-slate-900">Volunteer Mentee Capacity (Max concurrent mentees)</label>
          <span class="text-xs font-extrabold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
            {{ profile.capacity }} mentees per term
          </span>
        </div>
        <p class="text-[11px] text-slate-500">
          Default is 1 mentee (2–3 hours/month). You can increase up to 3 mentees if your schedule permits. When full, you will be shown as "Full" to students.
        </p>
        <input type="range" min="1" max="3" v-model.number="profile.capacity" class="w-full accent-blue-600 cursor-pointer">
      </div>

      <!-- Office Hours Slots -->
      <div>
        <label class="block text-xs font-bold text-slate-700 mb-2">Weekly Office Hours Availability Slots</label>
        <div class="flex flex-wrap gap-2 mb-3">
          <span 
            v-for="(slot, i) in profile.officeHours" 
            :key="i"
            class="px-3 py-1.5 rounded-lg bg-blue-50 text-blue-800 text-xs font-semibold border border-blue-200 flex items-center space-x-2"
          >
            <span>{{ slot }}</span>
            <button type="button" @click="removeSlot(i)" class="text-blue-500 hover:text-blue-800 font-bold">×</button>
          </span>
        </div>

        <div class="flex gap-2 max-w-sm">
          <input v-model="newSlot" placeholder="e.g. Sat 4:00 PM" class="text-xs p-2 rounded-lg border border-slate-300 flex-1">
          <button type="button" @click="addSlot" class="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg">
            + Add Slot
          </button>
        </div>
      </div>

      <div class="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
        <button type="submit" class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs">
          Update Profile & Availability
        </button>
      </div>

    </form>

  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';

const profile = reactive({
  role: 'Senior Data Scientist',
  company: 'Fractal Analytics',
  headline: 'Foundation → Analyst → Data Scientist at Fractal',
  domain: 'Data & ML',
  pathway: 'Industry',
  capacity: 3,
  officeHours: ['Tue 6:30 PM', 'Thu 6:30 PM']
});

const newSlot = ref('');

function addSlot() {
  if (newSlot.value.trim()) {
    profile.officeHours.push(newSlot.value.trim());
    newSlot.value = '';
  }
}

function removeSlot(index) {
  profile.officeHours.splice(index, 1);
}

function saveProfile() {
  alert('Profile updated successfully!');
}
</script>
