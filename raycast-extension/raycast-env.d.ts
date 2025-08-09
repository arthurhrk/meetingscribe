/// <reference types="@raycast/api">

/* 🚧 🚧 🚧
 * This file is auto-generated from the extension's manifest.
 * Do not modify manually. Instead, update the `package.json` file.
 * 🚧 🚧 🚧 */

/* eslint-disable @typescript-eslint/ban-types */

type ExtensionPreferences = {
  /** Python Path - Caminho para o executável Python do MeetingScribe */
  "pythonPath": string,
  /** Project Path - Caminho para o diretório do MeetingScribe */
  "projectPath": string,
  /** Default Whisper Model - Modelo Whisper padrão para transcrições */
  "defaultModel": "tiny" | "base" | "small" | "medium" | "large-v3"
}

/** Preferences accessible in all the extension's commands */
declare type Preferences = ExtensionPreferences

declare namespace Preferences {
  /** Preferences accessible in the `record` command */
  export type Record = ExtensionPreferences & {}
  /** Preferences accessible in the `recent` command */
  export type Recent = ExtensionPreferences & {}
  /** Preferences accessible in the `transcribe` command */
  export type Transcribe = ExtensionPreferences & {}
  /** Preferences accessible in the `status` command */
  export type Status = ExtensionPreferences & {}
  /** Preferences accessible in the `export` command */
  export type Export = ExtensionPreferences & {}
  /** Preferences accessible in the `teams-monitor` command */
  export type TeamsMonitor = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `record` command */
  export type Record = {}
  /** Arguments passed to the `recent` command */
  export type Recent = {}
  /** Arguments passed to the `transcribe` command */
  export type Transcribe = {}
  /** Arguments passed to the `status` command */
  export type Status = {}
  /** Arguments passed to the `export` command */
  export type Export = {}
  /** Arguments passed to the `teams-monitor` command */
  export type TeamsMonitor = {}
}

