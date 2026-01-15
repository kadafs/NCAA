import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);

export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const date = searchParams.get("date") || "";

        // Path to the Python bridge script in the parent directory
        const scriptPath = path.join(process.cwd(), "..", "api_bridge.py");

        // Command to execute python
        const cmd = date ? `python "${scriptPath}" "${date}"` : `python "${scriptPath}"`;

        const { stdout, stderr } = await execAsync(cmd, {
            cwd: path.join(process.cwd(), "..")
        });

        if (stderr && !stdout) {
            console.error("Python Error:", stderr);
            return NextResponse.json({ error: "Failed to generate predictions" }, { status: 500 });
        }

        const data = JSON.parse(stdout);
        return NextResponse.json(data);
    } catch (error) {
        console.error("API Route Error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
