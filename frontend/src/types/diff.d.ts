declare module 'diff' {
  export interface Change {
    count?: number
    value: string
    added?: boolean
    removed?: boolean
  }

  export function diffLines(oldStr: string, newStr: string, options?: any): Change[]
  export function diffWords(oldStr: string, newStr: string, options?: any): Change[]
  export function diffChars(oldStr: string, newStr: string, options?: any): Change[]
  export function createPatch(fileName: string, oldStr: string, newStr: string, oldHeader?: string, newHeader?: string, options?: any): string
  export function applyPatch(source: string, patch: string, options?: any): string | false
}
