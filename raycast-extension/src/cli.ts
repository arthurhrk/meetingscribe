import { execFile } from "child_process";
import { promisify } from "util";
import { getPreferenceValues } from "@raycast/api";

const execFileAsync = promisify(execFile);

interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

export async function runCliJSON(args: string[]): Promise<any> {
  const { pythonPath, projectPath } = getPreferenceValues<Preferences>();
  const { stdout } = await execFileAsync(pythonPath, args, {
    cwd: projectPath,
    windowsHide: true,
    maxBuffer: 10 * 1024 * 1024,
  });
  return JSON.parse(stdout);
}

