<template>
  <header class="bg-white border-b border-slate-200 sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        
        <!-- Brand & Logo -->
        <div class="flex items-center space-x-6">
          <router-link to="/" class="flex items-center space-x-2">
            <div class="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
              S
            </div>
            <div>
              <span class="text-xl font-bold text-slate-900 tracking-tight">Sangam</span>
              <span class="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                IITM BS Mentoring
              </span>
            </div>
          </router-link>

          <!-- Navigation Links Based on Role -->
          <nav class="hidden md:flex space-x-1 pl-4 border-l border-slate-200">
            <!-- Student Links -->
            <template v-if="auth.isStudent">
              <router-link 
                to="/student/dashboard" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/student/dashboard' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Dashboard
              </router-link>
              <router-link 
                to="/student/discover" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/student/discover' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Discover Mentors
              </router-link>
              <router-link 
                to="/student/requests" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors relative"
                :class="$route.path === '/student/requests' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                My Requests
                <span v-if="store.myStudentRequests.length" class="ml-1.5 px-1.5 py-0.2 rounded-full text-xs bg-slate-200 text-slate-800">
                  {{ store.myStudentRequests.length }}
                </span>
              </router-link>
              <router-link 
                to="/student/workspace" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/student/workspace' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Mentorship Workspace
              </router-link>
            </template>

            <!-- Mentor Links -->
            <template v-else-if="auth.isMentor">
              <router-link 
                to="/mentor/dashboard" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/mentor/dashboard' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Mentor Dashboard
              </router-link>
              <router-link 
                to="/mentor/workspace" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/mentor/workspace' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                My Mentees & Workspace
              </router-link>
              <router-link 
                to="/mentor/profile" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/mentor/profile' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Profile & Capacity
              </router-link>
            </template>

            <!-- Admin Links -->
            <template v-else-if="auth.isAdmin">
              <router-link 
                to="/admin/insights" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/admin/insights' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Program Insights
              </router-link>
              <router-link 
                to="/admin/verify" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors relative"
                :class="$route.path === '/admin/verify' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Verification Queue
                <span v-if="store.pendingVerificationMentors.length" class="ml-1 px-1.5 py-0.2 rounded-full text-xs bg-amber-100 text-amber-800 font-bold">
                  {{ store.pendingVerificationMentors.length }}
                </span>
              </router-link>
              <router-link 
                to="/admin/flags" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/admin/flags' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Safety & Flags
              </router-link>
              <router-link 
                to="/admin/audit" 
                class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
                :class="$route.path === '/admin/audit' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'"
              >
                Audit Log
              </router-link>
            </template>
          </nav>
        </div>

        <!-- Role Switcher & User Profile Pill -->
        <div class="flex items-center space-x-3">
          
          <!-- Quick Role Switcher for Milestone Evaluation -->
          <div class="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
            <span class="text-xs font-semibold text-slate-500 uppercase px-2 hidden lg:inline">View as:</span>
            <button
              v-for="role in auth.availableRoles"
              :key="role.id"
              @click="handleRoleChange(role)"
              class="px-2.5 py-1 text-xs font-medium rounded-md transition-all"
              :class="auth.currentRole === role.id ? 'bg-white text-blue-700 shadow-xs font-semibold' : 'text-slate-600 hover:text-slate-900'"
            >
              {{ role.id === 'student' ? 'Student' : role.id === 'mentor' ? 'Mentor' : 'Admin' }}
            </button>
          </div>

          <!-- User Badge / Logout -->
          <div class="flex items-center space-x-2 pl-2 border-l border-slate-200">
            <div class="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-xs">
              {{ auth.currentUser.name.charAt(0) }}
            </div>
            <div class="hidden sm:block text-left leading-tight">
              <div class="text-xs font-bold text-slate-900">{{ auth.currentUser.name.split(' ')[0] }}</div>
              <div class="text-[10px] text-slate-500 capitalize">{{ auth.currentRole }}</div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useAuthStore } from '../../stores/auth';
import { useMentorshipStore } from '../../stores/mentorship';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const store = useMentorshipStore();
const router = useRouter();

function handleRoleChange(role) {
  auth.switchRole(role.id);
  router.push(role.defaultPath);
}
</script>
