import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import fs from "fs";

const execAsync = promisify(exec);

export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const league = searchParams.get("league") || "nba";
        const mode = searchParams.get("mode") || "safe";

        // Path to the Universal bridge script in the core directory
        const scriptPath = path.join(process.cwd(), "..", "core", "universal_bridge.py");

        // Command to execute python
        const cmd = `python "${scriptPath}" --league ${league} --mode ${mode}`;

        const { stdout, stderr } = await execAsync(cmd, {
            cwd: path.join(process.cwd(), "..")
        });

        if (stderr && !stdout) {
            console.error("Python Error:", stderr);
            return NextResponse.json({ error: "Failed to generate predictions" }, { status: 500 });
        }

        try {
            const data = JSON.parse(stdout);

            // Load audit data
            let audit = {};
            const auditPath = path.join(process.cwd(), "..", "data", "performance_audit.json");
            if (fs.existsSync(auditPath)) {
                try {
                    const auditContent = fs.readFileSync(auditPath, "utf-8");
                    const allAudit = JSON.parse(auditContent);
                    audit = allAudit[league] || {};
                } catch (e) {
                    console.error("Audit Read Error:", e);
                }
            }

            return NextResponse.json({ ...data, audit });
        } catch (parseError) {
            console.error("JSON Parse Error:", parseError, "Stdout:", stdout);
            return NextResponse.json({ error: "Invalid response from prediction engine" }, { status: 500 });
        }
    } catch (error) {
        console.error("API Route Error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
