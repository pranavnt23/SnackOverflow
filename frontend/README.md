# Snack Overflow - Frontend

Production-minded single-page application (SPA) for the Snack Overflow office pantry tracker.

## Tech Stack
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Routing**: React Router DOM (v6)
- **Styling**: Tailwind CSS (mobile-first, custom palette)
- **Icons**: Lucide React
- **State Management**: React Context (`AuthContext`, `ToastContext`), minimal dependencies (zero Redux, zero heavy UI kits)

---

## Getting Started

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration:
```env
VITE_API_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```
The frontend dev server starts at `http://localhost:5173`.

### 4. Build for Production
```bash
npm run build
```
Builds optimized static assets in `/frontend/dist`.

---

## Architecture Overview

### 1. Lightweight Typed API Client (`src/api/client.ts`)
- Native `fetch` wrapper automatically appending `Authorization: Bearer <token>` from `localStorage`.
- Unpacks standardized backend error envelope `{"error": {"code": "...", "message": "...", "details": [...]}}` into a typed `ApiError` class.
- Handles HTTP 401 Unauthorized by clearing session state and safely redirecting to `/login`.

### 2. Authentication Lifecycle (`src/context/AuthContext.tsx`)
- Restores session on initial load via `GET /auth/me`.
- Stores JWT token in `localStorage` with defense-in-depth considerations.
- Exposes `isAdmin` boolean helper for role-aware rendering.

### 3. Role-Aware UI & Defense-in-Depth
- UI elements (e.g. Admin badges, inventory controls) conditionally render using `useAuth().isAdmin`.
- Note: UI-level role checks exist strictly for user guidance; the backend independently checks and authorizes all actions on every single request.

### 4. Reusable Feedback Systems
- **`StatusBadge`**: Stock level status indicators adhering to system rules (`stocked` = green, `running_low` = amber, `gone` = red).
- **`ToastContext`**: Lightweight, floating notification system for success, warning, and error messages.
