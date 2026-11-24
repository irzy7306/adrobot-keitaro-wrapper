import axios from 'axios';
export const api = axios.create({baseURL: '/api'});
export function message(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const detail = e.response?.data?.detail;
    return typeof detail === 'string' ? detail : JSON.stringify(detail ?? e.message);
  }
  return e instanceof Error ? e.message : String(e);
}
export type Item = {id: number; name: string; [key: string]: unknown};
export type Stream = {id: number; name: string; type?: string; schema?: string; offers?: {offer_id: number; share: number; state?: string}[]};
export type Campaign = {id: number; name: string; alias?: string; domain_id?: number};
