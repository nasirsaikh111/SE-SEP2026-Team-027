<template>
  <!-- Floating helpdesk; answers come only from IIC-published articles and are never stored -->
  <div class="fixed bottom-5 right-5 z-50">
    <button v-if="!open" @click="open = true"
            class="px-4 py-2.5 rounded-full bg-blue-600 text-white text-sm font-semibold shadow-lg hover:bg-blue-700">
      Ask Sangam
    </button>
    <div v-else class="w-[360px] bg-white rounded-xl border border-slate-200 shadow-xl flex flex-col max-h-[520px]">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <div>
          <div class="text-sm font-bold">Ask Sangam</div>
          <div class="text-[10px] text-slate-500">Questions about Sangam only · messages are not stored</div>
        </div>
        <button @click="open = false" class="text-slate-400 hover:text-slate-700 text-sm">Close</button>
      </div>
      <div v-if="!auth.isLive" class="p-4 text-xs text-slate-600 space-y-3">
        <p>Ask Sangam answers questions about using Sangam for students, mentors and IIC admins. Sign in to start.</p>
        <router-link to="/login" @click="open = false" class="inline-block px-3 py-1.5 rounded bg-blue-600 text-white">Sign in</router-link>
      </div>
      <div v-else ref="box" class="flex-1 overflow-y-auto p-3 space-y-3 text-xs">
        <div v-if="!messages.length" class="text-slate-500">I can help with using Sangam: requests, matching, meetings, goals, feedback and privacy. Try "How do I log a meeting?"</div>
        <div v-for="(m, i) in messages" :key="i" :class="m.me ? 'text-right' : ''">
          <div class="inline-block max-w-[85%] px-3 py-2 rounded-lg whitespace-pre-line text-left"
               :class="m.me ? 'bg-blue-600 text-white' : m.scope === 'out_of_scope' ? 'bg-amber-50 text-amber-900 border border-amber-200' : 'bg-slate-100 text-slate-800'">{{ m.text }}</div>
          <div v-if="m.sources?.length" class="text-[10px] text-slate-400 mt-1">Sources: {{ m.sources.map((s) => s.title).join(', ') }}
            · {{ m.llm ? 'Gemini' : 'article text' }}</div>
        </div>
        <div v-if="busy" class="text-slate-400">Thinking…</div>
      </div>
      <form v-if="auth.isLive" @submit.prevent="send" class="flex gap-2 p-3 border-t border-slate-100">
        <input v-model="q" maxlength="1000" placeholder="Ask about requests, meetings, goals…" class="flex-1 text-xs p-2 rounded border border-slate-300" />
        <button :disabled="busy || q.trim().length < 2" class="px-3 text-xs rounded bg-blue-600 text-white disabled:opacity-50">Send</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import { Sangam } from '../../api/client';
import { useAuthStore } from '../../stores/auth';

const auth = useAuthStore();

const open = ref(false);
const q = ref('');
const busy = ref(false);
const messages = ref([]);
const box = ref(null);

async function send() {
  const text = q.value.trim();
  messages.value.push({ me: true, text });
  q.value = '';
  busy.value = true;
  try {
    const r = await Sangam.chat(text);
    messages.value.push({ text: r.answer, sources: r.sources, llm: r.llm_used, scope: r.scope });
  } catch (e) {
    messages.value.push({ text: e.status === 429 ? 'Too many questions in a minute. Please wait a moment.' : 'Sorry, the helpdesk is unavailable right now.' });
  } finally {
    busy.value = false;
    await nextTick();
    if (box.value) box.value.scrollTop = box.value.scrollHeight;
  }
}
</script>
