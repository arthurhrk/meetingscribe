/// <reference types="@raycast/api">

/* 🚧 🚧 🚧
 * This file is auto-generated from the extension's manifest.
 * Do not modify manually. Instead, update the `package.json` file.
 * 🚧 🚧 🚧 */

/* eslint-disable @typescript-eslint/ban-types */

type ExtensionPreferences = {
  /** Python Path - Path to Python executable (e.g., .venv/Scripts/python.exe) */
  "pythonPath": string,
  /** Project Path - Full path to the MeetingScribe project directory */
  "projectPath": string,
  /** Google Gemini API Key - API key for Google Gemini transcription service (optional - get from https://makersuite.google.com/app/apikey) */
  "geminiApiKey": string,
  /** Gemini Model - Choose which Gemini model to use for transcription */
  "geminiModel": "models/gemini-2.0-flash-exp" | "models/gemini-1.5-pro",
  /** Audio Format - Choose the audio format for recording (WAV is uncompressed, M4A is compressed) */
  "audioFormat": "wav" | "m4a",
  /** Optimize Audio Before Upload - Reduce audio file size before uploading (converts to 16kHz mono WAV). Requires ffmpeg for non-WAV files. */
  "optimizeAudio": boolean
}

/** Preferences accessible in all the extension's commands */
declare type Preferences = ExtensionPreferences

declare namespace Preferences {
  /** Preferences accessible in the `record` command */
  export type Record = ExtensionPreferences & {}
  /** Preferences accessible in the `recording-status` command */
  export type RecordingStatus = ExtensionPreferences & {}
  /** Preferences accessible in the `recent` command */
  export type Recent = ExtensionPreferences & {}
  /** Preferences accessible in the `transcription-progress` command */
  export type TranscriptionProgress = ExtensionPreferences & {}
  /** Preferences accessible in the `status` command */
  export type Status = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `record` command */
  export type Record = {}
  /** Arguments passed to the `recording-status` command */
  export type RecordingStatus = {}
  /** Arguments passed to the `recent` command */
  export type Recent = {}
  /** Arguments passed to the `transcription-progress` command */
  export type TranscriptionProgress = {}
  /** Arguments passed to the `status` command */
  export type Status = {}
}

