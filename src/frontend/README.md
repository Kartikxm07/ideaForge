# Next.js Better Auth Template

A modern Next.js template with authentication powered by [Better Auth](https://www.better-auth.com/), [shadcn/ui](https://ui.shadcn.com/) components, and PostgreSQL database integration.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/nextjs-better-auth-shadcn?referralCode=Z1xivh&utm_medium=integration&utm_source=template&utm_campaign=generic)

## Features

- **Authentication**: Fully configured Better Auth with Google OAuth support
- **UI Components**: Beautiful, accessible components from shadcn/ui
- **Database**: PostgreSQL integration with Drizzle ORM
- **Type Safety**: Full TypeScript support
- **Modern Stack**: Next.js 16 with App Router and React 19
- **Styling**: Tailwind CSS with custom design system

## Tech Stack

- [Next.js 16](https://nextjs.org/) - React framework
- [Better Auth](https://www.better-auth.com/) - Authentication library
- [Drizzle ORM](https://orm.drizzle.team/) - TypeScript ORM
- [PostgreSQL](https://www.postgresql.org/) - Database
- [shadcn/ui](https://ui.shadcn.com/) - UI components
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [TypeScript](https://www.typescriptlang.org/) - Type safety

## Prerequisites

- Node.js 20+ installed
- PostgreSQL database running
- Google OAuth credentials (for authentication)

## Getting Started

### 1. Clone and Install

```bash
npm install
```

### 2. Set Up Environment Variables

Copy the sample environment file:

```bash
cp .env.sample .env.local
```

Edit `.env.local` with your configuration:

```env
# Generate a random secret (e.g., using: openssl rand -base64 32)
BETTER_AUTH_SECRET=your-secret-key-here

# Base URL for your application
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000

# PostgreSQL database connection
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

# Google OAuth credentials (see instructions below)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 3. Configure Google OAuth

Follow these steps to obtain Google OAuth credentials:

#### Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top of the page
3. Click "New Project"
4. Enter a project name (e.g., "My Auth App")
5. Click "Create"

#### Configure OAuth Consent Screen

1. In the left sidebar, go to "APIs & Services" > "OAuth consent screen"
2. Select "External" user type and click "Create"
3. Fill in the required fields:
   - App name: Your application name
   - User support email: Your email address
   - Developer contact information: Your email address
4. Click "Save and Continue"
5. On the Scopes page, click "Save and Continue" (default scopes are fine)
6. On the Test users page, click "Save and Continue"
7. Review and click "Back to Dashboard"

#### Create OAuth Credentials

1. In the left sidebar, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" at the top
3. Select "OAuth client ID"
4. Choose "Web application" as the application type
5. Enter a name (e.g., "Web Client")
6. Under "Authorized redirect URIs", click "Add URI" and add:
   ```
   http://localhost:3000/api/auth/callback/google
   ```
7. Click "Create"
8. A dialog will appear with your credentials:
   - Copy the **Client ID** to `GOOGLE_CLIENT_ID` in your `.env.local`
   - Copy the **Client Secret** to `GOOGLE_CLIENT_SECRET` in your `.env.local`

You can always access these credentials later from the "Credentials" page in Google Cloud Console.

### 4. Set Up Database

Make sure your PostgreSQL database is running, then run migrations:

```bash
npm run db:push
```

### 5. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see your application.

## Project Structure

```
├── app/
│   ├── api/auth/[...all]/     # Better Auth API routes
│   └── page.tsx                # Main page with auth
├── components/
│   ├── auth-section.tsx        # Login/logout component
│   └── ui/                     # shadcn/ui components
├── lib/
│   ├── auth.ts                 # Server-side auth configuration
│   ├── auth-client.ts          # Client-side auth hooks
│   └── db/
│       ├── client.ts           # Database client
│       └── schema/
│           └── auth-schema.ts  # Auth database schema
└── .env.sample                 # Environment variables template
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run db:push` - Push database schema changes to your database
- `npm run db:generate` - Generate SQL migration files
- `npm run db:studio` - Open Drizzle Studio to browse your database

## Authentication Features

The template includes a pre-built authentication system with:

- Google OAuth sign-in
- User session management
- Protected routes support
- User profile display
- Secure logout functionality

## Customization

### Adding More OAuth Providers

Edit `lib/auth.ts` to add more providers:

```typescript
socialProviders: {
  google: { /* ... */ },
  github: {
    clientId: process.env.GITHUB_CLIENT_ID,
    clientSecret: process.env.GITHUB_CLIENT_SECRET,
  },
}
```

### Styling

The template uses Tailwind CSS. Customize your theme in `tailwind.config.ts` and global styles in `app/globals.css`.

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Better Auth Documentation](https://www.better-auth.com/docs)
- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Drizzle ORM Documentation](https://orm.drizzle.team/docs/overview)

## Deploy on Railway

Deploy your Next.js app with database on [Railway](https://railway.app/).

### Deployment Steps

1. **Create a Railway account** at [railway.app](https://railway.app/)

2. **Create a new project** and add two services:
   - PostgreSQL database
   - Web service (Next.js app)

3. **Configure environment variables** in your web service:
   ```
   BETTER_AUTH_SECRET=your-secret-key-here
   BETTER_AUTH_URL=https://your-app.railway.app
   NEXT_PUBLIC_BETTER_AUTH_URL=https://your-app.railway.app
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```

4. **Update Google OAuth** authorized redirect URIs:
   ```
   https://your-app.railway.app/api/auth/callback/google
   ```

5. **Deploy** - Railway will automatically build and deploy your app from your Git repository

Railway provides built-in PostgreSQL with automatic backups and makes it easy to scale your application.
