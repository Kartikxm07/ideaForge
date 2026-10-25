import { defineConfig } from "drizzle-kit";
import * as dotenv from "dotenv";

// Load .env.local so drizzle-kit picks up DATABASE_URL without a manual env prefix
dotenv.config({ path: ".env.local" });

export default defineConfig({
  out: "./drizzle",
  schema: "./lib/db/schema/index.ts",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL as string,
    ssl: false,
  },
});
