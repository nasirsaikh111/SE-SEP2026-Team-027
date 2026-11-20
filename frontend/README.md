# Sangam frontend

React 19 + Vite + TypeScript + Tailwind CSS 4 + DaisyUI 5. All data comes from the Django REST API (`/api/v1/`).
There are no mock stores, and no direct database or Supabase access.

```bash
npm install
cp .env.example .env      # VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
npm run dev               # http://localhost:5173
npm run build             # type-check + production build into dist/
```

## Structure
| Path | Purpose |
|---|---|
| `src/lib/api.ts` | The single Axios client: JWT header, single-flight token refresh, error helpers |
| `src/lib/queries.ts` | TanStack Query hooks for every endpoint; mutations invalidate affected queries |
| `src/lib/types.ts` | Types mirroring the DRF serializers |
| `src/auth/AuthContext.tsx` | Session and role from `GET /auth/me/` (`effective_role`); route guards (UX only) |
| `src/layout/` | App shell: top bar, role sidebar (`nav.ts`), mobile drawer, theme toggle |
| `src/components/` | DaisyUI primitives, workspace panels, charts |
| `src/pages/` | Screens per role (`student/`, `mentor/`, `admin/`) plus shared pages |

The role-to-screen and screen-to-endpoint mapping is in [`docs/03-integration-contract.md`](../docs/03-integration-contract.md).
Deploying to Vercel: root `frontend`, output `dist`, set `VITE_API_BASE_URL`; `vercel.json` handles SPA routing.
