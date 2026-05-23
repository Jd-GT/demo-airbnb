import { redirect } from "next/navigation";

export default function SignUpRoute() {
  redirect("/login?mode=register");
}
