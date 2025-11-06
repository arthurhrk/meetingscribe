import * as fs from "fs";
import * as path from "path";

/**
 * Creates a stop signal file for graceful recording shutdown
 * Used across all recording-related commands to communicate with the Python backend
 *
 * @param projectPath - MeetingScribe project directory
 * @param sessionId - Recording session ID
 * @returns true if signal created successfully, false otherwise
 */
export function createStopSignal(projectPath: string, sessionId: string): boolean {
  try {
    const signalsDir = path.join(projectPath, "storage", "signals");
    const stopSignalPath = path.join(signalsDir, `${sessionId}.stop`);

    // Ensure signals directory exists
    if (!fs.existsSync(signalsDir)) {
      fs.mkdirSync(signalsDir, { recursive: true });
    }

    // Write empty stop signal file
    fs.writeFileSync(stopSignalPath, "");
    console.log("[Signals] Stop signal created:", stopSignalPath);
    return true;
  } catch (error) {
    console.error("[Signals] Failed to create stop signal:", error);
    return false;
  }
}

/**
 * Checks if there are any active recordings
 *
 * @param projectPath - MeetingScribe project directory
 * @returns Array of active recording status files, or empty array if none
 */
export function getActiveRecordings(projectPath: string): string[] {
  try {
    const statusDir = path.join(projectPath, "storage", "status");

    if (!fs.existsSync(statusDir)) {
      return [];
    }

    const files = fs.readdirSync(statusDir).filter((f) => f.endsWith(".json"));
    const activeRecordings: string[] = [];

    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(statusDir, file), "utf8");
        const status = JSON.parse(content);
        if (status.status === "recording") {
          activeRecordings.push(file);
        }
      } catch (err) {
        // Skip files that can't be parsed
      }
    }

    return activeRecordings;
  } catch (error) {
    console.error("[Signals] Failed to get active recordings:", error);
    return [];
  }
}

/**
 * Reads a recording status file
 *
 * @param projectPath - MeetingScribe project directory
 * @param filename - Status filename (with .json extension)
 * @returns Parsed status object or null if error
 */
export function readRecordingStatus(projectPath: string, filename: string): any {
  try {
    const statusPath = path.join(projectPath, "storage", "status", filename);
    const content = fs.readFileSync(statusPath, "utf8");
    return JSON.parse(content);
  } catch (error) {
    console.error("[Signals] Failed to read recording status:", error);
    return null;
  }
}
