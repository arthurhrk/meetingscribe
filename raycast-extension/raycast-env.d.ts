/// <reference types="@raycast/api">

/* 🚧 🚧 🚧
 * This file is auto-generated from the extension's manifest.
 * Do not modify manually. Instead, update the `package.json` file.
 * 🚧 🚧 🚧 */

/* eslint-disable @typescript-eslint/ban-types */

type ExtensionPreferences = {
  /** Python Path - Path to Python executable (e.g., python or ./venv/Scripts/python.exe) */
  "pythonPath": string,
  /** Project Path - Path to the MeetingScribe project directory */
  "projectPath": string
}

/** Preferences accessible in all the extension's commands */
declare type Preferences = ExtensionPreferences

declare namespace Preferences {
  /** Preferences accessible in the `record` command */
  export type Record = ExtensionPreferences & {}
  /** Preferences accessible in the `recent` command */
  export type Recent = ExtensionPreferences & {}
  /** Preferences accessible in the `status` command */
  export type Status = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `record` command */
  export type Record = {}
  /** Arguments passed to the `recent` command */
  export type Recent = {}
  /** Arguments passed to the `status` command */
  export type Status = {}
}

