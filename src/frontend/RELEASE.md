# Next.js + Better Auth + shadcn/ui Template

A modern Next.js template with authentication powered by Better Auth, shadcn/ui components, and PostgreSQL database integration. Ready to deploy on Railway.

## Features

- **Next.js 16+** - React framework with App Router
- **Better Auth** - Modern authentication library with Google OAuth support
- **PostgreSQL + Drizzle ORM** - Type-safe database integration
- **shadcn/ui** - 50+ pre-installed components (Button, Card, Dialog, Form, Table, Chart, and more)
- **TypeScript** - Full type safety
- **Tailwind CSS** - Utility-first CSS framework
- **Dark Mode** - Built-in support with next-themes
- **Lucide Icons** - 1000+ beautiful icons

## What's Included

### Authentication
- Google OAuth pre-configured
- Secure session management with Better Auth
- User profiles stored in PostgreSQL
- Protected routes support
- Pre-built login/logout UI

### UI Components
- All shadcn/ui components ready to use
- Dark mode toggle
- Responsive design patterns
- Form validation with react-hook-form and Zod
- Toast notifications with Sonner
- Chart components with Recharts

### Database
- PostgreSQL schema for authentication
- Drizzle ORM for type-safe queries
- Database migration scripts
- Drizzle Studio for database management

# Deploy and Host

## About Hosting

This Next.js + Better Auth template is designed to be deployed on Railway with minimal configuration. Railway automatically detects your Next.js application, provides a PostgreSQL database, installs dependencies, builds the project, and deploys it with a public URL.

Railway provides:
- **Automatic deployments** from your Git repository
- **Built-in PostgreSQL** with automatic backups
- **Custom domains** and SSL certificates
- **Environment variable management**
- **Instant rollbacks** to previous deployments
- **Built-in metrics** and logging
- **Horizontal scaling** capabilities

## Why Deploy

Deploy this template to Railway when you need:
- A production-ready starting point for your authenticated Next.js application
- Social login (Google OAuth) without managing authentication infrastructure
- User management with sessions and profiles stored in PostgreSQL
- Beautiful, accessible UI components out of the box
- Type-safe database integration with Drizzle ORM
- Rapid prototyping with pre-built components
- A professional-looking dashboard, landing page, or web application
- Dark mode support without additional configuration
- A scalable hosting solution that grows with your application

## Common Use Cases

- **SaaS Applications** - Multi-tenant apps with authentication and dashboards
- **Member Portals** - Gated content with user profiles
- **Internal Tools** - Authenticated internal applications
- **Customer Dashboards** - Client portals with data visualization
- **Admin Panels** - Authenticated interfaces for management
- **CMS Platforms** - Content management with role-based access

## Dependencies for

### Deployment Dependencies

This template includes the following core dependencies for production deployment:

**Framework & Runtime:**
- `next` (v16.1.1) - React framework for production
- `react` (v19.2.3) & `react-dom` - React library
- `typescript` (v5) - Type safety

**Authentication & Database:**
- `better-auth` (v1.4.9) - Modern authentication library
- `drizzle-orm` (v0.45.1) - Type-safe ORM
- `pg` (v8.16.3) - PostgreSQL client

**UI & Styling:**
- `tailwindcss` (v4) - Utility-first CSS framework
- `@radix-ui/*` - Accessible component primitives (40+ packages)
- `class-variance-authority` - Component variant management
- `clsx` & `tailwind-merge` - Utility for merging Tailwind classes
- `lucide-react` - Icon library with 1000+ icons
- `next-themes` - Dark mode support

**Additional Libraries:**
- `sonner` - Toast notifications
- `recharts` - Chart and data visualization
- `date-fns` - Modern date utilities
- `vaul` - Drawer component
- `embla-carousel-react` - Carousel functionality
- `input-otp` - OTP input component
- `cmdk` - Command menu component

**Development Dependencies:**
- `drizzle-kit` - Database migration toolkit
- `eslint` & `eslint-config-next` - Code linting
- `@types/*` - TypeScript type definitions

All dependencies are production-ready and actively maintained.

## Getting Started

### Local Development

```bash
npm install
cp .env.sample .env.local
# Fill in .env.local with your credentials
npm run db:push
npm run dev
```

**Environment variables needed:**
- `BETTER_AUTH_SECRET` - Generate with `openssl rand -base64 32`
- `DATABASE_URL` - PostgreSQL connection string
- `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET` - From Google Cloud Console

App runs at `http://localhost:3000`

### Deploy to Railway

1. Create account at [railway.app](https://railway.app/)
2. Create project with PostgreSQL + Web service
3. Configure environment variables:
   ```
   BETTER_AUTH_SECRET=<random-secret>
   BETTER_AUTH_URL=https://your-app.railway.app
   NEXT_PUBLIC_BETTER_AUTH_URL=https://your-app.railway.app
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   GOOGLE_CLIENT_ID=<your-id>
   GOOGLE_CLIENT_SECRET=<your-secret>
   ```
4. Update Google OAuth redirect: `https://your-app.railway.app/api/auth/callback/google`
5. Deploy from Git repository

## Using the Template

### Authentication

```tsx
// Use pre-built auth UI
import { AuthSection } from "@/components/auth-section";

// Access session in components
"use client";
import { useSession } from "@/lib/auth-client";

export function UserProfile() {
  const { data: session } = useSession();
  return <div>Welcome, {session?.user?.name}</div>;
}
```

### UI Components

```tsx
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

export default function Page() {
  return (
    <Card>
      <Button>Click me</Button>
    </Card>
  )
}
```

### Database

```tsx
import { db } from "@/lib/db/client";
import { user } from "@/lib/db/schema/auth-schema";

const users = await db.select().from(user);
```

## Available Scripts

- `npm run dev` - Start development
- `npm run build` - Build for production
- `npm run db:push` - Push database schema
- `npm run db:studio` - Open Drizzle Studio

## Extending the Template

### Add OAuth Providers

Edit `lib/auth.ts`:

```typescript
socialProviders: {
  google: { /* ... */ },
  github: {
    clientId: process.env.GITHUB_CLIENT_ID,
    clientSecret: process.env.GITHUB_CLIENT_SECRET,
  },
}
```

### Add Database Tables

Create in `lib/db/schema/`:

```typescript
export const posts = pgTable("posts", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  userId: text("user_id").references(() => user.id),
});
```

Run `npm run db:push` to apply changes.

## Learn More

- [Next.js](https://nextjs.org/docs) - [Better Auth](https://www.better-auth.com/docs) - [shadcn/ui](https://ui.shadcn.com)
- [Drizzle ORM](https://orm.drizzle.team/docs) - [Railway](https://docs.railway.app)
