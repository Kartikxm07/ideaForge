"use client";

import { useSession, signIn, signOut } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LogIn, LogOut, User } from "lucide-react";

export function AuthSection() {
  const { data: session, isPending } = useSession();

  const handleGoogleSignIn = async () => {
    await signIn.social({
      provider: "google",
      callbackURL: "/",
    });
  };

  const handleSignOut = async () => {
    await signOut();
  };

  if (isPending) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Authentication</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Authentication</CardTitle>
        <CardDescription>
          {session?.user ? "You are signed in" : "Sign in to continue"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {session?.user ? (
          <>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              {session.user.image ? (
                <img
                  src={session.user.image}
                  alt={session.user.name}
                  className="w-12 h-12 rounded-full"
                />
              ) : (
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="w-6 h-6" />
                </div>
              )}
              <div className="flex-1">
                <p className="font-medium">{session.user.name}</p>
                <p className="text-sm text-muted-foreground">
                  {session.user.email}
                </p>
              </div>
            </div>
            <Button
              onClick={handleSignOut}
              variant="outline"
              className="w-full"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign Out
            </Button>
          </>
        ) : (
          <Button onClick={handleGoogleSignIn} className="w-full">
            <LogIn className="mr-2 h-4 w-4" />
            Sign in with Google
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
