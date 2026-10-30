<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased selection:bg-blue-100 selection:text-blue-900">
    <!-- Main Top Navigation with Role Switcher -->
    <AppNavbar />

    <!-- Primary Router Outlet -->
    <main class="flex-1">
      <router-view />
    </main>

    <!-- Global Footer -->
    <footer class="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
      <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
        <div>
          <strong>Sangam Mentoring Platform</strong> · IITM BS Degree Program (Problem Statement 2)
        </div>
        <div>
          Team 027 · Software Engineering Course (Sep 2026 Term)
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import AppNavbar from './components/common/AppNavbar.vue';
</script>
