import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

export async function GET() {
    try {
        const auditPath = path.join(process.cwd(), "..", "data", "performance_audit.json");
        if (fs.existsSync(auditPath)) {
            const auditContent = fs.readFileSync(auditPath, "utf-8");
            const audit = JSON.parse(auditContent);
            return NextResponse.json(audit);
        }
        return NextResponse.json({ error: "Audit file not found" }, { status: 404 });
    } catch (error) {
        console.error("Audit API Error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
