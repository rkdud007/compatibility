import { NextRequest, NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const userId = searchParams.get("user");

  if (!userId || (userId !== "a" && userId !== "b")) {
    return NextResponse.json(
      { error: "Invalid user parameter. Must be 'a' or 'b'." },
      { status: 400 }
    );
  }

  try {
    const fileName =
      userId === "a" ? "conversations_A.json" : "conversations_B.json";
    const filePath = join(process.cwd(), "..", fileName);
    const fileContent = readFileSync(filePath, "utf-8");
    const conversations = JSON.parse(fileContent);

    return NextResponse.json(conversations);
  } catch (error) {
    console.error("Error loading default conversations:", error);
    return NextResponse.json(
      { error: "Failed to load default conversation file" },
      { status: 500 }
    );
  }
}
